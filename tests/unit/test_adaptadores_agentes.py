"""Pruebas de los adaptadores del registro de agentes (issue S3-03).

QUE CUBRE ESTO QUE NO CUBRIA test_registro.py

test_registro.py verifica que los agentes esten registrados y que resolver()
devuelva el destino correcto. Eso comprueba el ENRUTAMIENTO, no la INVOCACION:
con esas pruebas en verde, un adaptador que lee una clave inexistente de la
respuesta del agente, o que invierte dos campos, pasa inadvertido.

El criterio de aceptacion de S3-03 dice que el agente "puede ser invocado
mediante el Orchestrator Agent". Los adaptadores son precisamente la pieza que
hace posible esa invocacion: traducen entre el contrato del orquestador y el
que cada agente definio por su cuenta. Son el unico lugar del sistema que
conoce la forma concreta en que habla cada agente, de modo que un error ahi no
lo detecta ninguna otra prueba.

Se mockea el agente, no el adaptador: lo que se verifica es la traduccion.

Las pruebas de colaboracion de S3-04 usan agentes falsos con MagicMock, lo cual
verifica la logica del orquestador pero deja estos adaptadores sin cubrir. Con
este archivo, la cadena completa -- orquestador -> adaptador real -> contrato
del agente -- queda comprobada sin depender de Vertex AI, Firestore ni
ChromaDB.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.orchestration.orchestrator import registro_agentes
from src.orchestration.orchestrator.agent import OrchestratorAgent
from src.orchestration.orchestrator.clasificador import Clasificacion

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


def clasificacion(intencion, confianza=0.9):
    return Clasificacion(
        intencion=intencion, motivo="motivo de prueba", confianza=confianza
    )


class TestAdaptadorDelNutritionAgent(unittest.TestCase):
    """_invocar_nutrition traduce la respuesta del agente al contrato interno."""

    def setUp(self):
        # El registro memoriza instancias entre pruebas. Se limpia para que
        # cada caso construya la suya y ninguna arrastre el mock de la
        # anterior.
        registro_agentes._instancias.clear()

    def tearDown(self):
        registro_agentes._instancias.clear()

    @patch.object(registro_agentes, "NutritionAgent")
    def test_traduce_la_respuesta_al_contrato_del_orquestador(self, MockAgente):
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        resultado = registro_agentes._invocar_nutrition("u-1", "cuantos geles llevo?")

        self.assertEqual(resultado["texto"], RESPUESTA_NUTRICION["respuesta"])
        self.assertEqual(resultado["detalle_agente"]["fuentes"], ["KB-006"])
        self.assertEqual(
            resultado["detalle_agente"]["fragmentos_recuperados"],
            RESPUESTA_NUTRICION["fragmentosRecuperados"],
        )
        self.assertTrue(resultado["detalle_agente"]["cubierto"])

    @patch.object(registro_agentes, "NutritionAgent")
    def test_el_mensaje_y_el_user_id_llegan_intactos_al_agente(self, MockAgente):
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        registro_agentes._invocar_nutrition("u-42", "que desayuno antes de correr?")

        MockAgente.return_value.responder.assert_called_once_with(
            "u-42", "que desayuno antes de correr?"
        )

    @patch.object(registro_agentes, "NutritionAgent")
    def test_no_declara_herramientas_porque_este_agente_no_usa_tool_calling(
        self, MockAgente
    ):
        """Vacia por diseno, no por dato ausente: el agente recupera y responde
        en una sola llamada. Lo que consulto viaja en fragmentos_recuperados."""
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        resultado = registro_agentes._invocar_nutrition("u-1", "cuanta agua tomo?")

        self.assertEqual(resultado["herramientas_invocadas"], [])
        self.assertTrue(resultado["detalle_agente"]["fragmentos_recuperados"])

    @patch.object(registro_agentes, "NutritionAgent")
    def test_una_cita_inventada_si_degrada(self, MockAgente):
        """Es el unico caso que degrada: el agente afirma haber usado una
        fuente que nunca recibio, y eso anula la trazabilidad."""
        MockAgente.return_value.responder.return_value = {
            **RESPUESTA_NUTRICION,
            "fuentesInventadas": ["KB-999"],
        }

        resultado = registro_agentes._invocar_nutrition("u-1", "cuanto sodio repongo?")

        self.assertTrue(resultado["degradado"])
        self.assertEqual(resultado["detalle_agente"]["fuentes_inventadas"], ["KB-999"])

    @patch.object(registro_agentes, "NutritionAgent")
    def test_un_vacio_de_cobertura_no_degrada(self, MockAgente):
        """La contraparte de la prueba anterior, y la razon de que existan las
        dos: distinguirlas es lo que impide que la medicion de S3-06 cuente la
        conducta correcta como si fuera un fallo."""
        MockAgente.return_value.responder.return_value = {
            **RESPUESTA_NUTRICION,
            "respuesta": "La base de conocimiento no cubre suplementacion.",
            "fuentes": [],
            "cubierto": False,
        }

        resultado = registro_agentes._invocar_nutrition("u-1", "que suplementos tomo?")

        self.assertFalse(resultado["degradado"])
        self.assertFalse(resultado["detalle_agente"]["cubierto"])


class TestAdaptadorDelWellnessCoach(unittest.TestCase):
    """El Coach habla el contrato del Sprint 2, con otras claves."""

    def setUp(self):
        registro_agentes._instancias.clear()

    def tearDown(self):
        registro_agentes._instancias.clear()

    @patch.object(registro_agentes, "WellnessCoachAgent")
    def test_traduce_las_claves_camelCase_del_ciclo_react(self, MockAgente):
        MockAgente.return_value.conversar.return_value = {
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

        resultado = registro_agentes._invocar_wellness_coach("u-1", "como voy?")

        self.assertIn("12%", resultado["texto"])
        self.assertEqual(
            resultado["herramientas_invocadas"],
            ["consultar_progreso", "consultar_base_conocimiento"],
        )
        self.assertFalse(resultado["degradado"])

    @patch.object(registro_agentes, "WellnessCoachAgent")
    def test_una_herramienta_degradada_marca_la_respuesta(self, MockAgente):
        """Aqui si es degradacion: una capacidad fallo. Es la distincion que el
        hallazgo D del Sprint 2 fijo para el clima caido."""
        MockAgente.return_value.conversar.return_value = {
            "respuesta": "No pude consultar el clima, pero con tu carga actual...",
            "herramientasInvocadas": [{"nombre": "consultar_clima", "argumentos": {}}],
            "herramientasDegradadas": ["consultar_clima"],
            "limiteAlcanzado": False,
            "reintentoUtilizado": True,
            "reintentoFallido": True,
        }

        resultado = registro_agentes._invocar_wellness_coach("u-1", "salgo hoy?")

        self.assertTrue(resultado["degradado"])
        self.assertEqual(
            resultado["detalle_agente"]["herramientas_degradadas"], ["consultar_clima"]
        )


class TestInvocacionDesdeElOrquestador(unittest.TestCase):
    """La cadena completa: clasificacion -> registro -> adaptador real -> traza.

    Es la comprobacion que pide el criterio de aceptacion de S3-03. Las demas
    pruebas verifican el adaptador aislado; esta verifica que el orquestador
    llegue hasta el y que lo que devuelva aparezca en la traza que ve el
    cliente.

    El registro de delegaciones se sustituye por un doble en cada caso para
    que la suite no escriba en Firestore.
    """

    def setUp(self):
        registro_agentes._instancias.clear()

    def tearDown(self):
        registro_agentes._instancias.clear()

    @patch.object(registro_agentes, "NutritionAgent")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_una_consulta_de_nutricion_llega_al_Nutrition_Agent(
        self, mock_clasificar, MockAgente
    ):
        mock_clasificar.return_value = clasificacion("nutricion")
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        orquestador = OrchestratorAgent()
        orquestador.registro = MagicMock()
        traza = orquestador.procesar("u-7", "cuantos carbohidratos por hora?")

        MockAgente.return_value.responder.assert_called_once_with(
            "u-7", "cuantos carbohidratos por hora?"
        )
        self.assertEqual(traza["agente"], "nutrition")
        self.assertTrue(traza["delegado"])
        self.assertIn("30-60 g", traza["respuesta"])
        self.assertFalse(traza["degradado"])

    @patch.object(registro_agentes, "NutritionAgent")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_el_wellness_coach_no_se_construye_para_una_consulta_de_nutricion(
        self, mock_clasificar, MockAgente
    ):
        """La construccion perezosa no es solo una optimizacion: abre
        conexiones a Firestore y Vertex AI. Si delegar en nutricion
        construyera tambien el Coach, cada consulta pagaria las dos."""
        mock_clasificar.return_value = clasificacion("nutricion")
        MockAgente.return_value.responder.return_value = RESPUESTA_NUTRICION

        orquestador = OrchestratorAgent()
        orquestador.registro = MagicMock()
        orquestador.procesar("u-7", "cuanta agua tomo en carrera?")

        self.assertIn("nutrition", registro_agentes._instancias)
        self.assertNotIn("wellness_coach", registro_agentes._instancias)

    @patch.object(registro_agentes, "NutritionAgent")
    @patch("src.orchestration.orchestrator.agent.clasificar")
    def test_un_fallo_del_agente_real_se_degrada_sin_tumbar_la_solicitud(
        self, mock_clasificar, MockAgente
    ):
        """El mismo patron de S2-04, un nivel mas arriba: la proteccion vive en
        el punto de despacho, asi que cualquier agente registrado despues la
        hereda sin escribir nada."""
        mock_clasificar.return_value = clasificacion("nutricion")
        MockAgente.return_value.responder.side_effect = RuntimeError("Vertex caido")

        orquestador = OrchestratorAgent()
        orquestador.registro = MagicMock()
        traza = orquestador.procesar("u-7", "que como antes de entrenar?")

        self.assertTrue(traza["degradado"])
        self.assertTrue(traza["delegado"])
        self.assertNotIn("Vertex caido", traza["respuesta"])


if __name__ == "__main__":
    unittest.main()
