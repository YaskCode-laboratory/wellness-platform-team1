"""Prueba que el seed de evaluacion produzca el mismo estado cualquier dia.

La quinta medicion alcanzo 100% de acierto de herramientas corriendo un
viernes. Si la profesora clona el repo y corre la evaluacion un lunes, con
el seed original obtendria 0 km en la semana actual y AG-08 fallaria sin
que nada estuviera roto: su premisa es "siento que he corrido demasiado
esta semana".

Esta prueba simula los siete dias de la semana, igual que se hizo en el
Sprint 1 para demostrar el defecto de test_calcular_carga_semanal, y
verifica que las fechas sembradas caigan siempre en la semana calendario
que les corresponde.
"""

import unittest
from datetime import date, timedelta

from scripts.evaluation.seed_agent_test_user import (
    KM_SEMANA_ACTUAL,
    KM_SEMANA_ANTERIOR,
    calcular_fechas_sesiones,
)

# Lunes 7 de septiembre de 2026. Se elige un lunes como punto de partida
# para recorrer los siete dias en orden natural.
LUNES_DE_REFERENCIA = date(2026, 9, 7)

DIAS = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")


class TestFechasDelSeedSonEstables(unittest.TestCase):

    def _rangos(self, hoy: date):
        """Los mismos rangos que usa RepositorioCorredor.calcular_carga_semanal:
        semana actual = [lunes, hoy], semana anterior = [lunes-7, domingo]."""
        lunes = hoy - timedelta(days=hoy.weekday())
        return (lunes, hoy), (lunes - timedelta(weeks=1), lunes - timedelta(days=1))

    def test_las_dos_sesiones_recientes_caen_siempre_en_la_semana_actual(self):
        for offset, nombre in enumerate(DIAS):
            with self.subTest(dia=nombre):
                hoy = LUNES_DE_REFERENCIA + timedelta(days=offset)
                fecha_a, fecha_b, _ = calcular_fechas_sesiones(hoy)
                (inicio, fin), _ = self._rangos(hoy)

                self.assertTrue(
                    inicio <= fecha_a <= fin,
                    f"{nombre}: {fecha_a} fuera del rango [{inicio}, {fin}]",
                )
                self.assertTrue(
                    inicio <= fecha_b <= fin,
                    f"{nombre}: {fecha_b} fuera del rango [{inicio}, {fin}]",
                )

    def test_la_sesion_antigua_cae_siempre_en_la_semana_anterior(self):
        for offset, nombre in enumerate(DIAS):
            with self.subTest(dia=nombre):
                hoy = LUNES_DE_REFERENCIA + timedelta(days=offset)
                _, _, fecha_anterior = calcular_fechas_sesiones(hoy)
                _, (inicio, fin) = self._rangos(hoy)

                self.assertTrue(
                    inicio <= fecha_anterior <= fin,
                    f"{nombre}: {fecha_anterior} fuera del rango [{inicio}, {fin}]",
                )

    def test_ninguna_sesion_se_siembra_en_el_futuro(self):
        """Una sesion con fecha futura quedaria fuera de [lunes, hoy] y
        ademas seria un dato incoherente en el historial del corredor."""
        for offset, nombre in enumerate(DIAS):
            with self.subTest(dia=nombre):
                hoy = LUNES_DE_REFERENCIA + timedelta(days=offset)
                for fecha in calcular_fechas_sesiones(hoy):
                    self.assertLessEqual(fecha, hoy, f"{nombre}: {fecha} esta en el futuro")

    def test_la_carga_semanal_resultante_es_la_misma_todos_los_dias(self):
        """La propiedad que de verdad importa: la premisa de AG-08 (un salto
        de 5 a 14 km) debe sostenerse corra el dia que corra."""
        distancias = {"a": 8, "b": 6, "anterior": 5}

        for offset, nombre in enumerate(DIAS):
            with self.subTest(dia=nombre):
                hoy = LUNES_DE_REFERENCIA + timedelta(days=offset)
                fecha_a, fecha_b, fecha_anterior = calcular_fechas_sesiones(hoy)
                (ini_act, fin_act), (ini_ant, fin_ant) = self._rangos(hoy)

                actual = sum(
                    km for fecha, km in ((fecha_a, distancias["a"]), (fecha_b, distancias["b"]))
                    if ini_act <= fecha <= fin_act
                )
                anterior = (
                    distancias["anterior"] if ini_ant <= fecha_anterior <= fin_ant else 0
                )

                self.assertEqual(actual, KM_SEMANA_ACTUAL, f"{nombre}: semana actual")
                self.assertEqual(anterior, KM_SEMANA_ANTERIOR, f"{nombre}: semana anterior")


if __name__ == "__main__":
    unittest.main()