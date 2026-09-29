"""Pruebas del calculo de fechas de la plataforma.

Fijan el defecto que motivo el modulo: el sistema razonaba sobre el calendario
en UTC mientras sus corredores viven en UTC-4, de modo que cada dia a partir
de las ocho de la noche hora local el backend creia que ya era el dia
siguiente. El domingo a esa hora empezaba una semana nueva y el kilometraje
semanal se reiniciaba cuatro horas antes de tiempo.

Se prueba con instantes fijos, no con la hora real. Una prueba sobre fechas
que dependa de cuando se ejecute es exactamente lo que dejo pasar el defecto:
las pruebas anteriores comparaban contra date.today() y pasaban dieciseis
horas al dia, fallaban ocho, y en CI pasaban siempre porque el runner esta en
UTC.
"""

import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from src.utils import fechas

CARACAS = ZoneInfo("America/Caracas")


def congelar(momento_utc: datetime):
    """Sustituye el reloj por un instante fijo, respetando la zona pedida."""
    class RelojFijo(datetime):
        @classmethod
        def now(cls, tz=None):
            return momento_utc.astimezone(tz) if tz else momento_utc

    return patch.object(fechas, "datetime", RelojFijo)


class TestElCalendarioSigueAlCorredor(unittest.TestCase):

    def test_a_las_ocho_de_la_noche_todavia_es_hoy(self):
        """El caso exacto del defecto. A las 00:30 UTC del lunes, en Caracas
        son las 20:30 del domingo. El corredor que sale a correr el domingo
        por la noche y registra su sesion debe verla contada en esa semana."""
        with congelar(datetime(2026, 9, 28, 0, 30, tzinfo=timezone.utc)):
            self.assertEqual(fechas.hoy(), date(2026, 9, 27))

    def test_la_semana_no_se_reinicia_antes_de_tiempo(self):
        """La consecuencia cara del mismo instante: con UTC, el lunes de 'esta
        semana' saltaba al 28 y el kilometraje acumulado desaparecia del
        panel del corredor cuatro horas antes."""
        with congelar(datetime(2026, 9, 28, 0, 30, tzinfo=timezone.utc)):
            self.assertEqual(fechas.lunes_de_esta_semana(), date(2026, 9, 21))

    def test_la_semana_si_cambia_a_medianoche_del_corredor(self):
        """La contraparte: a las 04:30 UTC ya son las 00:30 del lunes en
        Caracas, y ahi si empieza la semana nueva."""
        with congelar(datetime(2026, 9, 28, 4, 30, tzinfo=timezone.utc)):
            self.assertEqual(fechas.hoy(), date(2026, 9, 28))
            self.assertEqual(fechas.lunes_de_esta_semana(), date(2026, 9, 28))

    def test_la_semana_empieza_en_lunes(self):
        """Lo asume el script de siembra, el calculo de carga y la interfaz.
        Si alguien lo cambiara a domingo, tres sitios dejarian de coincidir."""
        with congelar(datetime(2026, 9, 24, 15, 0, tzinfo=timezone.utc)):
            lunes = fechas.lunes_de_esta_semana()

        self.assertEqual(lunes.weekday(), 0)
        self.assertEqual(lunes, date(2026, 9, 21))

    def test_los_dias_transcurridos_se_cuentan_en_la_zona_del_corredor(self):
        with congelar(datetime(2026, 9, 28, 0, 30, tzinfo=timezone.utc)):
            self.assertEqual(fechas.dias_desde(date(2026, 9, 21)), 6)


class TestLosInstantesSiVanEnUTC(unittest.TestCase):
    """La distincion que el modulo existe para mantener.

    El calendario va en la zona del corredor; los instantes que se persisten
    -- createdAt, generadoEn -- van en UTC, porque marcan cuando ocurrio algo
    y se comparan entre si. Guardarlos en hora local seria el error simetrico.
    """

    def test_lleva_zona_explicita_y_es_utc(self):
        marca = fechas.instante_iso()

        self.assertTrue(marca.endswith("+00:00"), marca)

    def test_es_parseable_y_consciente_de_zona(self):
        """utcnow() devolvia un datetime ingenuo: al reparsearlo se perdia la
        zona y comparar dos marcas podia dar un resultado equivocado."""
        parseado = datetime.fromisoformat(fechas.instante_iso())

        self.assertIsNotNone(parseado.tzinfo)
        self.assertEqual(parseado.utcoffset().total_seconds(), 0)


class TestConfiguracion(unittest.TestCase):

    def test_la_zona_por_defecto_es_la_de_los_corredores(self):
        """No se elige UTC como zona 'neutral': UTC no es neutral para nadie,
        es la zona de otro sitio. El valor se puede cambiar con la variable de
        entorno ZONA_HORARIA si la plataforma se usa desde otra region."""
        self.assertEqual(str(fechas.ZONA_HORARIA), "America/Caracas")


if __name__ == "__main__":
    unittest.main()
