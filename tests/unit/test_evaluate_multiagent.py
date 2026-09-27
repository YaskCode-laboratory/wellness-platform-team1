"""Pruebas del marco de evaluacion multiagente (issue S3-06).

El Sprint 2 dejo una leccion cara sobre este tipo de codigo: su criterio de
coincidencia usaba subconjunto en vez de igualdad, lo que hacia imposible
detectar la sobreinvocacion y convertia en infalibles los casos que esperaban
cero herramientas. El defecto sobrevivio cinco corridas porque nadie probaba el
medidor, solo lo medido.

Estas pruebas cubren el medidor.

La revision de S3-06 senalo un defecto de la misma familia: el golden set
declaraba un criterio_aprobacion por caso y ningun resultado decia si se
cumplia, de modo que la corrida terminaba con "100% de delegacion exacta"
mientras MA-05 incumplia su criterio. Se agrega la evaluacion explicita de
calidad, y aqui se prueba.
"""

import unittest

from scripts.evaluation.evaluate_multiagent import (
    _evaluar_calidad,
    _evaluar_comprobaciones,
    _evaluar_delegacion,
    calcular_metricas,
    fuentes_observadas,
)


def resultado(id_caso, tipo, esperados, invocados, intencion_ok=True,
              degradado=False, colaboracion=False, confianza=0.95,
              respuesta_ms=1000, clasificacion_ms=200, agentes_ms=800,
              veredicto="cumple", fallidas=()):
    return {
        "id": id_caso,
        "tipo": tipo,
        "intencion_coincide": intencion_ok,
        "confianza": confianza,
        "delegacion": _evaluar_delegacion(esperados, invocados),
        "colaboracion": colaboracion,
        "degradado": degradado,
        "calidad": {"veredicto": veredicto, "comprobaciones_fallidas": list(fallidas)},
        "latencia_respuesta_ms": respuesta_ms,
        "latencias_internas": {
            "totalMs": respuesta_ms - 5,
            "clasificacionMs": clasificacion_ms,
            "agentesMs": agentes_ms,
        },
    }


