# tests/unit/test_registro.py
import unittest
from unittest.mock import patch

from src.agents.wellness_coach.tools.registro import despachar, obtener_tool_vertexai


class TestRegistro(unittest.TestCase):

    def test_declara_las_cuatro_herramientas(self):
        tool = obtener_tool_vertexai()
        nombres = {d.name for d in tool.function_declarations}
        self.assertEqual(nombres, {
            "consultar_historial_sesiones",
            "consultar_progreso_objetivo",
            "consultar_clima",
            "consultar_base_conocimiento",
        })

    @patch("src.agents.wellness_coach.tools.registro.consultar_historial_sesiones")
    def test_despacha_historial_con_argumentos(self, mock_fn):
        mock_fn.return_value = {"sesiones": []}
        despachar("consultar_historial_sesiones", {"n": 3}, user_id="u1")
        mock_fn.assert_called_once_with("u1", n=3)

    @patch("src.agents.wellness_coach.tools.registro.consultar_clima")
    def test_despacha_clima_con_ciudad_inyectada_no_del_modelo(self, mock_fn):
        mock_fn.return_value = {"disponible": True}
        despachar("consultar_clima", {}, user_id="u1", ciudad="Maracaibo")
        mock_fn.assert_called_once_with("Maracaibo")

    def test_herramienta_desconocida_lanza_error(self):
        with self.assertRaises(ValueError):
            despachar("herramienta_inventada", {}, user_id="u1")


if __name__ == "__main__":
    unittest.main()