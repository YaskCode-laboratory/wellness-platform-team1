"""Pruebas del marco de evaluacion multiagente (issue S3-06).

El Sprint 2 dejo una leccion cara sobre este tipo de codigo: su criterio de
coincidencia usaba subconjunto en vez de igualdad, lo que hacia imposible
detectar la sobreinvocacion y convertia en infalibles los casos que esperaban
cero herramientas. El defecto sobrevivio cinco corridas porque nadie probaba el
medidor, solo lo medido.

Estas pruebas cubren el medidor.
"""

import unittest

from scripts.evaluation.evaluate_multiagent import (
    _evaluar_delegacion,
    calcular_metricas,
)


def resultado(id_caso, tipo, esperados, invocados, intencion_ok=True,
              degradado=False, colaboracion=False, confianza=0.95,
              total_ms=1000, clasificacion_ms=200):
    return {
        "id": id_caso,
        "tipo": tipo,
        "intencion_coincide": intencion_ok,
        "confianza": confianza,
        "delegacion": _evaluar_delegacion(esperados, invocados),
        "colaboracion": colaboracion,
        "degradado": degradado,
        "latencias": {"totalMs": total_ms, "clasificacionMs": clasificacion_ms},
    }


class TestEvaluacionDeDelegacion(unittest.TestCase):
    """El criterio es igualdad de conjuntos, no subconjunto."""

    def test_delegacion_identica_es_exacta(self):
        d = _evaluar_delegacion(["nutrition"], ["nutrition"])

        self.assertTrue(d["exacta"])
        self.assertEqual(d["sobredelegacion"], [])
        self.assertEqual(d["subdelegacion"], [])

    def test_invocar_de_mas_no_es_acierto(self):
        """El defecto exacto que el marco del Sprint 2 no podia detectar."""
        d = _evaluar_delegacion(["nutrition"], ["nutrition", "wellness_coach"])

        self.assertFalse(d["exacta"])
        self.assertEqual(d["sobredelegacion"], ["wellness_coach"])
        self.assertEqual(d["subdelegacion"], [])

    def test_invocar_de_menos_no_es_acierto(self):
        d = _evaluar_delegacion(["nutrition", "wellness_coach"], ["nutrition"])

        self.assertFalse(d["exacta"])
        self.assertEqual(d["subdelegacion"], ["wellness_coach"])
        self.assertEqual(d["sobredelegacion"], [])

    def test_un_caso_que_espera_cero_agentes_puede_fallar(self):
        """Con criterio de subconjunto esto habria sido un acierto, porque el
        conjunto vacio es subconjunto de cualquier cosa. En el Sprint 2 eso
        hizo que dos casos fueran estructuralmente infalibles."""
        d = _evaluar_delegacion([], ["wellness_coach"])

        self.assertFalse(d["exacta"])
        self.assertEqual(d["sobredelegacion"], ["wellness_coach"])

    def test_no_delegar_cuando_no_se_espera_delegacion_es_acierto(self):
        d = _evaluar_delegacion([], [])

        self.assertTrue(d["exacta"])

    def test_el_orden_se_reporta_aparte_de_la_coincidencia(self):
        """Invocar a los agentes correctos en orden invertido no es un fallo de
        delegacion, pero si cambia que respuesta sirve de contexto a cual. Son
        dos problemas distintos y se miden por separado."""
        d = _evaluar_delegacion(
            ["nutrition", "wellness_coach"], ["wellness_coach", "nutrition"]
        )

        self.assertTrue(d["exacta"])
        self.assertFalse(d["orden_esperado"])


class TestMetricas(unittest.TestCase):

    def test_la_tasa_cuenta_solo_las_delegaciones_exactas(self):
        resultados = [
            resultado("MA-01", "sin_delegacion", [], []),
            resultado("MA-02", "nutricion", ["nutrition"], ["nutrition"]),
            resultado("MA-03", "entrenamiento", ["wellness_coach"], []),
        ]

        m = calcular_metricas(resultados)

        self.assertEqual(m["total_casos"], 3)
        self.assertEqual(m["tasa_delegacion_exacta"], round(2 / 3, 3))

    def test_sobredelegacion_y_subdelegacion_se_reportan_por_separado(self):
        """Sumarlas ocultaria cual de los dos problemas esta ocurriendo:
        subdelegar deja una parte sin responder, sobredelegar duplica latencia
        y alarga la respuesta sin aportar."""
        resultados = [
            resultado("MA-01", "nutricion", ["nutrition"], ["nutrition", "wellness_coach"]),
            resultado("MA-02", "colaboracion", ["nutrition", "wellness_coach"], ["nutrition"]),
        ]

        m = calcular_metricas(resultados)

        self.assertEqual(m["casos_con_sobredelegacion"], ["MA-01"])
        self.assertEqual(m["casos_con_subdelegacion"], ["MA-02"])

    def test_registra_los_valores_de_confianza_observados(self):
        """Si la lista trae un solo valor, el modelo no esta calibrando y el
        umbral que decide si delegar es una salvaguarda que nunca se activa."""
        resultados = [
            resultado("MA-01", "a", [], [], confianza=0.95),
            resultado("MA-02", "b", [], [], confianza=0.9),
            resultado("MA-03", "c", [], [], confianza=0.95),
        ]

        m = calcular_metricas(resultados)

        self.assertEqual(m["valores_de_confianza_observados"], [0.9, 0.95])

    def test_desglosa_los_aciertos_por_tipo(self):
        resultados = [
            resultado("MA-01", "nutricion", ["nutrition"], ["nutrition"]),
            resultado("MA-02", "nutricion", ["nutrition"], []),
            resultado("MA-03", "colaboracion",
                      ["nutrition", "wellness_coach"], ["nutrition", "wellness_coach"]),
        ]

        m = calcular_metricas(resultados)

        self.assertEqual(m["por_tipo"]["nutricion"], {"total": 2, "aciertos": 1})
        self.assertEqual(m["por_tipo"]["colaboracion"], {"total": 1, "aciertos": 1})

    def test_un_conjunto_vacio_no_rompe_el_calculo(self):
        self.assertEqual(calcular_metricas([]), {"total_casos": 0})


if __name__ == "__main__":
    unittest.main()