def traza(respuesta="respuesta de prueba", fuentes=(), herramientas=()):
    return {
        "respuesta": respuesta,
        "fuentes": list(fuentes),
        "herramientasInvocadas": list(herramientas),
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

    def test_la_calidad_separa_cumplen_no_cumplen_y_pendientes(self):
        """Tres categorias y no una tasa. Sumar los pendientes a cualquiera de
        los otros dos grupos esconderia precisamente lo que hay que ver: que
        falta juicio sobre esos casos."""
        resultados = [
            resultado("MA-01", "a", [], [], veredicto="cumple"),
            resultado("MA-02", "b", [], [], veredicto="no_cumple",
                      fallidas=["cita_fuentes"]),
            resultado("MA-03", "c", [], [], veredicto="pendiente"),
        ]

        m = calcular_metricas(resultados)

        self.assertEqual(m["calidad"]["cumplen"], ["MA-01"])
        self.assertEqual(m["calidad"]["no_cumplen"], ["MA-02"])
        self.assertEqual(m["calidad"]["pendientes_de_veredicto_manual"], ["MA-03"])
        self.assertEqual(m["calidad"]["tasa_calidad"], round(1 / 3, 3))
        self.assertEqual(m["calidad"]["fallos_por_comprobacion"],
                         {"cita_fuentes": ["MA-02"]})

    def test_la_latencia_publicada_es_la_medida_externa(self):
        """El tiempo total de respuesta es el medido alrededor de la llamada,
        no el que el orquestador se contabiliza a si mismo. Confundirlos fue
        la ambiguedad que la revision de S3-06 pidio aclarar."""
        resultados = [
            resultado("MA-01", "a", [], [], respuesta_ms=3000,
                      clasificacion_ms=900, agentes_ms=2000),
            resultado("MA-02", "b", [], [], respuesta_ms=5000,
                      clasificacion_ms=1100, agentes_ms=3800),
        ]

        m = calcular_metricas(resultados)

        self.assertEqual(m["latencia_respuesta_promedio_ms"], 4000)
        self.assertEqual(m["latencia_clasificacion_promedio_ms"], 1000)
        self.assertEqual(m["latencia_agentes_promedio_ms"], 2900)
        self.assertNotIn("latencia_total_promedio_ms", m)


class TestFuentesObservadas(unittest.TestCase):
    """Los dos agentes citan distinto y hay que mirar los dos caminos."""

    def test_recoge_las_fuentes_estructuradas_del_Nutrition_Agent(self):
        f = fuentes_observadas(traza(respuesta="Bebe segun la sed.",
                                     fuentes=["KB-006"]))

        self.assertEqual(f["en_traza"], ["KB-006"])
        self.assertEqual(f["en_texto"], [])
        self.assertEqual(f["union"], ["KB-006"])

    def test_recoge_los_doc_id_que_el_Coach_escribe_en_su_prosa(self):
        """Su contrato de salida no las expone como lista, asi que mirar solo
        la traza daria por no citada toda respuesta del Coach."""
        f = fuentes_observadas(traza(
            respuesta="Segun KB-002, la zona 2 esta bajo el umbral LT1."
        ))

        self.assertEqual(f["en_traza"], [])
        self.assertEqual(f["en_texto"], ["KB-002"])
        self.assertEqual(f["union"], ["KB-002"])

    def test_no_confunde_otros_codigos_con_un_doc_id(self):
        f = fuentes_observadas(traza(respuesta="Tu FC esta en KB-12 y KB-1234."))

        self.assertEqual(f["union"], [])


class TestComprobacionesAutomaticas(unittest.TestCase):

    def test_cita_fuentes_falla_cuando_el_criterio_lo_exige_y_no_hay_ninguna(self):
        """El caso MA-05: contenido correcto y proveniente de la base de
        conocimiento, pero sin mencionar su origen. Se contaba como acierto
        porque la delegacion habia sido exacta."""
        r = _evaluar_comprobaciones(
            {"cita_fuentes": True},
            traza(respuesta="La zona 2 es la base aerobica.",
                  herramientas=["consultar_base_conocimiento"]),
            fuentes_observadas(traza(respuesta="La zona 2 es la base aerobica.")),
        )

        self.assertFalse(r["cita_fuentes"]["cumple"])

    def test_cita_fuentes_falso_exige_que_no_se_cite_nada(self):
        """MA-11: ante una laguna documental, citar seria peor que no citar.
        Una comprobacion que solo verificara presencia no podria expresarlo."""
        t = traza(respuesta="La base no cubre suplementacion.")
        r = _evaluar_comprobaciones({"cita_fuentes": False}, t, fuentes_observadas(t))

        self.assertTrue(r["cita_fuentes"]["cumple"])

        t2 = traza(respuesta="Segun KB-006, toma proteina.", fuentes=["KB-006"])
        r2 = _evaluar_comprobaciones({"cita_fuentes": False}, t2, fuentes_observadas(t2))

        self.assertFalse(r2["cita_fuentes"]["cumple"])

    def test_reporta_que_fuente_esperada_falta(self):
        t = traza(respuesta="...", fuentes=["KB-001"])
        r = _evaluar_comprobaciones(
            {"fuentes_esperadas": ["KB-006"]}, t, fuentes_observadas(t)
        )

        self.assertFalse(r["fuentes_esperadas"]["cumple"])
        self.assertEqual(r["fuentes_esperadas"]["faltantes"], ["KB-006"])

    def test_reporta_que_herramienta_requerida_falta(self):
        t = traza(herramientas=["consultar_historial_sesiones"])
        r = _evaluar_comprobaciones(
            {"herramientas_requeridas": ["consultar_clima"]}, t, fuentes_observadas(t)
        )

        self.assertFalse(r["herramientas_requeridas"]["cumple"])
        self.assertEqual(r["herramientas_requeridas"]["faltantes"], ["consultar_clima"])

    def test_no_menciona_detecta_una_redireccion_indebida(self):
        """MA-01 y MA-12: un saludo o un mensaje incompleto no deben tratarse
        como tema ajeno a la plataforma."""
        t = traza(respuesta="Soy el asistente de RunCoach, me limito a temas de running.")
        r = _evaluar_comprobaciones(
            {"no_menciona": ["me limito a temas"]}, t, fuentes_observadas(t)
        )

        self.assertFalse(r["no_menciona"]["cumple"])
        self.assertEqual(r["no_menciona"]["presentes"], ["me limito a temas"])

    def test_un_caso_sin_comprobaciones_no_produce_ninguna(self):
        """No aprueba por omision: queda sin senal automatica y su veredicto
        depende enteramente del juicio manual."""
        t = traza()

        self.assertEqual(_evaluar_comprobaciones({}, t, fuentes_observadas(t)), {})


class TestVeredictoDeCalidad(unittest.TestCase):
    """Como se combinan la senal automatica y el juicio humano."""

    def caso(self, comprobaciones=None):
        return {"id": "MA-99", "comprobaciones": comprobaciones or {}}

    def test_sin_veredicto_manual_queda_pendiente_y_no_aprobado(self):
        """Una evaluacion de calidad a la que le falta juicio humano debe
        declararlo, no disimularlo aprobando por defecto."""
        t = traza()
        c = _evaluar_calidad(self.caso(), t, fuentes_observadas(t), manual={})

        self.assertEqual(c["veredicto"], "pendiente")

    def test_un_veredicto_manual_positivo_aprueba(self):
        t = traza()
        c = _evaluar_calidad(
            self.caso(), t, fuentes_observadas(t),
            manual={"MA-99": {"cumple": True, "nota": "correcta"}},
        )

        self.assertEqual(c["veredicto"], "cumple")
        self.assertEqual(c["nota_manual"], "correcta")

    def test_una_comprobacion_fallida_manda_sobre_el_juicio_humano(self):
        """La senal automatica es la que no depende de quien la mire. Un
        veredicto manual puede reprobar lo que las comprobaciones aprobaron,
        pero no al reves."""
        t = traza(respuesta="La zona 2 es la base aerobica.")
        c = _evaluar_calidad(
            self.caso({"cita_fuentes": True}), t, fuentes_observadas(t),
            manual={"MA-99": {"cumple": True, "nota": "a mi me parece bien"}},
        )

        self.assertEqual(c["veredicto"], "no_cumple")
        self.assertEqual(c["comprobaciones_fallidas"], ["cita_fuentes"])

    def test_un_veredicto_manual_negativo_reprueba_aunque_lo_automatico_pase(self):
        t = traza(respuesta="Segun KB-002, entrena mas.", fuentes=["KB-002"])
        c = _evaluar_calidad(
            self.caso({"cita_fuentes": True}), t, fuentes_observadas(t),
            manual={"MA-99": {"cumple": False, "nota": "cita bien pero no responde"}},
        )

        self.assertEqual(c["veredicto"], "no_cumple")
        self.assertEqual(c["comprobaciones_fallidas"], [])


if __name__ == "__main__":
    unittest.main()