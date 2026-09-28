"""Pruebas unitarias de RepositorioCorredor.

Usan mocks de Firestore: no requieren credenciales de GCP ni conexión de
red. Verifican la lógica de negocio (parseo de perfil, cálculo de carga
semanal, filtrado de objetivos activos) de forma aislada de la
infraestructura real.
"""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.data.repositorio_corredor import PerfilCorredor, RepositorioCorredor
# Se usa hoy() y no fecha_de_hoy(). Son la misma fecha en el portatil del equipo
# y distintas en el runner de CI, que corre en UTC: comparar contra fecha_de_hoy()
# hacia que estas pruebas pasaran o fallaran segun la hora y la maquina. La
# prueba tiene que compartir la definicion de "hoy" con el codigo que verifica.
from src.utils.fechas import hoy as fecha_de_hoy



def _doc(datos: dict, existe: bool = True) -> MagicMock:
    """Construye un mock de DocumentSnapshot de Firestore."""
    doc = MagicMock()
    doc.exists = existe
    doc.to_dict.return_value = datos
    return doc


class TestPerfilCorredor(unittest.TestCase):

    def test_perfil_completo(self):
        perfil = PerfilCorredor.desde_documento("u1", {
            "email": "julio@example.com",
            "nombre": "Julio",
            "peso": 70.5,
            "edad": 29,
            "nivel": "intermedio",
            "ciudad": "Maracaibo",
        })
        self.assertEqual(perfil.ciudad, "Maracaibo")
        self.assertEqual(perfil.nivel, "intermedio")

    def test_perfil_sin_ciudad_no_falla(self):
        """Perfiles creados antes de agregar 'ciudad' no deben romper el parseo."""
        perfil = PerfilCorredor.desde_documento("u2", {
            "email": "ana@example.com",
            "nombre": "Ana",
        })
        self.assertIsNone(perfil.ciudad)
        self.assertEqual(perfil.nivel, "no declarado")


class TestRepositorioCorredor(unittest.TestCase):

    def setUp(self):
        patcher = patch("src.data.repositorio_corredor.db")
        self.mock_db = patcher.start()
        self.addCleanup(patcher.stop)

    def test_obtener_perfil_existente(self):
        self.mock_db.collection.return_value.document.return_value.get.return_value = _doc({
            "nombre": "Julio", "nivel": "principiante", "ciudad": "Maracaibo",
        })
        repo = RepositorioCorredor()
        perfil = repo.obtener_perfil("u1")
        self.assertEqual(perfil.nombre, "Julio")
        self.assertEqual(perfil.ciudad, "Maracaibo")

    def test_obtener_perfil_inexistente(self):
        self.mock_db.collection.return_value.document.return_value.get.return_value = _doc(
            {}, existe=False
        )
        repo = RepositorioCorredor()
        perfil = repo.obtener_perfil("desconocido")
        self.assertEqual(perfil.uid, "desconocido")
        self.assertEqual(perfil.nivel, "no declarado")

    def test_calcular_carga_semanal(self):
        hoy = fecha_de_hoy()
        lunes = hoy - timedelta(days=hoy.weekday())

        sesiones_falsas = [
            _doc({"fecha": lunes.isoformat(), "distanciaKm": 5}),
            _doc({"fecha": (lunes + timedelta(days=2)).isoformat(), "distanciaKm": 8}),
            _doc({"fecha": (lunes - timedelta(days=3)).isoformat(), "distanciaKm": 6}),
        ]
        self.mock_db.collection.return_value.where.return_value.stream.return_value = (
            sesiones_falsas
        )

        repo = RepositorioCorredor()
        actual, anterior = repo.calcular_carga_semanal("u1")

        self.assertEqual(actual, 13.0)   # 5 + 8, ambas dentro de la semana actual
        self.assertEqual(anterior, 6.0)  # la de hace 3 días cae en la semana previa

    def test_objetivos_solo_activos(self):
        objetivos_falsos = [
            _doc({"kmMeta": 30, "activo": True}),
            _doc({"kmMeta": 20, "activo": False}),
            _doc({"kmMeta": 40}),  # sin campo 'activo' -> se asume activo
        ]
        self.mock_db.collection.return_value.where.return_value.stream.return_value = (
            objetivos_falsos
        )

        repo = RepositorioCorredor()
        activos = repo.obtener_objetivos_activos("u1")

        self.assertEqual(len(activos), 2)

    def test_cargar_estado_sin_sesiones_devuelve_none(self):
        self.mock_db.collection.return_value.where.return_value.stream.return_value = []
        repo = RepositorioCorredor()
        self.assertIsNone(repo.cargar_estado_corredor("u1"))


if __name__ == "__main__":
    unittest.main()