"""Pruebas de la correccion S2-04: degradacion generalizada de herramientas.

La revision del PR #25 observo que el hallazgo D protegio unicamente a
consultar_clima, dejando a las otras tres herramientas -- que dependen de
Firestore y ChromaDB -- capaces de tumbar la conversacion completa si su
infraestructura falla.

Estas pruebas cubren el punto de despacho, no las herramientas
individuales: lo que se verifica es que NINGUN fallo, venga de donde venga,
se propague hasta romper el turno.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.agents.wellness_coach.agent import (
    MENSAJE_HERRAMIENTA_NO_DISPONIBLE,
    WellnessCoachAgent,
    _despachar_con_degradacion,
)


class FakeFunctionCall:
    """Imita vertexai.generative_models.FunctionCall: .name y .args
    (mapping) son legibles, a diferencia de FunctionDeclaration/Tool."""

    def __init__(self, name, args):
        self.name = name
        self.args = args


class FakeCandidate:
    def __init__(self, function_calls=None):
        self.function_calls = function_calls or []


class FakeResponse:
    def __init__(self, function_calls=None, text=""):
        self.candidates = [FakeCandidate(function_calls)]
        self.text = text


class TestDespacharConDegradacion(unittest.TestCase):
    """Prueba la funcion de despacho aislada, sin el ciclo ReAct alrededor.

    Se prueba por separado del agente porque _despachar_con_degradacion no
    depende del estado de la conversacion: su contrato es puramente
    entrada -> (resultado, degradada), y verificarlo aqui deja las pruebas
    del agente enfocadas en el comportamiento del ciclo.
    """

    @patch("src.agents.wellness_coach.agent.despachar")
    def test_pasa_el_resultado_tal_cual_cuando_la_herramienta_funciona(self, mock_despachar):
        mock_despachar.return_value = {"disponible": True, "temperaturaC": 30.1}

        resultado, degradada = _despachar_con_degradacion(
            "consultar_clima", {}, user_id="u1", ciudad="Maracaibo"
        )

        self.assertEqual(resultado, {"disponible": True, "temperaturaC": 30.1})
        self.assertFalse(degradada)
        mock_despachar.assert_called_once_with(
            "consultar_clima", {}, user_id="u1", ciudad="Maracaibo"
        )

    @patch("src.agents.wellness_coach.agent.despachar")
    def test_un_fallo_de_firestore_produce_el_contrato_de_no_disponible(self, mock_despachar):
        """Reutiliza el contrato del hallazgo D en vez de inventar uno nuevo:
        el modelo ya demostro en AG-07 que sabe interpretar 'disponible:
        False' y seguir razonando con las fuentes que si respondieron."""
        mock_despachar.side_effect = ConnectionError("Firestore no responde")

        resultado, degradada = _despachar_con_degradacion(
            "consultar_progreso_objetivo", {}, user_id="u1", ciudad="Maracaibo"
        )

        self.assertTrue(degradada)
        self.assertFalse(resultado["disponible"])
        self.assertEqual(resultado["mensaje"], MENSAJE_HERRAMIENTA_NO_DISPONIBLE)

    @patch("src.agents.wellness_coach.agent.despachar")
    def test_un_fallo_de_chromadb_tambien_degrada(self, mock_despachar):
        mock_despachar.side_effect = RuntimeError("coleccion no encontrada")

        resultado, degradada = _despachar_con_degradacion(
            "consultar_base_conocimiento", {"consulta": "zona 2"}, user_id="u1", ciudad=None
        )

        self.assertTrue(degradada)
        self.assertFalse(resultado["disponible"])

    @patch("src.agents.wellness_coach.agent.despachar")
    def test_una_herramienta_alucinada_degrada_en_vez_de_romper(self, mock_despachar):
        """despachar() lanza ValueError si el modelo inventa un nombre de
        herramienta. De cara al corredor eso no es distinto de un fallo de
        infraestructura: la distincion vive en el log, no en la charla."""
        mock_despachar.side_effect = ValueError("Herramienta desconocida: 'consultar_horoscopo'")

        resultado, degradada = _despachar_con_degradacion(
            "consultar_horoscopo", {}, user_id="u1", ciudad=None
        )

        self.assertTrue(degradada)
        self.assertFalse(resultado["disponible"])

    @patch("src.agents.wellness_coach.agent.despachar")
    def test_registra_la_excepcion_real_en_el_log(self, mock_despachar):
        """El diagnostico necesita el tipo de excepcion y su traza; el
        modelo solo debe recibir el mensaje generico."""
        mock_despachar.side_effect = ConnectionError("Firestore no responde")

        with self.assertLogs("src.agents.wellness_coach.agent", level="ERROR") as captura:
            resultado, _ = _despachar_con_degradacion(
                "consultar_historial_sesiones", {"n": 5}, user_id="u1", ciudad=None
            )

        log_completo = "\n".join(captura.output)
        self.assertIn("consultar_historial_sesiones", log_completo)
        self.assertIn("Firestore no responde", log_completo)
        self.assertIn("ConnectionError", log_completo)
        self.assertNotIn("Firestore no responde", resultado["mensaje"])


