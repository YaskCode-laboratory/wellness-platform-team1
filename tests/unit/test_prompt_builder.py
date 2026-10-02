"""Pruebas de las utilidades de fechas de prompt_builder.

Fijan un defecto de sombreado de nombres: prompt_builder importaba
dias_desde desde src.utils.fechas y luego definia su propia dias_desde con el
mismo nombre. La local tapaba a la importada y, al delegar en ella, se llamaba
a si misma hasta agotar la recursion. Las rutas /agent/analyze y
/agent/compare respondian 500 en los dos modos, legacy y RAG.

La suite no lo detecto porque solo probaba la dias_desde de fechas, que es
correcta. Estas pruebas ejercitan la de prompt_builder, que es la que usan
los agentes al enriquecer las sesiones.

Se fija la fecha de hoy, por la misma razon que en test_fechas: una prueba
sobre fechas que dependa de cuando se ejecute no prueba nada.
"""

import unittest
from datetime import date
from unittest.mock import patch

from src.utils import fechas
from src.utils.prompt_builder import dias_desde, enriquecer_sesiones


class DiasDesdeTest(unittest.TestCase):
    def test_calcula_dias_desde_fecha_iso(self):
        with patch.object(fechas, "hoy", return_value=date(2026, 10, 1)):
            self.assertEqual(dias_desde("2026-09-23T07:00:00Z"), 8)

    def test_fecha_invalida_o_vacia_devuelve_none(self):
        self.assertIsNone(dias_desde("no-es-fecha"))
        self.assertIsNone(dias_desde(None))

    def test_enriquecer_sesiones_agrega_dias_atras(self):
        with patch.object(fechas, "hoy", return_value=date(2026, 10, 1)):
            r = enriquecer_sesiones([{"fecha": "2026-09-30"}, {"fecha": None}])
        self.assertEqual([s["diasAtras"] for s in r], [1, "desconocido"])


if __name__ == "__main__":
    unittest.main()
