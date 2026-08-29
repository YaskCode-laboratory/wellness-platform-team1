"""Pruebas unitarias del cliente Firestore perezoso.

Verifican que la conexión real a Firestore no se dispara al importar el
módulo, sino solo en el primer uso efectivo. No requieren credenciales
de GCP: se mockea init_firebase() en vez de conectarse de verdad.
"""

import unittest
from unittest.mock import patch

import src.database.firestore_client as firestore_client_module


class TestClienteFirestorePerezoso(unittest.TestCase):

    def test_no_conecta_al_importar(self):
        """Si llegamos hasta aquí sin excepción, importar no disparó la conexión."""
        self.assertIsNone(firestore_client_module.db._cliente)

    @patch("src.database.firestore_client.init_firebase")
    def test_conecta_solo_en_el_primer_uso(self, mock_init):
        mock_init.return_value = "cliente-falso"
        proxy = firestore_client_module._ClienteFirestorePerezoso()

        mock_init.assert_not_called()
        resultado = proxy._obtener_cliente()

        mock_init.assert_called_once()
        self.assertEqual(resultado, "cliente-falso")

    @patch("src.database.firestore_client.init_firebase")
    def test_cachea_el_cliente_tras_la_primera_conexion(self, mock_init):
        mock_init.return_value = "cliente-falso"
        proxy = firestore_client_module._ClienteFirestorePerezoso()

        proxy._obtener_cliente()
        proxy._obtener_cliente()

        mock_init.assert_called_once()


if __name__ == "__main__":
    unittest.main()