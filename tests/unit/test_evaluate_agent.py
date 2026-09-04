import unittest

from scripts.evaluation.evaluate_agent import _coincide_herramientas, calcular_metricas


class TestCoincidenciaHerramientas(unittest.TestCase):

    def test_coincide_exacto(self):
        self.assertTrue(_coincide_herramientas(
            ["consultar_clima"],
            [{"nombre": "consultar_clima", "argumentos": {}}],
        ))

    def test_coincide_subconjunto_no_exige_cantidad_exacta(self):
        """Invocar la herramienta esperada mas otras adicionales sigue
        contando como acierto -- Gemini puede razonar de mas de una forma
        valida."""
        self.assertTrue(_coincide_herramientas(
            ["consultar_clima"],
            [
                {"nombre": "consultar_progreso_objetivo", "argumentos": {}},
                {"nombre": "consultar_clima", "argumentos": {}},
            ],
        ))

    def test_no_coincide_si_falta_una_esperada(self):
        self.assertFalse(_coincide_herramientas(
            ["consultar_clima", "consultar_progreso_objetivo"],
            [{"nombre": "consultar_clima", "argumentos": {}}],
        ))

    def test_sin_herramientas_esperadas_y_ninguna_invocada_coincide(self):
        self.assertTrue(_coincide_herramientas([], []))

    def test_sin_herramientas_esperadas_pero_invoco_alguna_igual_coincide(self):
        """El criterio de coincidencia solo exige que lo esperado este
        presente, no prohibe herramientas de mas -- eso se revisa
        manualmente en el analisis cualitativo, no en la metrica automatica."""
        self.assertTrue(_coincide_herramientas(
            [],
            [{"nombre": "consultar_clima", "argumentos": {}}],
        ))


class TestCalcularMetricas(unittest.TestCase):

    def test_lista_vacia(self):
        self.assertEqual(calcular_metricas([]), {"total_casos": 0})

    def test_metricas_agregadas(self):
        resultados = [
            {"tipo": "tool_calling", "coincidencia_herramientas": True, "limite_alcanzado": False, "latencia_ms": 1000},
            {"tipo": "tool_calling", "coincidencia_herramientas": False, "limite_alcanzado": False, "latencia_ms": 2000},
            {"tipo": "rag", "coincidencia_herramientas": True, "limite_alcanzado": False, "latencia_ms": 1500},
            {"tipo": "react", "coincidencia_herramientas": True, "limite_alcanzado": True, "latencia_ms": 3000},
        ]
        metricas = calcular_metricas(resultados)

        self.assertEqual(metricas["total_casos"], 4)
        self.assertEqual(metricas["tasa_acierto_herramientas"], 0.75)
        self.assertEqual(metricas["casos_con_limite_alcanzado"], 1)
        self.assertEqual(metricas["latencia_promedio_ms"], 1875)
        self.assertEqual(metricas["por_tipo"]["tool_calling"], {"total": 2, "aciertos": 1})
        self.assertEqual(metricas["por_tipo"]["rag"], {"total": 1, "aciertos": 1})


if __name__ == "__main__":
    unittest.main()