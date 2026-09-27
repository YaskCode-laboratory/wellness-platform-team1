"""Pruebas de los adaptadores del registro de agentes (issues S3-03, S3-04).

QUE CUBRE ESTO QUE NO CUBRIA NINGUNA OTRA PRUEBA

test_registro.py verifica el ENRUTAMIENTO: que los agentes esten registrados y
que resolver() devuelva el destino correcto. Las pruebas de colaboracion de
test_orchestrator.py verifican la LOGICA DEL ORQUESTADOR usando agentes falsos
con MagicMock. Entre las dos queda un hueco: los adaptadores reales.

Y son precisamente la pieza que traduce SolicitudAgente hacia cada agente y
devuelve RespuestaAgente. Es el unico lugar del sistema que conoce la forma
concreta en que habla cada agente -- el Coach con las claves camelCase que
definio el Sprint 2, el Nutrition Agent con las suyas -- de modo que un
adaptador que lea una clave inexistente, invierta dos campos o se salte
mensaje_con_contexto() pasa inadvertido con toda la suite en verde.

Se mockea el agente, no el adaptador: lo que se verifica es la traduccion, sin
tocar Vertex AI, Firestore ni ChromaDB.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.orchestration.communication.contratos import SolicitudAgente
from src.orchestration.orchestrator import registro_agentes
from src.orchestration.orchestrator.agent import OrchestratorAgent
from src.orchestration.orchestrator.clasificador import Clasificacion, SubConsulta

# Respuesta del Nutrition Agent con su forma real: la que define
# NutritionAgent.responder(), no la que consume el orquestador.
RESPUESTA_NUTRICION = {
    "respuesta": "Durante una tirada larga, 30-60 g de carbohidratos por hora.",
    "fuentes": ["KB-006"],
    "fuentesInventadas": [],
    "fragmentosRecuperados": [
        {"doc_id": "KB-006", "seccion": "Carbohidratos en carrera", "similitud": 0.81}
    ],
    "cubierto": True,
}

RESPUESTA_COACH = {
    "respuesta": "Tu carga subio un 12%: conviene sostenerla una semana.",
    "herramientasInvocadas": [
        {"nombre": "consultar_progreso", "argumentos": {}},
        {"nombre": "consultar_base_conocimiento", "argumentos": {}},
    ],
    "herramientasDegradadas": [],
    "limiteAlcanzado": False,
    "reintentoUtilizado": False,
    "reintentoFallido": False,
}


def solicitud(mensaje="mensaje de prueba", contexto="", intencion="nutricion",
              user_id="u-1", paso=1) -> SolicitudAgente:
    return SolicitudAgente(
        traza_id="traza-de-prueba",
        user_id=user_id,
        mensaje=mensaje,
        intencion=intencion,
        contexto=contexto,
        paso=paso,
    )


class _ConRegistroLimpio(unittest.TestCase):
    """El registro memoriza instancias entre llamadas.

    Se limpia en cada caso para que ninguno arrastre el doble del anterior.
    """

    def setUp(self):
        registro_agentes._instancias.clear()

    def tearDown(self):
        registro_agentes._instancias.clear()


class TestAdaptadorDelNutritionAgent(_ConRegistroLimpio):

    @patch.object(registro_agentes, "NutritionAgent")
    def test_traduce_la_respuesta_a_RespuestaAgente(self, MockAgente):
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        respuesta = registro_agentes._invocar_nutrition(solicitud())

        self.assertEqual(respuesta.agente, "nutrition")
        self.assertEqual(respuesta.texto, RESPUESTA_NUTRICION["respuesta"])
        self.assertEqual(respuesta.fuentes, ["KB-006"])
        self.assertFalse(respuesta.degradado)
        self.assertFalse(respuesta.fallo)
        self.assertEqual(
            respuesta.detalle["fragmentos_recuperados"],
            RESPUESTA_NUTRICION["fragmentosRecuperados"],
        )
        self.assertTrue(respuesta.detalle["cubierto"])

    @patch.object(registro_agentes, "NutritionAgent")
    def test_el_user_id_lo_toma_de_la_solicitud_y_no_del_texto(self, MockAgente):
        """El identificador lo inyecta el orquestador desde el contexto de la
        peticion: elimina por construccion que un mensaje pueda inducir a
        consultar datos de otro corredor."""
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        registro_agentes._invocar_nutrition(
            solicitud(user_id="u-42", mensaje="cuantos geles llevo?")
        )

        llamada = MockAgente.return_value.responder.call_args[0]
        self.assertEqual(llamada[0], "u-42")

    @patch.object(registro_agentes, "NutritionAgent")
    def test_entrega_el_mensaje_con_el_contexto_del_agente_anterior(self, MockAgente):
        """Es lo que convierte dos respuestas sueltas en colaboracion. Si el
        adaptador pasara solicitud.mensaje en vez de mensaje_con_contexto(),
        el encadenamiento se perderia justo en el ultimo paso, despues de que
        el orquestador lo hubiera preparado correctamente."""
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        registro_agentes._invocar_nutrition(
            solicitud(
                mensaje="y que como?",
                contexto="Wellness Coach Agent respondió:\nBaja el volumen un 20%.",
            )
        )

        entregado = MockAgente.return_value.responder.call_args[0][1]
        self.assertIn("y que como?", entregado)
        self.assertIn("Baja el volumen un 20%.", entregado)

    @patch.object(registro_agentes, "NutritionAgent")
    def test_sin_contexto_el_mensaje_viaja_intacto(self, MockAgente):
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        registro_agentes._invocar_nutrition(solicitud(mensaje="cuanta agua tomo?"))

        self.assertEqual(
            MockAgente.return_value.responder.call_args[0][1], "cuanta agua tomo?"
        )

    @patch.object(registro_agentes, "NutritionAgent")
    def test_no_declara_herramientas_porque_no_usa_tool_calling(self, MockAgente):
        """Vacia por diseno, no por dato ausente: recupera y responde en una
        sola llamada. Lo que consulto viaja en fuentes y en el detalle."""
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        respuesta = registro_agentes._invocar_nutrition(solicitud())

        self.assertEqual(respuesta.herramientas_invocadas, [])
        self.assertTrue(respuesta.fuentes)

    @patch.object(registro_agentes, "NutritionAgent")
    def test_una_cita_inventada_degrada(self, MockAgente):
        """Unico caso que degrada en este agente: afirma haber usado una
        fuente que nunca recibio, y eso anula la trazabilidad."""
        MockAgente.return_value.responder.return_value = {
            **RESPUESTA_NUTRICION,
            "fuentesInventadas": ["KB-999"],
        }

        respuesta = registro_agentes._invocar_nutrition(solicitud())

        self.assertTrue(respuesta.degradado)
        self.assertEqual(respuesta.detalle["fuentes_inventadas"], ["KB-999"])

    @patch.object(registro_agentes, "NutritionAgent")
    def test_un_vacio_de_cobertura_no_degrada(self, MockAgente):
        """La contraparte de la anterior, y la razon de que existan las dos:
        distinguirlas impide que la medicion de S3-06 cuente la conducta
        correcta como si fuera un fallo."""
        MockAgente.return_value.responder.return_value = {
            **RESPUESTA_NUTRICION,
            "respuesta": "La base de conocimiento no cubre suplementacion.",
            "fuentes": [],
            "cubierto": False,
        }

        respuesta = registro_agentes._invocar_nutrition(solicitud())

        self.assertFalse(respuesta.degradado)
        self.assertFalse(respuesta.detalle["cubierto"])


class TestAdaptadorDelWellnessCoach(_ConRegistroLimpio):

    @patch.object(registro_agentes, "WellnessCoachAgent")
    def test_traduce_las_claves_camelCase_del_ciclo_react(self, MockAgente):
        MockAgente.return_value.conversar.return_value = RESPUESTA_COACH

        respuesta = registro_agentes._invocar_wellness_coach(
            solicitud(intencion="entrenamiento", mensaje="como voy?")
        )

        self.assertEqual(respuesta.agente, "wellness_coach")
        self.assertIn("12%", respuesta.texto)
        self.assertEqual(
            respuesta.herramientas_invocadas,
            ["consultar_progreso", "consultar_base_conocimiento"],
        )
        self.assertFalse(respuesta.degradado)
        self.assertFalse(respuesta.fallo)

    @patch.object(registro_agentes, "WellnessCoachAgent")
    def test_las_fuentes_quedan_vacias_por_limitacion_conocida(self, MockAgente):
        """No es que no cite: cita dentro de su prosa, gobernado por las
        reglas de citacion de su prompt, pero su contrato de salida no las
        devuelve como lista. Extraerlas exige cambiar el ciclo ReAct del
        Sprint 2. Se fija aqui para que el dia que cambie, la prueba avise."""
        MockAgente.return_value.conversar.return_value = RESPUESTA_COACH

        respuesta = registro_agentes._invocar_wellness_coach(
            solicitud(intencion="entrenamiento")
        )

        self.assertEqual(respuesta.fuentes, [])

    @patch.object(registro_agentes, "WellnessCoachAgent")
    def test_entrega_el_mensaje_con_el_contexto_del_agente_anterior(self, MockAgente):
        MockAgente.return_value.conversar.return_value = RESPUESTA_COACH

        registro_agentes._invocar_wellness_coach(
            solicitud(
                intencion="entrenamiento",
                mensaje="como ajusto la carga?",
                contexto="Nutrition Agent respondió:\n30-60 g por hora.",
                paso=2,
            )
        )

        entregado = MockAgente.return_value.conversar.call_args[0][1]
        self.assertIn("como ajusto la carga?", entregado)
        self.assertIn("30-60 g por hora.", entregado)

    @patch.object(registro_agentes, "WellnessCoachAgent")
    def test_una_herramienta_caida_degrada_pero_no_es_fallo(self, MockAgente):
        """La distincion que sostiene _contexto_para_el_siguiente(): el Coach
        respondio algo util aunque una capacidad fallara, asi que su texto SI
        sirve de contexto al siguiente agente."""
        MockAgente.return_value.conversar.return_value = {
            **RESPUESTA_COACH,
            "respuesta": "No pude consultar el clima, pero con tu carga actual...",
            "herramientasInvocadas": [{"nombre": "consultar_clima", "argumentos": {}}],
            "herramientasDegradadas": ["consultar_clima"],
            "reintentoUtilizado": True,
            "reintentoFallido": True,
        }

        respuesta = registro_agentes._invocar_wellness_coach(
            solicitud(intencion="entrenamiento")
        )

        self.assertTrue(respuesta.degradado)
        self.assertFalse(respuesta.fallo)
        self.assertEqual(respuesta.detalle["herramientas_degradadas"], ["consultar_clima"])


class TestInvocacionDesdeElOrquestador(_ConRegistroLimpio):
    """La cadena completa: clasificacion -> registro -> adaptador real -> traza.

    Es la comprobacion que pide el criterio de aceptacion de S3-03 ("puede ser
    invocado mediante el Orchestrator Agent"). Las demas pruebas verifican el
    adaptador aislado; esta verifica que el orquestador llegue hasta el y que
    lo que devuelva aparezca en la traza que ve el cliente.

    El registro de delegaciones se sustituye por un doble para que la suite no
    escriba en Firestore.
    """

    @patch.object(registro_agentes, "NutritionAgent")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_una_consulta_de_nutricion_llega_al_Nutrition_Agent(
        self, mock_clasificar, MockAgente
    ):
        mock_clasificar.return_value = Clasificacion(
            intencion="nutricion", motivo="pregunta por su alimentacion", confianza=0.9
        )
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        traza = OrchestratorAgent(registro=MagicMock()).procesar(
            "u-7", "cuantos carbohidratos por hora?"
        )

        MockAgente.return_value.responder.assert_called_once_with(
            "u-7", "cuantos carbohidratos por hora?"
        )
        self.assertEqual(traza["agentes"], ["nutrition"])
        self.assertTrue(traza["delegado"])
        self.assertIn("30-60 g", traza["respuesta"])
        self.assertEqual(traza["fuentes"], ["KB-006"])
        self.assertFalse(traza["degradado"])

    @patch.object(registro_agentes, "WellnessCoachAgent")
    @patch.object(registro_agentes, "NutritionAgent")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_una_consulta_mixta_recorre_los_dos_adaptadores_reales(
        self, mock_clasificar, MockNutricion, MockCoach
    ):
        """El escenario de colaboracion con los adaptadores de verdad, no con
        dobles del registro: es lo que demuestra el protocolo de punta a punta
        sin depender de servicios externos."""
        mock_clasificar.return_value = Clasificacion(
            intencion="mixta",
            motivo="alimentacion y carga",
            confianza=0.9,
            subconsultas=[
                SubConsulta(dominio="nutricion", mensaje="que como antes?"),
                SubConsulta(dominio="entrenamiento", mensaje="como ajusto la carga?"),
            ],
        )
        MockNutricion.return_value.responder.return_value = RESPUESTA_NUTRICION
        MockCoach.return_value.conversar.return_value = RESPUESTA_COACH

        traza = OrchestratorAgent(registro=MagicMock()).procesar(
            "u-7", "que como antes de la tirada larga y como ajusto la carga?"
        )

        self.assertEqual(traza["agentes"], ["nutrition", "wellness_coach"])
        self.assertTrue(traza["colaboracion"])

        # Cada agente recibio su sub-consulta, no el mensaje completo.
        self.assertEqual(traza["pasos"][0]["mensajeDelegado"], "que como antes?")
        self.assertEqual(traza["pasos"][1]["mensajeDelegado"], "como ajusto la carga?")

        # Y el segundo recibio lo que respondio el primero.
        entregado_al_coach = MockCoach.return_value.conversar.call_args[0][1]
        self.assertIn("30-60 g", entregado_al_coach)

    @patch.object(registro_agentes, "NutritionAgent")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_el_wellness_coach_no_se_construye_para_una_consulta_de_nutricion(
        self, mock_clasificar, MockAgente
    ):
        """La construccion perezosa no es solo una optimizacion: abre
        conexiones a Firestore y Vertex AI. Si delegar en nutricion
        construyera tambien el Coach, cada consulta pagaria las dos."""
        mock_clasificar.return_value = Clasificacion(
            intencion="nutricion", motivo="hidratacion", confianza=0.9
        )
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        OrchestratorAgent(registro=MagicMock()).procesar("u-7", "cuanta agua tomo?")

        self.assertIn("nutrition", registro_agentes._instancias)
        self.assertNotIn("wellness_coach", registro_agentes._instancias)

    @patch.object(registro_agentes, "NutritionAgent")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_un_fallo_del_agente_real_se_degrada_sin_tumbar_la_solicitud(
        self, mock_clasificar, MockAgente
    ):
        """El mismo patron de S2-04, un nivel mas arriba: la proteccion vive
        en el punto de despacho, asi que cualquier agente registrado despues
        la hereda sin escribir nada."""
        mock_clasificar.return_value = Clasificacion(
            intencion="nutricion", motivo="alimentacion", confianza=0.9
        )
        MockAgente.return_value.responder.side_effect = RuntimeError("Vertex caido")

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            traza = OrchestratorAgent(registro=MagicMock()).procesar(
                "u-7", "que como antes de entrenar?"
            )

        self.assertTrue(traza["degradado"])
        self.assertTrue(traza["pasos"][0]["fallo"])
        self.assertNotIn("Vertex caido", traza["respuesta"])


if __name__ == "__main__":
    unittest.main()
