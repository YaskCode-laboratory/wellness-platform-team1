# tests/unit/test_tools.py
import unittest
from unittest.mock import MagicMock, patch

from src.agents.wellness_coach.tools.historial import (
    consultar_historial_sesiones,
    consultar_progreso_objetivo,
)
from src.agents.wellness_coach.tools.clima import consultar_clima


class TestHerramientaHistorial(unittest.TestCase):

    @patch("src.agents.wellness_coach.tools.historial._repo")
    def test_sin_sesiones(self, mock_repo):
        mock_repo.obtener_sesiones_recientes.return_value = []
        resultado = consultar_historial_sesiones("u1")
        self.assertEqual(resultado["sesiones"], [])
        self.assertIn("mensaje", resultado)

    @patch("src.agents.wellness_coach.tools.historial._repo")
    def test_con_sesiones(self, mock_repo):
        mock_repo.obtener_sesiones_recientes.return_value = [{"fecha": "2026-08-01", "distanciaKm": 5}]
        resultado = consultar_historial_sesiones("u1", n=3)
        self.assertEqual(resultado["total"], 1)
        mock_repo.obtener_sesiones_recientes.assert_called_once_with("u1", n=3)


class TestHerramientaProgreso(unittest.TestCase):

    @patch("src.agents.wellness_coach.tools.historial._repo")
    def test_sin_objetivos(self, mock_repo):
        mock_repo.calcular_carga_semanal.return_value = (10.0, 8.0)
        mock_repo.obtener_objetivos_activos.return_value = []
        resultado = consultar_progreso_objetivo("u1")
        self.assertIsNone(resultado["objetivo"])

    @patch("src.agents.wellness_coach.tools.historial._repo")
    def test_con_objetivo_calcula_progreso(self, mock_repo):
        mock_repo.calcular_carga_semanal.return_value = (15.0, 10.0)
        mock_repo.obtener_objetivos_activos.return_value = [{"kmMeta": 30, "activo": True}]
        resultado = consultar_progreso_objetivo("u1")
        self.assertEqual(resultado["progresoPct"], 50.0)


class TestHerramientaClima(unittest.TestCase):

    def test_sin_ciudad_no_llama_a_open_meteo(self):
        resultado = consultar_clima(None)
        self.assertFalse(resultado["disponible"])
        self.assertIn("no tiene ciudad", resultado["mensaje"])

    @patch("src.agents.wellness_coach.tools.clima.requests.get")
    def test_ciudad_no_encontrada(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": []}
        mock_get.return_value = mock_resp
        resultado = consultar_clima("CiudadInexistenteXYZ")
        self.assertFalse(resultado["disponible"])

    @patch("src.agents.wellness_coach.tools.clima.requests.get")
    def test_ciudad_encontrada_devuelve_clima(self, mock_get):
        geo_resp = MagicMock()
        geo_resp.json.return_value = {"results": [{"latitude": 10.6, "longitude": -71.6}]}
        forecast_resp = MagicMock()
        forecast_resp.json.return_value = {
            "current": {"temperature_2m": 31.5, "precipitation": 0.0, "wind_speed_10m": 12.0}
        }
        mock_get.side_effect = [geo_resp, forecast_resp]

        resultado = consultar_clima("Maracaibo")

        self.assertTrue(resultado["disponible"])
        self.assertEqual(resultado["temperaturaC"], 31.5)
        self.assertEqual(mock_get.call_count, 2)


if __name__ == "__main__":
    unittest.main()