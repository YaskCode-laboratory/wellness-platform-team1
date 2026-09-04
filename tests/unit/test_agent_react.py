import unittest
from unittest.mock import MagicMock, patch

from src.agents.wellness_coach.agent import (
    MAX_ITERACIONES_HERRAMIENTAS,
    WellnessCoachAgent,
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


class TestWellnessCoachAgentReAct(unittest.TestCase):

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

    def test_respuesta_directa_sin_herramientas(self):
        self.mock_chat.send_message.return_value = FakeResponse(text="Hola, en que puedo ayudarte?")

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "hola")

        self.assertEqual(resultado["respuesta"], "Hola, en que puedo ayudarte?")
        self.assertEqual(resultado["herramientasInvocadas"], [])
        self.assertFalse(resultado["limiteAlcanzado"])
        self.mock_chat.send_message.assert_called_once_with("hola")
        self.MockMemoria.return_value.agregar_turno.assert_any_call("u1", "usuario", "hola")
        self.MockMemoria.return_value.agregar_turno.assert_any_call(
            "u1", "agente", "Hola, en que puedo ayudarte?"
        )

    def test_una_herramienta_luego_respuesta_final(self):
        self.mock_despachar.return_value = {"disponible": True, "temperaturaC": 31.0}
        self.mock_chat.send_message.side_effect = [
            FakeResponse(function_calls=[FakeFunctionCall("consultar_clima", {})]),
            FakeResponse(text="Hace calor, hidrata bien antes de correr."),
        ]

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "deberia correr hoy?")

        self.assertEqual(resultado["respuesta"], "Hace calor, hidrata bien antes de correr.")
        self.assertEqual(len(resultado["herramientasInvocadas"]), 1)
        self.assertEqual(resultado["herramientasInvocadas"][0]["nombre"], "consultar_clima")
        self.assertFalse(resultado["limiteAlcanzado"])
        self.mock_despachar.assert_called_once_with(
            "consultar_clima", {}, user_id="u1", ciudad="Maracaibo"
        )
        self.assertEqual(self.mock_chat.send_message.call_count, 2)

    def test_supera_limite_de_iteraciones(self):
        self.mock_despachar.return_value = {"algo": "resultado"}
        siempre_pide_herramienta = FakeResponse(
            function_calls=[FakeFunctionCall("consultar_progreso_objetivo", {})]
        )
        self.mock_chat.send_message.side_effect = [siempre_pide_herramienta] * (
            MAX_ITERACIONES_HERRAMIENTAS + 1
        )

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "como voy?")

        self.assertTrue(resultado["limiteAlcanzado"])
        self.assertEqual(len(resultado["herramientasInvocadas"]), MAX_ITERACIONES_HERRAMIENTAS)
        self.assertIn("No pude completar", resultado["respuesta"])

    def test_multiples_herramientas_en_un_solo_turno(self):
        self.mock_despachar.side_effect = [
            {"progresoPct": 60.0},
            {"disponible": True, "temperaturaC": 20.0},
        ]
        self.mock_chat.send_message.side_effect = [
            FakeResponse(function_calls=[
                FakeFunctionCall("consultar_progreso_objetivo", {}),
                FakeFunctionCall("consultar_clima", {}),
            ]),
            FakeResponse(text="Vas bien y el clima acompaña, puedes entrenar tranquilo."),
        ]

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "puedo entrenar fuerte hoy?")

        self.assertEqual(len(resultado["herramientasInvocadas"]), 2)
        self.assertEqual(self.mock_despachar.call_count, 2)


class TestWellnessCoachAgentReintentoSinInvocar(unittest.TestCase):
    """Cubre el hallazgo C detectado por Jose en la verificacion real:
    el modelo narra o atribuye contenido a una herramienta sin invocarla."""

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

    def test_reintenta_y_logra_invocar_tras_el_empuje(self):
        """Replica el caso AG-05 real: el modelo anuncia consulta, se le
        empuja una vez, y en el reintento si invoca la herramienta."""
        self.mock_despachar.return_value = {
            "fragmentos": [{"doc_id": "KB-004", "texto": "..."}],
        }
        self.mock_chat.send_message.side_effect = [
            FakeResponse(text="Voy a consultar la base de conocimiento sobre esto."),
            FakeResponse(function_calls=[
                FakeFunctionCall("consultar_base_conocimiento", {"consulta": "dolor de rodilla"})
            ]),
            FakeResponse(text="Segun la base de conocimiento, el dolor de rodilla puede deberse a..."),
        ]

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "me duele la rodilla, que puede ser?")

        self.assertTrue(resultado["reintentoUtilizado"])
        self.assertFalse(resultado["reintentoFallido"])
        self.assertEqual(len(resultado["herramientasInvocadas"]), 1)
        self.assertIn("Segun la base de conocimiento", resultado["respuesta"])
        self.assertEqual(self.mock_chat.send_message.call_count, 3)
        self.mock_chat.send_message.assert_any_call("me duele la rodilla, que puede ser?")

    def test_reintento_agotado_usa_respuesta_de_respaldo(self):
        """Replica la manifestacion 2 real: el modelo atribuye contenido a
        la KB sin invocarla, ni siquiera despues del empuje. No se debe
        confiar en ese texto -- se sustituye por una respuesta honesta."""
        self.mock_chat.send_message.side_effect = [
            FakeResponse(text="Segun la informacion que tengo en nuestra base de conocimiento, el dolor de rodilla es comun."),
            FakeResponse(text="Segun la base de conocimiento, esto suele deberse a sobrecarga."),
        ]

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "me duele la rodilla, que puede ser?")

        self.assertTrue(resultado["reintentoUtilizado"])
        self.assertTrue(resultado["reintentoFallido"])
        self.assertEqual(resultado["herramientasInvocadas"], [])
        self.assertIn("No logré completar", resultado["respuesta"])
        self.mock_despachar.assert_not_called()
        self.assertEqual(self.mock_chat.send_message.call_count, 2)

    def test_no_reintenta_si_ya_invoco_una_herramienta_antes(self):
        """Citar 'segun la base de conocimiento' DESPUES de haber invocado
        la herramienta en el mismo turno es legitimo, no debe disparar
        un reintento innecesario."""
        self.mock_despachar.return_value = {"fragmentos": []}
        self.mock_chat.send_message.side_effect = [
            FakeResponse(function_calls=[
                FakeFunctionCall("consultar_base_conocimiento", {"consulta": "tapering"})
            ]),
            FakeResponse(text="Segun la base de conocimiento, el tapering dura entre 1 y 3 semanas."),
        ]

        agente = WellnessCoachAgent()
        resultado = agente.conversar("u1", "que es el tapering?")

        self.assertFalse(resultado["reintentoUtilizado"])
        self.assertFalse(resultado["reintentoFallido"])
        self.assertEqual(len(resultado["herramientasInvocadas"]), 1)
        self.assertEqual(self.mock_chat.send_message.call_count, 2)


if __name__ == "__main__":
    unittest.main()