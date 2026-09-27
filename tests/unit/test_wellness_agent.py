"""Pruebas unitarias de WellnessAgent.

Cubren únicamente las rutas que no requieren Vertex AI ni credenciales de
GCP: el caso de un corredor sin sesiones registradas, tanto en analyze()
como en comparar(). Las rutas que sí generan una recomendación real
dependen de Gemini y del pipeline RAG, y se evalúan como parte del issue
#15 (evaluación del comportamiento del agente), no aquí.
"""

import unittest
from unittest.mock import patch

from src.agents.wellness.agent import WellnessAgent


class TestWellnessAgentSinSesiones(unittest.TestCase):

    def setUp(self):
        patcher = patch(
            "src.agents.wellness.agent.RepositorioCorredor.cargar_estado_corredor"
        )
        self.mock_cargar_estado = patcher.start()
        self.addCleanup(patcher.stop)
        self.mock_cargar_estado.return_value = None

        # Evita que analyze() intente escribir en Firestore real si algún
        # día esta prueba se extiende más allá del caso "sin sesiones".
        patcher_db = patch("src.agents.wellness.agent.db")
        patcher_db.start()
        self.addCleanup(patcher_db.stop)

    def test_analyze_sin_sesiones(self):
        agente = WellnessAgent()
        resultado = agente.analyze("usuario-sin-datos")

        self.assertEqual(resultado["userId"], "usuario-sin-datos")
        self.assertIn("Sin sesiones registradas", resultado["message"])

    def test_comparar_sin_sesiones(self):
        agente = WellnessAgent()
        resultado = agente.comparar("usuario-sin-datos")

        self.assertEqual(resultado["userId"], "usuario-sin-datos")
        self.assertIn("Sin sesiones registradas", resultado["message"])

    def test_analyze_modo_invalido_lanza_error(self):
        agente = WellnessAgent()
        with self.assertRaises(ValueError):
            agente.analyze("cualquier-usuario", mode="modo-que-no-existe")


if __name__ == "__main__":
    unittest.main()