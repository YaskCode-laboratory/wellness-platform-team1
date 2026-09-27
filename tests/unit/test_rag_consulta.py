"""Pruebas de la sintesis de la consulta de recuperacion del modo RAG.

El agente no recibe preguntas, recibe datos: construir_consulta traduce el
estado del corredor a lenguaje natural para poder recuperar semanticamente. La
calidad de la recuperacion esta limitada por la calidad de esa consulta -- si
describe mal la situacion, se recupera conocimiento correcto pero irrelevante.

Estas pruebas cubren sobre todo la incorporacion de las notas del corredor,
agregada en el Sprint 3 tras observar que el modo RAG esquivaba un sintoma
reportado porque la consulta nunca lo mencionaba.
"""

import unittest

from src.rag.pipeline.rag_pipeline import (
    DIAS_NOTAS_RELEVANTES,
    MAX_CARACTERES_NOTAS,
    construir_consulta,
    notas_recientes,
)


def sesion(dias, notas=None, km=8):
    return {"diasAtras": dias, "notas": notas, "distanciaKm": km}


class TestNotasRecientes(unittest.TestCase):

    def test_sin_notas_devuelve_cadena_vacia(self):
        self.assertEqual(notas_recientes([sesion(1), sesion(3)]), "")

    def test_una_nota_vacia_o_en_blanco_se_ignora(self):
        self.assertEqual(notas_recientes([sesion(1, ""), sesion(2, "   ")]), "")

    def test_recoge_la_nota_de_una_sesion_reciente(self):
        salida = notas_recientes([sesion(2, "Sentí un poco de mareo al final")])

        self.assertIn("mareo", salida)

    def test_descarta_notas_antiguas(self):
        """Una molestia anotada hace dos meses no describe el estado actual y
        desviaria la recuperacion hacia conocimiento que ya no aplica."""
        salida = notas_recientes([
            sesion(DIAS_NOTAS_RELEVANTES + 1, "Me dolía la rodilla"),
            sesion(60, "Tuve una fascitis"),
        ])

        self.assertEqual(salida, "")

    def test_conserva_las_del_limite_de_la_ventana(self):
        salida = notas_recientes([sesion(DIAS_NOTAS_RELEVANTES, "Piernas pesadas")])

        self.assertIn("Piernas pesadas", salida)

    def test_ordena_de_la_mas_reciente_a_la_mas_antigua(self):
        """Al recortar por longitud se conserva lo ultimo que escribio el
        corredor, que es lo que mejor describe su estado actual."""
        salida = notas_recientes([
            sesion(7, "hace una semana"),
            sesion(1, "ayer"),
            sesion(4, "hace cuatro dias"),
        ])

        self.assertTrue(salida.startswith("ayer"))
        self.assertLess(salida.index("hace cuatro dias"), salida.index("hace una semana"))

    def test_se_recorta_para_no_dominar_la_consulta(self):
        """Las notas son texto libre. Una consulta dominada por prosa del
        corredor recupera peor que una que describe su estado: deben matizar
        la busqueda, no sustituirla."""
        larga = "x" * 500
        salida = notas_recientes([sesion(1, larga)])

        self.assertLessEqual(len(salida), MAX_CARACTERES_NOTAS)

    def test_una_sesion_sin_diasAtras_no_rompe(self):
        """enriquecer_sesiones marca 'desconocido' cuando la fecha no es
        parseable."""
        salida = notas_recientes([{"diasAtras": "desconocido", "notas": "algo"}])

        self.assertEqual(salida, "")


class TestConsultaCompleta(unittest.TestCase):

    def test_las_notas_llegan_a_la_consulta(self):
        consulta = construir_consulta(
            nivel="intermedio", current_km=14, previous_km=5, cambio=180.0,
            goals=[], sessions=[sesion(1, "Sentí un poco de mareo al final")],
        )

        self.assertIn("el corredor reporta", consulta)
        self.assertIn("mareo", consulta)

    def test_sin_notas_la_consulta_no_cambia_de_forma(self):
        consulta = construir_consulta(
            nivel="intermedio", current_km=14, previous_km=5, cambio=180.0,
            goals=[], sessions=[sesion(1)],
        )

        self.assertNotIn("el corredor reporta", consulta)
        self.assertIn("corredor de nivel intermedio", consulta)

    def test_el_estado_numerico_sigue_estando(self):
        """Las notas se suman al estado, no lo reemplazan: la recuperacion
        sigue necesitando saber de que volumen y que variacion se habla."""
        consulta = construir_consulta(
            nivel="intermedio", current_km=14, previous_km=5, cambio=180.0,
            goals=[], sessions=[sesion(1, "mareo")],
        )

        self.assertIn("volumen semanal actual 14 km", consulta)
        self.assertIn("variación de carga 180.0%", consulta)
        self.assertIn("progresión de carga", consulta)


if __name__ == "__main__":
    unittest.main()