class TestConversarDegradaSinRomperse(unittest.TestCase):
    """El criterio de aceptacion de S2-04: un fallo generico de cualquier
    herramienta no tumba la conversacion, produce una respuesta degradada
    y el flujo sigue con normalidad."""

    def setUp(self):
        p1 = patch("src.agents.wellness_coach.agent.RepositorioCorredor")
        p2 = patch("src.agents.wellness_coach.agent.MemoriaConversacional")
        p3 = patch("src.agents.wellness_coach.agent.GenerativeModel")
        p4 = patch("src.agents.wellness_coach.agent.obtener_tool_vertexai")
        p5 = patch("src.agents.wellness_coach.agent.despachar")

        self.MockRepo = p1.start()
        self.MockMemoria = p2.start()
        self.MockModel = p3.start()
        p4.start()
        self.mock_despachar = p5.start()

        for p in (p1, p2, p3, p4, p5):
            self.addCleanup(p.stop)

        self.mock_perfil = MagicMock(nivel="intermedio", ciudad="Maracaibo")
        self.MockRepo.return_value.obtener_perfil.return_value = self.mock_perfil
        self.MockMemoria.return_value.obtener_historial.return_value = []
        self.MockMemoria.return_value.formatear_para_prompt.return_value = "Sin conversacion previa."

        self.mock_chat = MagicMock()
        self.MockModel.return_value.start_chat.return_value = self.mock_chat

    def test_un_fallo_de_herramienta_no_tumba_la_conversacion(self):
        """Antes de S2-04 esta excepcion subia desde despachar() hasta el
        llamador y el turno moria entero -- exactamente lo que le paso al
        clima en la segunda medicion real antes del hallazgo D."""
        self.mock_despachar.side_effect = ConnectionError("Firestore no responde")
        self.mock_chat.send_message.side_effect = [
            FakeResponse(function_calls=[FakeFunctionCall("consultar_progreso_objetivo", {})]),
            FakeResponse(text="No pude consultar tu progreso ahora mismo, pero cuéntame cómo te sentiste."),
        ]

        agente = WellnessCoachAgent()

        with self.assertLogs("src.agents.wellness_coach.agent", level="ERROR"):
            resultado = agente.conversar("u1", "como voy esta semana?")

        self.assertIn("No pude consultar tu progreso", resultado["respuesta"])
        self.assertFalse(resultado["limiteAlcanzado"])
        self.assertEqual(len(resultado["herramientasInvocadas"]), 1)
        self.assertEqual(resultado["herramientasDegradadas"], ["consultar_progreso_objetivo"])

    def test_la_memoria_registra_el_turno_aunque_la_herramienta_falle(self):
        """La degradacion no debe dejar la conversacion a medias en
        Firestore: el turno se persiste igual que uno exitoso."""
        self.mock_despachar.side_effect = RuntimeError("ChromaDB caido")
        self.mock_chat.send_message.side_effect = [
            FakeResponse(function_calls=[
                FakeFunctionCall("consultar_base_conocimiento", {"consulta": "tapering"})
            ]),
            FakeResponse(text="Ese dato no pude consultarlo ahora."),
        ]

        agente = WellnessCoachAgent()

        with self.assertLogs("src.agents.wellness_coach.agent", level="ERROR"):
            agente.conversar("u1", "que es el tapering?")

        self.MockMemoria.return_value.agregar_turno.assert_any_call(
            "u1", "usuario", "que es el tapering?"
        )
        self.MockMemoria.return_value.agregar_turno.assert_any_call(
            "u1", "agente", "Ese dato no pude consultarlo ahora."
        )

    def test_una_herramienta_falla_y_la_otra_responde_en_el_mismo_turno(self):
        """El caso que mas importa: degradacion parcial. El agente conserva
        la fuente que si funciono en vez de perder el turno completo."""
        self.mock_despachar.side_effect = [
            {"progresoPct": 56.0, "kmSemanaActual": 14},
            ConnectionError("Open-Meteo 500"),
        ]
        self.mock_chat.send_message.side_effect = [
            FakeResponse(function_calls=[
                FakeFunctionCall("consultar_progreso_objetivo", {}),
                FakeFunctionCall("consultar_clima", {}),
            ]),
            FakeResponse(text="Llevas 14 km. El clima no pude consultarlo, revísalo antes de salir."),
        ]

        agente = WellnessCoachAgent()

        with self.assertLogs("src.agents.wellness_coach.agent", level="ERROR"):
            resultado = agente.conversar("u1", "puedo entrenar fuerte hoy?")

        self.assertEqual(len(resultado["herramientasInvocadas"]), 2)
        self.assertEqual(resultado["herramientasDegradadas"], ["consultar_clima"])
        self.assertIn("14 km", resultado["respuesta"])

    def test_un_turno_sano_no_reporta_degradacion(self):
        """Guarda contra el falso positivo: si nada falla, la lista queda
        vacia. Sin esto, la telemetria nueva podria estar siempre encendida
        y nadie lo notaria."""
        self.mock_despachar.return_value = {"disponible": True, "temperaturaC": 30.1}
        self.mock_chat.send_message.side_effect = [
            FakeResponse(function_calls=[FakeFunctionCall("consultar_clima", {})]),
            FakeResponse(text="Hace calor, hidrata bien."),
        ]

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "corro hoy?")

        self.assertEqual(resultado["herramientasDegradadas"], [])
        self.assertEqual(len(resultado["herramientasInvocadas"]), 1)


if __name__ == "__main__":
    unittest.main()