"""Pruebas del Orchestrator Agent (issue S3-02).

Se separan en tres clases segun que se esta probando:

- TestDecisionDeDelegacion cubre _decidir(), que es logica pura: no toca red
  ni modelo, asi que se prueba sin mockear nada mas que la clasificacion de
  entrada. Es la politica completa de cuando delegar y cuando no.
- TestProcesarSolicitud cubre el flujo de punta a punta con el clasificador y
  el registro mockeados.
- TestClasificador cubre la degradacion del clasificador ante respuestas
  malformadas del modelo.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.orchestration.orchestrator.agent import (
    RESPUESTA_AGENTE_FALLO,
    RESPUESTA_DOMINIO_SIN_AGENTE,
    RESPUESTA_FUERA_DE_DOMINIO,
    RESPUESTA_MIXTA_NO_SOPORTADA,
    RESPUESTA_NO_RECONOCIDA,
    OrchestratorAgent,
)
from src.orchestration.orchestrator.clasificador import Clasificacion, clasificar


def clasificacion(intencion, confianza=0.9, motivo="motivo de prueba"):
    return Clasificacion(intencion=intencion, motivo=motivo, confianza=confianza)


AGENTE_FALSO = {
    "nombre": "wellness_coach",
    "intencion": "entrenamiento",
    "titulo": "Wellness Coach Agent",
    "descripcion": "...",
    "invocador": None,
}


class TestDecisionDeDelegacion(unittest.TestCase):
    """La politica de delegacion, aislada de la red y del modelo."""

    def setUp(self):
        self.orq = OrchestratorAgent()

    @patch("src.orchestration.orchestrator.agent.resolver")
    def test_delega_cuando_la_intencion_tiene_agente(self, mock_resolver):
        mock_resolver.return_value = AGENTE_FALSO

        decision = self.orq._decidir(clasificacion("entrenamiento"))

        self.assertIs(decision["agente"], AGENTE_FALSO)
        self.assertIsNone(decision["motivo_no_delegacion"])

    def test_no_delega_con_confianza_insuficiente(self):
        """Una delegacion equivocada es peor que una pregunta de mas: el
        corredor recibiria una respuesta del dominio incorrecto sin saber
        que hubo un error."""
        decision = self.orq._decidir(clasificacion("entrenamiento", confianza=0.3))

        self.assertIsNone(decision["agente"])
        self.assertEqual(decision["motivo_no_delegacion"], "confianza_insuficiente")
        self.assertEqual(decision["texto"], RESPUESTA_NO_RECONOCIDA)

    def test_la_confianza_se_evalua_antes_que_la_intencion(self):
        """Aunque la intencion tenga agente disponible, una clasificacion poco
        confiable no debe delegarse. El orden de las comprobaciones importa."""
        with patch("src.orchestration.orchestrator.agent.resolver") as mock_resolver:
            mock_resolver.return_value = AGENTE_FALSO
            decision = self.orq._decidir(clasificacion("entrenamiento", confianza=0.49))

        self.assertIsNone(decision["agente"])
        mock_resolver.assert_not_called()

    def test_fuera_de_dominio_redirige_sin_delegar(self):
        decision = self.orq._decidir(clasificacion("fuera_de_dominio"))

        self.assertIsNone(decision["agente"])
        self.assertEqual(decision["texto"], RESPUESTA_FUERA_DE_DOMINIO)

    def test_no_reconocida_pide_aclaracion(self):
        decision = self.orq._decidir(clasificacion("no_reconocida"))

        self.assertIsNone(decision["agente"])
        self.assertEqual(decision["texto"], RESPUESTA_NO_RECONOCIDA)

    def test_mixta_se_reconoce_pero_no_se_atiende_todavia(self):
        """La delegacion multiple corresponde a S3-04. Hasta entonces el
        orquestador lo declara en vez de responder a medias sin avisar."""
        decision = self.orq._decidir(clasificacion("mixta"))

        self.assertIsNone(decision["agente"])
        self.assertEqual(decision["texto"], RESPUESTA_MIXTA_NO_SOPORTADA)
        self.assertEqual(
            decision["motivo_no_delegacion"], "delegacion_multiple_no_implementada"
        )

    def test_dominio_de_la_plataforma_sin_agente_no_es_fuera_de_dominio(self):
        """Distincion que justifica _DOMINIOS_SIN_AGENTE: una pregunta de
        nutricion pertenece a la plataforma aunque no tenga agente. Tratarla
        como tema ajeno le diria al corredor algo falso."""
        decision = self.orq._decidir(clasificacion("nutricion"))

        self.assertIsNone(decision["agente"])
        self.assertEqual(decision["texto"], RESPUESTA_DOMINIO_SIN_AGENTE)
        self.assertEqual(decision["motivo_no_delegacion"], "dominio_sin_agente")
        self.assertNotEqual(decision["texto"], RESPUESTA_FUERA_DE_DOMINIO)


class TestProcesarSolicitud(unittest.TestCase):
    """Flujo completo, con clasificador y registro mockeados."""

    def setUp(self):
        self.orq = OrchestratorAgent()
        self.invocador = MagicMock(
            return_value={
                "texto": "Esta semana llevas 14 km de tu meta de 25 km.",
                "herramientas_invocadas": ["consultar_progreso_objetivo"],
                "degradado": False,
                "detalle_agente": {"limite_alcanzado": False},
            }
        )
        self.agente = dict(AGENTE_FALSO, invocador=self.invocador)

    @patch("src.orchestration.orchestrator.agent.resolver")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_delegacion_exitosa_devuelve_la_respuesta_del_agente(
        self, mock_clasificar, mock_resolver
    ):
        mock_clasificar.return_value = clasificacion("entrenamiento")
        mock_resolver.return_value = self.agente

        resultado = self.orq.procesar("u1", "como voy esta semana?")

        self.assertTrue(resultado["delegado"])
        self.assertEqual(resultado["agente"], "wellness_coach")
        self.assertIn("14 km", resultado["respuesta"])
        self.assertEqual(
            resultado["herramientasInvocadas"], ["consultar_progreso_objetivo"]
        )
        self.invocador.assert_called_once_with("u1", "como voy esta semana?")

    @patch("src.orchestration.orchestrator.agent.resolver")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_la_traza_permite_reconstruir_la_solicitud(
        self, mock_clasificar, mock_resolver
    ):
        """S3-06 exige poder responder que se entendio, a quien se delego y
        por que, y cuanto costo cada paso."""
        mock_clasificar.return_value = clasificacion(
            "entrenamiento", motivo="pregunta por su progreso semanal"
        )
        mock_resolver.return_value = self.agente

        resultado = self.orq.procesar("u1", "como voy?")

        self.assertTrue(resultado["trazaId"])
        self.assertEqual(resultado["intencion"], "entrenamiento")
        self.assertEqual(
            resultado["motivoClasificacion"], "pregunta por su progreso semanal"
        )
        self.assertEqual(resultado["agente"], "wellness_coach")
        self.assertIn("clasificacionMs", resultado["latencias"])
        self.assertIn("agenteMs", resultado["latencias"])
        self.assertIn("totalMs", resultado["latencias"])

    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_sin_delegacion_no_se_invoca_ningun_agente(self, mock_clasificar):
        mock_clasificar.return_value = clasificacion("fuera_de_dominio")

        resultado = self.orq.procesar("u1", "que pelicula me recomiendas?")

        self.assertFalse(resultado["delegado"])
        self.assertIsNone(resultado["agente"])
        self.assertEqual(resultado["respuesta"], RESPUESTA_FUERA_DE_DOMINIO)
        self.assertEqual(resultado["herramientasInvocadas"], [])
        self.assertEqual(resultado["latencias"]["agenteMs"], 0)
        self.invocador.assert_not_called()

    @patch("src.orchestration.orchestrator.agent.resolver")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_un_fallo_del_agente_no_tumba_la_solicitud(
        self, mock_clasificar, mock_resolver
    ):
        """Misma decision que la correccion S2-04 tomo para el despacho de
        herramientas, un nivel mas arriba: el punto por donde pasan todas las
        invocaciones a agentes es donde hay que protegerlas."""
        mock_clasificar.return_value = clasificacion("entrenamiento")
        self.invocador.side_effect = ConnectionError("Vertex AI no responde")
        mock_resolver.return_value = self.agente

        with self.assertLogs("src.orchestration.orchestrator.agent", level="ERROR"):
            resultado = self.orq.procesar("u1", "como voy?")

        self.assertTrue(resultado["delegado"])
        self.assertTrue(resultado["degradado"])
        self.assertEqual(resultado["respuesta"], RESPUESTA_AGENTE_FALLO)

    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_un_fallo_del_clasificador_pide_aclaracion(self, mock_clasificar):
        """clasificar() nunca lanza: degrada a no_reconocida con confianza
        cero, que el orquestador traduce en una peticion de aclaracion."""
        mock_clasificar.return_value = Clasificacion(
            intencion="no_reconocida", motivo="el clasificador no respondio", confianza=0.0
        )

        resultado = self.orq.procesar("u1", "algo")

        self.assertFalse(resultado["delegado"])
        self.assertEqual(resultado["respuesta"], RESPUESTA_NO_RECONOCIDA)


class TestClasificador(unittest.TestCase):
    """Degradacion del clasificador ante respuestas inesperadas del modelo."""

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_clasificacion_valida_se_devuelve_tal_cual(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = (
            '{"intencion": "entrenamiento", "motivo": "pregunta por su carga", '
            '"confianza": 0.92}'
        )
        MockModel.return_value.generate_content.return_value = respuesta

        resultado = clasificar("puedo entrenar fuerte hoy?")

        self.assertEqual(resultado.intencion, "entrenamiento")
        self.assertEqual(resultado.confianza, 0.92)
        self.assertTrue(resultado.es_confiable)

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_json_malformado_degrada_a_no_reconocida(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = "esto no es json"
        MockModel.return_value.generate_content.return_value = respuesta

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="ERROR"):
            resultado = clasificar("algo")

        self.assertEqual(resultado.intencion, "no_reconocida")
        self.assertEqual(resultado.confianza, 0.0)
        self.assertFalse(resultado.es_confiable)

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_intencion_desconocida_degrada_en_vez_de_propagarse(self, MockModel):
        """El enum del esquema deberia impedirlo, pero si el modelo devolviera
        una intencion que el orquestador no sabe resolver, degradar es mejor
        que delegar a ciegas."""
        respuesta = MagicMock()
        respuesta.text = '{"intencion": "horoscopo", "motivo": "x", "confianza": 0.99}'
        MockModel.return_value.generate_content.return_value = respuesta

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="ERROR"):
            resultado = clasificar("algo")

        self.assertEqual(resultado.intencion, "no_reconocida")
        self.assertEqual(resultado.confianza, 0.0)

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_un_fallo_del_modelo_no_lanza_excepcion(self, MockModel):
        MockModel.return_value.generate_content.side_effect = ConnectionError("caido")

        with self.assertLogs("src.orchestration.orchestrator.clasificador", level="ERROR"):
            resultado = clasificar("algo")

        self.assertEqual(resultado.intencion, "no_reconocida")

    @patch("src.orchestration.orchestrator.clasificador.GenerativeModel")
    def test_la_confianza_se_acota_al_rango_valido(self, MockModel):
        respuesta = MagicMock()
        respuesta.text = '{"intencion": "entrenamiento", "motivo": "x", "confianza": 7}'
        MockModel.return_value.generate_content.return_value = respuesta

        resultado = clasificar("algo")

        self.assertEqual(resultado.confianza, 1.0)


if __name__ == "__main__":
    unittest.main()