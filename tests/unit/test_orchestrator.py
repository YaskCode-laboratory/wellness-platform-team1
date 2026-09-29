"""Pruebas del Orchestrator Agent (issues S3-02 y S3-04).

Cinco clases, segun que se esta probando:

- TestPlanificacion cubre _planificar(), que es logica pura: no toca red ni
  modelo. Es la politica completa de cuando delegar, en quien, con que mensaje
  y en que orden.
- TestColaboracionEntreAgentes cubre el flujo con mas de un agente: reparto de
  la consulta, encadenamiento de contexto, consolidacion y degradacion parcial.
- TestProcesarSolicitud cubre el flujo de punta a punta.
- TestClasificador cubre la degradacion del clasificador y el reparto.
- TestRegistroDeAgentes cubre que el catalogo se derive del registro.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.orchestration.communication.contratos import RespuestaAgente, SolicitudAgente
from src.orchestration.orchestrator import registro_agentes
from src.orchestration.orchestrator.agent import (
    INTRO_COLABORACION,
    RESPUESTA_AGENTE_FALLO,
    RESPUESTA_DOMINIO_SIN_AGENTE,
    RESPUESTA_FUERA_DE_DOMINIO,
    RESPUESTA_NO_RECONOCIDA,
    OrchestratorAgent,
)
from src.orchestration.orchestrator.clasificador import (
    Clasificacion,
    SubConsulta,
    clasificar,
)


def clasificacion(intencion, confianza=0.9, motivo="motivo de prueba", subconsultas=None):
    return Clasificacion(
        intencion=intencion,
        motivo=motivo,
        confianza=confianza,
        subconsultas=subconsultas or [],
    )


def agente_falso(nombre, intencion, etiqueta, texto="respuesta del agente",
                 error=None, degradado=False):
    """Entrada de registro con un invocador que respeta el contrato de S3-04.

    'error' y 'degradado' modelan dos situaciones que no son la misma. Con
    'error' el agente lanza y _delegar() devuelve una respuesta marcada como
    fallo: no produjo contenido de dominio. Con 'degradado' el agente responde
    con normalidad aunque alguna capacidad suya fallara, y su texto sigue
    siendo util. De esa diferencia depende que su respuesta se encadene o no
    como contexto al siguiente agente.
    """

    def _invocar(solicitud: SolicitudAgente) -> RespuestaAgente:
        if error is not None:
            raise error
        return RespuestaAgente(
            agente=nombre,
            texto=texto,
            herramientas_invocadas=[f"herramienta_de_{nombre}"],
            fuentes=[f"KB-{nombre[:3].upper()}"],
            degradado=degradado,
        )

    return {
        "nombre": nombre,
        "intencion": intencion,
        "titulo": f"{nombre} Agent",
        "etiqueta": etiqueta,
        "descripcion": "...",
        "invocador": MagicMock(side_effect=_invocar),
    }


def orquestador_sin_persistencia() -> OrchestratorAgent:
    """Orquestador con el registro de delegaciones inyectado como mock.

    Persistir la traza es auxiliar y toca Firestore; las pruebas del
    orquestador no deben depender de la red.
    """
    return OrchestratorAgent(registro=MagicMock())


class TestPlanificacion(unittest.TestCase):
    """La politica de delegacion, aislada de la red y del modelo."""

    def setUp(self):
        self.orq = orquestador_sin_persistencia()
        self.coach = agente_falso("wellness_coach", "entrenamiento", "Sobre tu entrenamiento")
        self.nutri = agente_falso("nutrition", "nutricion", "Sobre tu alimentacion")

    @patch("src.orchestration.orchestrator.agent.resolver")
    def test_delega_en_un_agente_con_el_mensaje_intacto(self, mock_resolver):
        """En delegacion simple no hay nada que repartir, y reformular el
        mensaje solo podria perder matices."""
        mock_resolver.return_value = self.coach

        plan = self.orq._planificar(clasificacion("entrenamiento"), "como voy?")

        self.assertEqual(len(plan["delegaciones"]), 1)
        self.assertIs(plan["delegaciones"][0]["agente"], self.coach)
        self.assertEqual(plan["delegaciones"][0]["mensaje"], "como voy?")
        self.assertIsNone(plan["motivo_no_delegacion"])

    def test_no_delega_con_confianza_insuficiente(self):
        """Una delegacion equivocada es peor que una pregunta de mas: el
        corredor recibiria una respuesta del dominio incorrecto sin saber
        que hubo un error."""
        plan = self.orq._planificar(clasificacion("entrenamiento", confianza=0.3), "msg")

        self.assertEqual(plan["delegaciones"], [])
        self.assertEqual(plan["motivo_no_delegacion"], "confianza_insuficiente")
        self.assertEqual(plan["texto"], RESPUESTA_NO_RECONOCIDA)

    def test_la_confianza_se_evalua_antes_que_la_intencion(self):
        with patch("src.orchestration.orchestrator.agent.resolver") as mock_resolver:
            mock_resolver.return_value = self.coach
            plan = self.orq._planificar(clasificacion("entrenamiento", confianza=0.49), "msg")

        self.assertEqual(plan["delegaciones"], [])
        mock_resolver.assert_not_called()

    def test_fuera_de_dominio_redirige_sin_delegar(self):
        plan = self.orq._planificar(clasificacion("fuera_de_dominio"), "msg")

        self.assertEqual(plan["delegaciones"], [])
        self.assertEqual(plan["texto"], RESPUESTA_FUERA_DE_DOMINIO)

    def test_no_reconocida_pide_aclaracion(self):
        plan = self.orq._planificar(clasificacion("no_reconocida"), "msg")

        self.assertEqual(plan["delegaciones"], [])
        self.assertEqual(plan["texto"], RESPUESTA_NO_RECONOCIDA)

    @patch("src.orchestration.orchestrator.agent.resolver")
    def test_la_colaboracion_reparte_la_consulta_y_respeta_el_orden(self, mock_resolver):
        """Cada agente recibe su parte, no la consulta entera. El orden no es
        cosmetico: determina quien responde primero y cuya respuesta sirve de
        contexto al siguiente."""
        mock_resolver.side_effect = lambda d: {
            "nutricion": self.nutri,
            "entrenamiento": self.coach,
        }[d]

        plan = self.orq._planificar(
            clasificacion(
                "mixta",
                subconsultas=[
                    SubConsulta("nutricion", "Que como antes de una tirada larga?"),
                    SubConsulta("entrenamiento", "Como ajusto el entrenamiento esta semana?"),
                ],
            ),
            "mensaje original completo",
        )

        self.assertEqual(
            [d["agente"]["nombre"] for d in plan["delegaciones"]],
            ["nutrition", "wellness_coach"],
        )
        self.assertEqual(plan["delegaciones"][0]["mensaje"], "Que como antes de una tirada larga?")
        self.assertEqual(
            plan["delegaciones"][1]["mensaje"], "Como ajusto el entrenamiento esta semana?"
        )

    def test_mixta_sin_subconsultas_no_delega(self):
        """Defensa en profundidad: en produccion el clasificador ya marca este
        caso con confianza cero, porque declarar que hacen falta varios
        especialistas sin poder nombrarlos es una afirmacion que se contradice
        a si misma. Aqui se comprueba que el planificador tampoco lo deja pasar
        si esa guarda anterior se debilitara."""
        plan = self.orq._planificar(clasificacion("mixta", subconsultas=[]), "msg")

        self.assertEqual(plan["delegaciones"], [])
        self.assertIsNotNone(plan["motivo_no_delegacion"])

    @patch("src.orchestration.orchestrator.agent.es_dominio_sin_agente")
    @patch("src.orchestration.orchestrator.agent.resolver")
    def test_un_dominio_previsto_sin_agente_no_es_fuera_de_dominio(
        self, mock_resolver, mock_es_dominio
    ):
        """Un dominio que la plataforma cubre pero que aun no tiene agente no
        debe tratarse como tema ajeno: eso le diria al corredor algo falso.

        Se prueba el MECANISMO con un dominio simulado. En S3-02 el caso real
        era 'nutricion'; al registrarse el Nutrition Agent en S3-03 esa
        intencion paso a tener agente, pero la regla sigue vigente para los
        agentes que contempla el roadmap."""
        mock_resolver.return_value = None
        mock_es_dominio.return_value = True

        plan = self.orq._planificar(clasificacion("motivacion"), "msg")

        self.assertEqual(plan["delegaciones"], [])
        self.assertEqual(plan["texto"], RESPUESTA_DOMINIO_SIN_AGENTE)
        self.assertEqual(plan["motivo_no_delegacion"], "dominio_sin_agente")

    @patch("src.orchestration.orchestrator.agent.es_dominio_sin_agente")
    @patch("src.orchestration.orchestrator.agent.resolver")
    def test_intencion_valida_sin_destino_pide_aclaracion(
        self, mock_resolver, mock_es_dominio
    ):
        mock_resolver.return_value = None
        mock_es_dominio.return_value = False

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            plan = self.orq._planificar(clasificacion("intencion_huerfana"), "msg")

        self.assertEqual(plan["delegaciones"], [])
        self.assertEqual(plan["motivo_no_delegacion"], "intencion_sin_destino")


class TestColaboracionEntreAgentes(unittest.TestCase):
    """El escenario que justifica el sistema multiagente."""

    def setUp(self):
        self.orq = orquestador_sin_persistencia()
        self.nutri = agente_falso(
            "nutrition", "nutricion", "Sobre tu alimentacion",
            texto="Consume 30-60 g de carbohidratos por hora.",
        )
        self.coach = agente_falso(
            "wellness_coach", "entrenamiento", "Sobre tu entrenamiento",
            texto="Manten el aumento de carga por debajo del 10%.",
        )
        self.delegaciones = [
            {"agente": self.nutri, "mensaje": "Que como antes de correr?"},
            {"agente": self.coach, "mensaje": "Como ajusto la carga?"},
        ]

    def test_invoca_a_los_dos_agentes_en_orden(self):
        _, respuestas = self.orq._ejecutar_plan(self.delegaciones, "u1", "traza-1")

        self.assertEqual([r.agente for r in respuestas], ["nutrition", "wellness_coach"])
        self.nutri["invocador"].assert_called_once()
        self.coach["invocador"].assert_called_once()

    def test_cada_agente_recibe_su_parte_de_la_consulta(self):
        """Sin el reparto, el primer especialista contesta su parte y ademas
        deriva la ajena al segundo, que responde justo debajo en la misma
        pantalla: el corredor lee una derivacion innecesaria."""
        self.orq._ejecutar_plan(self.delegaciones, "u1", "traza-1")

        primera = self.nutri["invocador"].call_args[0][0]
        segunda = self.coach["invocador"].call_args[0][0]

        self.assertEqual(primera.mensaje, "Que como antes de correr?")
        self.assertEqual(segunda.mensaje, "Como ajusto la carga?")

    def test_el_segundo_agente_recibe_lo_que_respondio_el_primero(self):
        """Es lo que convierte dos respuestas sueltas en colaboracion: el
        segundo complementa en vez de repetir."""
        self.orq._ejecutar_plan(self.delegaciones, "u1", "traza-1")

        primera = self.nutri["invocador"].call_args[0][0]
        segunda = self.coach["invocador"].call_args[0][0]

        self.assertEqual(primera.contexto, "")
        self.assertEqual(primera.paso, 1)
        self.assertIn("carbohidratos", segunda.contexto)
        self.assertEqual(segunda.paso, 2)
        self.assertIn("carbohidratos", segunda.mensaje_con_contexto())

    def test_la_traza_id_es_la_misma_para_todos_los_pasos(self):
        """Un flujo con dos agentes debe poder reconstruirse entero
        correlacionando por traza_id."""
        self.orq._ejecutar_plan(self.delegaciones, "u1", "traza-abc")

        for entrada in (self.nutri, self.coach):
            self.assertEqual(entrada["invocador"].call_args[0][0].traza_id, "traza-abc")

    def test_la_respuesta_consolidada_atribuye_cada_parte_sin_reescribirla(self):
        """El orquestador no parafrasea: las citas de cada agente se validaron
        contra el texto que ese agente produjo, y reescribirlo romperia esa
        correspondencia."""
        ejecutadas, respuestas = self.orq._ejecutar_plan(
            self.delegaciones, "u1", "traza-1"
        )

        texto = self.orq._consolidar(ejecutadas, respuestas)

        self.assertIn(INTRO_COLABORACION, texto)
        self.assertIn("Sobre tu alimentacion", texto)
        self.assertIn("Sobre tu entrenamiento", texto)
        self.assertIn("Consume 30-60 g de carbohidratos por hora.", texto)
        self.assertIn("Manten el aumento de carga por debajo del 10%.", texto)

    def test_con_un_solo_agente_no_se_agrega_estructura(self):
        delegacion = [{"agente": self.coach, "mensaje": "msg"}]
        ejecutadas, respuestas = self.orq._ejecutar_plan(delegacion, "u1", "traza-1")

        texto = self.orq._consolidar(ejecutadas, respuestas)

        self.assertEqual(texto, "Manten el aumento de carga por debajo del 10%.")
        self.assertNotIn(INTRO_COLABORACION, texto)

    def test_si_el_primer_agente_falla_el_segundo_responde_igual(self):
        """Degradacion parcial: el corredor recibe la mitad que si funciono,
        declarada como tal, en vez de perder la consulta entera. Es la misma
        leccion de la correccion S2-04, un nivel mas arriba."""
        nutri_caido = agente_falso(
            "nutrition", "nutricion", "Sobre tu alimentacion",
            error=ConnectionError("ChromaDB no responde"),
        )
        delegaciones = [
            {"agente": nutri_caido, "mensaje": "que como?"},
            {"agente": self.coach, "mensaje": "como entreno?"},
        ]

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            _, respuestas = self.orq._ejecutar_plan(delegaciones, "u1", "traza-1")

        self.assertEqual(len(respuestas), 2)
        self.assertTrue(respuestas[0].degradado)
        self.assertEqual(respuestas[0].texto, RESPUESTA_AGENTE_FALLO)
        self.assertFalse(respuestas[1].degradado)
        self.assertIn("carga", respuestas[1].texto)

    def test_ningun_agente_se_invoca_dos_veces_en_la_misma_solicitud(self):
        """Guarda contra ciclos. El clasificador ya elimina duplicados y los
        agentes no pueden delegar, asi que esto no deberia dispararse nunca:
        esta por si una de esas dos protecciones se debilita."""
        repetidas = [
            {"agente": self.coach, "mensaje": "a"},
            {"agente": self.coach, "mensaje": "b"},
        ]

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            ejecutadas, respuestas = self.orq._ejecutar_plan(repetidas, "u1", "traza-1")

        self.assertEqual(len(respuestas), 1)
        self.assertEqual(self.coach["invocador"].call_count, 1)
        self.assertEqual(len(ejecutadas), 1)
        self.assertEqual(ejecutadas[0]["mensaje"], "a")

    def test_una_delegacion_omitida_no_desalinea_la_traza(self):
        """El defecto que motivo devolver las delegaciones ejecutadas.

        _componer() reconstruia mensajeDelegado indexando el PLAN por la
        posicion de la RESPUESTA. Con una omision intermedia el indice se
        desplaza y la traza atribuye a un agente un mensaje que nunca recibio.

        Aqui el plan pide nutricion, nutricion otra vez (omitida por la
        guarda) y entrenamiento. Sin la correccion, el Coach aparecia en la
        traza habiendo recibido la sub-consulta de nutricion.

        Una traza equivocada es peor que una ausente: se lee como evidencia. Y
        el defecto solo se manifestaba cuando actuaba una proteccion, que es
        exactamente cuando hace falta poder auditar.
        """
        plan = {
            "delegaciones": [
                {"agente": self.nutri, "mensaje": "que como antes?"},
                {"agente": self.nutri, "mensaje": "duplicada que se omite"},
                {"agente": self.coach, "mensaje": "como ajusto la carga?"},
            ],
            "texto": None,
            "motivo_no_delegacion": None,
        }

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            ejecutadas, respuestas = self.orq._ejecutar_plan(
                plan["delegaciones"], "u1", "traza-1"
            )

        traza = self.orq._componer(
            traza_id="traza-1",
            clasificacion=clasificacion("mixta"),
            plan=plan,
            ejecutadas=ejecutadas,
            respuestas=respuestas,
            latencia_clasificacion=10,
            latencia_total=20,
        )

        self.assertEqual([p["agente"] for p in traza["pasos"]],
                         ["nutrition", "wellness_coach"])
        self.assertEqual(traza["pasos"][0]["mensajeDelegado"], "que como antes?")
        self.assertEqual(traza["pasos"][1]["mensajeDelegado"], "como ajusto la carga?")

    def test_el_texto_de_un_fallo_no_se_encadena_como_respuesta_valida(self):
        """El segundo defecto de la revision de S3-04.

        Cuando un agente falla, su 'texto' es RESPUESTA_AGENTE_FALLO: un
        mensaje del orquestador dirigido al corredor, no contenido de dominio.
        Encadenarlo producia "Nutrition Agent respondió: No pude completar tu
        consulta...", y mensaje_con_contexto() le pide al siguiente que lo
        COMPLEMENTE y no lo CONTRADIGA. El segundo agente acababa tratando un
        mensaje de error como aportacion de un especialista.

        Ademas invertia el sentido de la degradacion, que S3-01 definio como
        conservar lo que si funciono: asi el fallo de uno contaminaba al otro.
        """
        nutri_caido = agente_falso(
            "nutrition", "nutricion", "Sobre tu alimentacion",
            error=ConnectionError("ChromaDB no responde"),
        )
        delegaciones = [
            {"agente": nutri_caido, "mensaje": "que como?"},
            {"agente": self.coach, "mensaje": "como entreno?"},
        ]

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            self.orq._ejecutar_plan(delegaciones, "u1", "traza-1")

        recibida = self.coach["invocador"].call_args[0][0]

        self.assertNotIn(RESPUESTA_AGENTE_FALLO, recibida.contexto)
        self.assertNotIn("respondió", recibida.contexto)
        self.assertIn("no pudo completar", recibida.contexto)

    def test_una_herramienta_caida_si_encadena_el_texto_del_agente(self):
        """La contraparte, y la razon de que el discriminante sea 'fallo' y no
        'degradado': un Coach que respondio bien pero no pudo consultar el
        clima viene degradado, y su texto SI es contexto util para el
        siguiente. Confundirlos descartaria informacion buena."""
        coach_degradado = agente_falso(
            "wellness_coach", "entrenamiento", "Sobre tu entrenamiento",
            texto="No pude ver el clima, pero baja el volumen un 20%.",
            degradado=True,
        )

        delegaciones = [
            {"agente": coach_degradado, "mensaje": "como entreno?"},
            {"agente": self.nutri, "mensaje": "que como?"},
        ]

        self.orq._ejecutar_plan(delegaciones, "u1", "traza-1")

        recibida = self.nutri["invocador"].call_args[0][0]

        self.assertIn("baja el volumen un 20%", recibida.contexto)
        self.assertIn("respondió", recibida.contexto)


class TestProcesarSolicitud(unittest.TestCase):
    """Flujo completo, con clasificador y registro mockeados."""

    def setUp(self):
        self.registro = MagicMock()
        self.orq = OrchestratorAgent(registro=self.registro)
        self.coach = agente_falso(
            "wellness_coach", "entrenamiento", "Sobre tu entrenamiento",
            texto="Esta semana llevas 14 km de tu meta de 25 km.",
        )

    @patch("src.orchestration.orchestrator.agent.resolver")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_delegacion_exitosa_devuelve_la_respuesta_del_agente(
        self, mock_clasificar, mock_resolver
    ):
        mock_clasificar.return_value = clasificacion("entrenamiento")
        mock_resolver.return_value = self.coach

        resultado = self.orq.procesar("u1", "como voy esta semana?")

        self.assertTrue(resultado["delegado"])
        self.assertFalse(resultado["colaboracion"])
        self.assertEqual(resultado["agente"], "wellness_coach")
        self.assertEqual(resultado["agentes"], ["wellness_coach"])
        self.assertIn("14 km", resultado["respuesta"])

    @patch("src.orchestration.orchestrator.agent.resolver")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_la_traza_permite_reconstruir_la_solicitud(
        self, mock_clasificar, mock_resolver
    ):
        """S3-06 exige poder responder que se entendio, a quien se delego, que
        se le pidio exactamente, que consulto y cuanto costo cada paso."""
        mock_clasificar.return_value = clasificacion(
            "entrenamiento", motivo="pregunta por su progreso semanal"
        )
        mock_resolver.return_value = self.coach

        resultado = self.orq.procesar("u1", "como voy?")

        self.assertTrue(resultado["trazaId"])
        self.assertEqual(resultado["intencion"], "entrenamiento")
        self.assertEqual(resultado["motivoClasificacion"], "pregunta por su progreso semanal")
        self.assertEqual(len(resultado["pasos"]), 1)
        self.assertEqual(resultado["pasos"][0]["agente"], "wellness_coach")
        self.assertEqual(resultado["pasos"][0]["mensajeDelegado"], "como voy?")
        self.assertIn("clasificacionMs", resultado["latencias"])
        self.assertIn("agentesMs", resultado["latencias"])
        self.assertIn("totalMs", resultado["latencias"])

    @patch("src.orchestration.orchestrator.agent.resolver")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_la_traza_se_registra_para_su_consulta_posterior(
        self, mock_clasificar, mock_resolver
    ):
        mock_clasificar.return_value = clasificacion("entrenamiento")
        mock_resolver.return_value = self.coach

        resultado = self.orq.procesar("u1", "como voy?")

        self.registro.registrar.assert_called_once()
        registrada = self.registro.registrar.call_args[0][0]
        self.assertEqual(registrada["trazaId"], resultado["trazaId"])

    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_sin_delegacion_no_se_invoca_ningun_agente(self, mock_clasificar):
        mock_clasificar.return_value = clasificacion("fuera_de_dominio")

        resultado = self.orq.procesar("u1", "que pelicula me recomiendas?")

        self.assertFalse(resultado["delegado"])
        self.assertIsNone(resultado["agente"])
        self.assertEqual(resultado["agentes"], [])
        self.assertEqual(resultado["pasos"], [])
        self.assertEqual(resultado["respuesta"], RESPUESTA_FUERA_DE_DOMINIO)
        self.assertEqual(resultado["latencias"]["agentesMs"], 0)

    @patch("src.orchestration.orchestrator.agent.resolver")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_un_fallo_del_agente_no_tumba_la_solicitud(
        self, mock_clasificar, mock_resolver
    ):
        mock_clasificar.return_value = clasificacion("entrenamiento")
        mock_resolver.return_value = agente_falso(
            "wellness_coach", "entrenamiento", "Sobre tu entrenamiento",
            error=ConnectionError("Vertex AI no responde"),
        )

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            resultado = self.orq.procesar("u1", "como voy?")

        self.assertTrue(resultado["delegado"])
        self.assertTrue(resultado["degradado"])
        self.assertEqual(resultado["respuesta"], RESPUESTA_AGENTE_FALLO)

    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_un_fallo_del_clasificador_pide_aclaracion(self, mock_clasificar):
        mock_clasificar.return_value = Clasificacion(
            intencion="no_reconocida", motivo="el clasificador no respondio", confianza=0.0
        )

        resultado = self.orq.procesar("u1", "algo")

        self.assertFalse(resultado["delegado"])
        self.assertEqual(resultado["respuesta"], RESPUESTA_NO_RECONOCIDA)


class TestClasificador(unittest.TestCase):
    """Degradacion del clasificador y reparto de consultas mixtas."""

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_clasificacion_valida_se_devuelve_tal_cual(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = (
            '{"intencion": "entrenamiento", "motivo": "pregunta por su carga", '
            '"confianza": 0.92, "dominios": []}'
        )
        MockModel.return_value.generate_content.return_value = respuesta

        resultado = clasificar("puedo entrenar fuerte hoy?")

        self.assertEqual(resultado.intencion, "entrenamiento")
        self.assertEqual(resultado.confianza, 0.92)
        self.assertTrue(resultado.es_confiable)
        self.assertFalse(resultado.es_colaboracion)

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_una_mixta_con_dos_subconsultas_es_colaboracion(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = (
            '{"intencion": "mixta", "motivo": "requiere ambos dominios", '
            '"confianza": 0.9, "dominios": ['
            '{"dominio": "nutricion", "mensaje": "Que como antes de correr?"},'
            '{"dominio": "entrenamiento", "mensaje": "Como ajusto la carga?"}]}'
        )
        MockModel.return_value.generate_content.return_value = respuesta

        resultado = clasificar("que como y como entreno?")

        self.assertTrue(resultado.es_colaboracion)
        self.assertEqual(resultado.dominios, ["nutricion", "entrenamiento"])
        self.assertEqual(resultado.subconsultas[0].mensaje, "Que como antes de correr?")
        self.assertEqual(resultado.subconsultas[1].mensaje, "Como ajusto la carga?")

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_los_dominios_se_filtran_contra_el_registro(self, MockModel):
        """El enum del esquema deberia impedirlo, pero un dominio inexistente
        no puede llegar al planificador."""
        respuesta = MagicMock()
        respuesta.text = (
            '{"intencion": "mixta", "motivo": "x", "confianza": 0.9, "dominios": ['
            '{"dominio": "nutricion", "mensaje": "a"},'
            '{"dominio": "astrologia", "mensaje": "b"},'
            '{"dominio": "entrenamiento", "mensaje": "c"}]}'
        )
        MockModel.return_value.generate_content.return_value = respuesta

        resultado = clasificar("algo")

        self.assertEqual(resultado.dominios, ["nutricion", "entrenamiento"])

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_un_dominio_repetido_se_invoca_una_sola_vez(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = (
            '{"intencion": "mixta", "motivo": "x", "confianza": 0.9, "dominios": ['
            '{"dominio": "nutricion", "mensaje": "a"},'
            '{"dominio": "nutricion", "mensaje": "b"},'
            '{"dominio": "entrenamiento", "mensaje": "c"}]}'
        )
        MockModel.return_value.generate_content.return_value = respuesta

        resultado = clasificar("algo")

        self.assertEqual(resultado.dominios, ["nutricion", "entrenamiento"])

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_un_submensaje_vacio_cae_al_mensaje_original(self, MockModel):
        """Un agente con la pregunta entera responde de mas; un agente al que
        no se invoca deja un hueco silencioso en la respuesta, que es peor."""
        respuesta = MagicMock()
        respuesta.text = (
            '{"intencion": "mixta", "motivo": "x", "confianza": 0.9, "dominios": ['
            '{"dominio": "nutricion", "mensaje": ""},'
            '{"dominio": "entrenamiento", "mensaje": "Como ajusto la carga?"}]}'
        )
        MockModel.return_value.generate_content.return_value = respuesta

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="WARNING"):
            resultado = clasificar("pregunta original completa")

        self.assertEqual(resultado.subconsultas[0].mensaje, "pregunta original completa")
        self.assertTrue(resultado.es_colaboracion)

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_una_mixta_sin_dominios_suficientes_no_es_confiable(self, MockModel):
        """Afirmar que hacen falta varios especialistas sin poder nombrarlos es
        una clasificacion que se contradice a si misma. Adivinar a quien
        delegar ahi seria inventar."""
        respuesta = MagicMock()
        respuesta.text = (
            '{"intencion": "mixta", "motivo": "x", "confianza": 0.95, "dominios": ['
            '{"dominio": "nutricion", "mensaje": "a"}]}'
        )
        MockModel.return_value.generate_content.return_value = respuesta

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="WARNING"):
            resultado = clasificar("algo")

        self.assertFalse(resultado.es_confiable)
        self.assertFalse(resultado.es_colaboracion)

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_json_malformado_degrada_a_no_reconocida(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = "esto no es json"
        MockModel.return_value.generate_content.return_value = respuesta

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="ERROR"):
            resultado = clasificar("algo")

        self.assertEqual(resultado.intencion, "no_reconocida")
        self.assertEqual(resultado.confianza, 0.0)

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_intencion_desconocida_degrada_en_vez_de_propagarse(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = '{"intencion": "horoscopo", "motivo": "x", "confianza": 0.99, "dominios": []}'
        MockModel.return_value.generate_content.return_value = respuesta

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="ERROR"):
            resultado = clasificar("algo")

        self.assertEqual(resultado.intencion, "no_reconocida")

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_un_fallo_del_modelo_no_lanza_excepcion(self, MockModel):
        MockModel.return_value.generate_content.side_effect = ConnectionError("caido")

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="ERROR"):
            resultado = clasificar("algo")

        self.assertEqual(resultado.intencion, "no_reconocida")

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_la_confianza_se_acota_al_rango_valido(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = '{"intencion": "entrenamiento", "motivo": "x", "confianza": 7, "dominios": []}'
        MockModel.return_value.generate_content.return_value = respuesta

        resultado = clasificar("algo")

        self.assertEqual(resultado.confianza, 1.0)


class TestRegistroDeAgentes(unittest.TestCase):
    """El catalogo y las intenciones validas se derivan del registro."""

    def test_los_dos_agentes_del_sprint_3_estan_registrados(self):
        self.assertIn("entrenamiento", registro_agentes.intenciones_con_agente())
        self.assertIn("nutricion", registro_agentes.intenciones_con_agente())

    def test_las_intenciones_genericas_son_validas_aunque_no_tengan_agente(self):
        validas = registro_agentes.intenciones_validas()
        for generica in ("mixta", "fuera_de_dominio", "no_reconocida"):
            self.assertIn(generica, validas)

    def test_el_catalogo_describe_a_cada_agente_registrado(self):
        catalogo = registro_agentes.catalogo_para_prompt()
        self.assertIn("Wellness Coach Agent", catalogo)
        self.assertIn("Nutrition Agent", catalogo)

    def test_resolver_devuelve_el_agente_correcto(self):
        self.assertEqual(registro_agentes.resolver("nutricion")["nombre"], "nutrition")
        self.assertEqual(
            registro_agentes.resolver("entrenamiento")["nombre"], "wellness_coach"
        )
        self.assertIsNone(registro_agentes.resolver("fuera_de_dominio"))

    def test_cada_agente_declara_una_etiqueta_para_la_consolidacion(self):
        """Sin etiqueta, una respuesta colaborativa no podria atribuir que
        aporto cada especialista."""
        for entrada in registro_agentes._AGENTES:
            self.assertTrue(entrada.get("etiqueta"))


if __name__ == "__main__":
    unittest.main()