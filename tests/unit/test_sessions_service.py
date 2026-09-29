"""Pruebas del servicio de sesiones y objetivos.

Cubren tres cosas: que la propiedad de los documentos se compruebe siempre,
que las consultas no necesiten indices compuestos, y que las reglas de
validacion de objetivos dependan del tipo.
"""

import unittest
from unittest.mock import MagicMock, patch

from src.services import sessions_service
from src.services.sessions_service import NoAutorizado, NoEncontrado, OperacionInvalida


def doc(datos, existe=True):
    d = MagicMock()
    d.exists = existe
    d.to_dict.return_value = datos
    return d


def sesion(id_, fecha, km=10, user="u1"):
    return {"id": id_, "userId": user, "fecha": fecha, "distanciaKm": km,
            "tiempoSeg": 3000, "ritmoMin": 5.0}


class TestListadoSinIndicesCompuestos(unittest.TestCase):
    """El orden y el filtro de 'activo' se resuelven en memoria.

    Firestore exige un indice compuesto para combinar 'where' con 'order_by' o
    con un segundo 'where' sobre otro campo, y crearlo es configuracion manual
    en la consola que no queda versionada: quien clone el repositorio se
    encontraria con consultas que fallan hasta que alguien recuerde crearlo.
    """

    @patch("src.services.sessions_service.db")
    def test_las_sesiones_se_ordenan_en_memoria_no_en_la_consulta(self, mock_db):
        consulta = mock_db.collection.return_value.where.return_value
        consulta.stream.return_value = [
            doc(sesion("a", "2026-09-10")),
            doc(sesion("c", "2026-09-16")),
            doc(sesion("b", "2026-09-14")),
        ]

        salida = sessions_service.listar_sesiones("u1")

        self.assertEqual([s["id"] for s in salida["sessions"]], ["c", "b", "a"])
        consulta.order_by.assert_not_called()

    @patch("src.services.sessions_service.db")
    def test_se_filtra_por_un_solo_campo(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = []

        sessions_service.listar_sesiones("u1")

        self.assertEqual(mock_db.collection.return_value.where.call_count, 1)

    @patch("src.services.sessions_service.db")
    def test_el_listado_se_recorta_al_limite(self, mock_db):
        muchas = [doc(sesion(str(i), f"2026-01-{i:02d}")) for i in range(1, 32)] * 2
        mock_db.collection.return_value.where.return_value.stream.return_value = muchas

        salida = sessions_service.listar_sesiones("u1")

        self.assertEqual(len(salida["sessions"]), sessions_service.LIMITE_SESIONES)

    @patch("src.services.sessions_service.db")
    def test_los_objetivos_inactivos_se_descartan_en_memoria(self, mock_db):
        consulta = mock_db.collection.return_value.where.return_value
        consulta.stream.return_value = [
            doc({"id": "g1", "userId": "u1", "activo": True}),
            doc({"id": "g2", "userId": "u1", "activo": False}),
        ]

        salida = sessions_service.listar_objetivos("u1")

        self.assertEqual([g["id"] for g in salida["goals"]], ["g1"])
        self.assertEqual(mock_db.collection.return_value.where.call_count, 1)


class TestPropiedadDeLosDocumentos(unittest.TestCase):
    """La comprobacion vive en un solo sitio para que no se pueda olvidar.

    Es la unica barrera que impide que un corredor lea o modifique datos de
    otro conociendo su identificador.
    """

    @patch("src.services.sessions_service.db")
    def test_un_documento_inexistente_no_se_devuelve(self, mock_db):
        mock_db.collection.return_value.document.return_value.get.return_value = doc(
            None, existe=False
        )

        with self.assertRaises(NoEncontrado):
            sessions_service.obtener_sesion("u1", "s1")

    @patch("src.services.sessions_service.db")
    def test_un_documento_de_otro_corredor_no_se_devuelve(self, mock_db):
        mock_db.collection.return_value.document.return_value.get.return_value = doc(
            sesion("s1", "2026-09-16", user="otro")
        )

        with self.assertRaises(NoAutorizado):
            sessions_service.obtener_sesion("u1", "s1")

    @patch("src.services.sessions_service.db")
    def test_no_se_puede_modificar_una_sesion_ajena(self, mock_db):
        ref = mock_db.collection.return_value.document.return_value
        ref.get.return_value = doc(sesion("s1", "2026-09-16", user="otro"))

        with self.assertRaises(NoAutorizado):
            sessions_service.actualizar_sesion("u1", "s1", {"distanciaKm": 99})

        ref.update.assert_not_called()

    @patch("src.services.sessions_service.db")
    def test_no_se_puede_eliminar_una_sesion_ajena(self, mock_db):
        ref = mock_db.collection.return_value.document.return_value
        ref.get.return_value = doc(sesion("s1", "2026-09-16", user="otro"))

        with self.assertRaises(NoAutorizado):
            sessions_service.eliminar_sesion("u1", "s1")

        ref.delete.assert_not_called()


class TestActualizacionDeSesiones(unittest.TestCase):

    @patch("src.services.sessions_service.db")
    def test_los_campos_no_enviados_no_se_sobreescriben(self, mock_db):
        """Un PUT parcial no debe borrar lo que no viene en el cuerpo."""
        ref = mock_db.collection.return_value.document.return_value
        ref.get.return_value = doc(sesion("s1", "2026-09-16"))

        sessions_service.actualizar_sesion(
            "u1", "s1", {"distanciaKm": 12.0, "notas": None, "fcPromedio": None}
        )

        enviado = ref.update.call_args[0][0]
        self.assertEqual(enviado["distanciaKm"], 12.0)
        self.assertNotIn("notas", enviado)
        self.assertNotIn("fcPromedio", enviado)
        self.assertIn("updatedAt", enviado)


class TestObjetivos(unittest.TestCase):
    """Los campos obligatorios dependen del tipo, asi que la validacion no
    puede vivir solo en el modelo de entrada."""

    @patch("src.services.sessions_service.db")
    def test_un_objetivo_semanal_exige_kmMeta(self, mock_db):
        with self.assertRaises(OperacionInvalida):
            sessions_service.crear_objetivo({"userId": "u1", "tipo": "semanal"})

        mock_db.collection.return_value.document.return_value.set.assert_not_called()

    @patch("src.services.sessions_service.db")
    def test_un_objetivo_de_largo_plazo_exige_distancia_y_fecha(self, mock_db):
        with self.assertRaises(OperacionInvalida):
            sessions_service.crear_objetivo({
                "userId": "u1", "tipo": "largo_plazo", "distanciaObjetivoKm": 21,
            })

    @patch("src.services.sessions_service.db")
    def test_un_tipo_desconocido_se_rechaza(self, mock_db):
        with self.assertRaises(OperacionInvalida):
            sessions_service.crear_objetivo({"userId": "u1", "tipo": "mensual"})

    @patch("src.services.sessions_service.db")
    def test_un_objetivo_semanal_valido_se_guarda_activo(self, mock_db):
        salida = sessions_service.crear_objetivo({
            "userId": "u1", "tipo": "semanal", "kmMeta": 25,
        })

        guardado = mock_db.collection.return_value.document.return_value.set.call_args[0][0]
        self.assertTrue(guardado["activo"])
        self.assertEqual(guardado["kmMeta"], 25)
        self.assertIn("createdAt", guardado)
        self.assertEqual(salida["goal"], guardado)

    @patch("src.services.sessions_service.db")
    def test_eliminar_un_objetivo_es_una_baja_logica(self, mock_db):
        """Las metricas historicas y las recomendaciones pasadas se calcularon
        contra objetivos que pueden haber sido dados de baja; borrarlos dejaria
        esas referencias sin destino."""
        ref = mock_db.collection.return_value.document.return_value
        ref.get.return_value = doc({"id": "g1", "userId": "u1", "activo": True})

        sessions_service.eliminar_objetivo("u1", "g1")

        ref.delete.assert_not_called()
        enviado = ref.update.call_args[0][0]
        self.assertFalse(enviado["activo"])
        self.assertIn("deletedAt", enviado)


if __name__ == "__main__":
    unittest.main()
