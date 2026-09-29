"""Pruebas del servicio de metricas.

Lo que importa verificar aqui es que la semana calendario coincida con la que
usa el resto del sistema, que una sola lectura sirva para todo el grafico, y
que el progreso de objetivos aplique el criterio correcto segun el tipo.
"""

import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

from src.services import metrics_service


def doc(datos, doc_id="doc-firestore"):
    d = MagicMock()
    d.id = doc_id
    d.to_dict.return_value = datos
    return d


def sesion(fecha, km=10.0, seg=3000, ritmo=5.0, user="u1"):
    return {"userId": user, "fecha": fecha, "distanciaKm": km,
            "tiempoSeg": seg, "ritmoMin": ritmo}


def lunes_de(hoy: date) -> date:
    return hoy - timedelta(days=hoy.weekday())


class TestResumen(unittest.TestCase):

    def test_calcula_km_tiempo_y_ritmo(self):
        r = metrics_service._resumen([
            sesion("2026-09-14", km=10, seg=3000),
            sesion("2026-09-16", km=5, seg=1500),
        ])

        self.assertEqual(r["sesiones"], 2)
        self.assertEqual(r["kmTotales"], 15)
        self.assertEqual(r["tiempoTotalMin"], 75.0)
        self.assertEqual(r["ritmoPromedio"], 5.0)

    def test_sin_kilometros_el_ritmo_es_cero_y_no_divide_por_cero(self):
        r = metrics_service._resumen([sesion("2026-09-14", km=0, seg=0)])

        self.assertEqual(r["ritmoPromedio"], 0)

    def test_un_conjunto_vacio_no_rompe(self):
        r = metrics_service._resumen([])

        self.assertEqual(r["sesiones"], 0)
        self.assertEqual(r["kmTotales"], 0)


class TestSemanaCalendario(unittest.TestCase):
    """La semana empieza el lunes, igual que en RepositorioCorredor.

    Desalinear esta convencion produciria que la aplicacion y el agente
    reporten cargas distintas para el mismo corredor en el mismo dia.
    """

    def test_el_rango_de_la_semana_actual_va_de_lunes_a_domingo(self):
        inicio, fin = metrics_service._rango_semana(0)

        self.assertEqual(date.fromisoformat(inicio).weekday(), 0)
        self.assertEqual(date.fromisoformat(fin).weekday(), 6)
        self.assertEqual(
            date.fromisoformat(fin) - date.fromisoformat(inicio), timedelta(days=6)
        )

    def test_el_offset_retrocede_semanas_completas(self):
        actual, _ = metrics_service._rango_semana(0)
        anterior, _ = metrics_service._rango_semana(1)

        self.assertEqual(
            date.fromisoformat(actual) - date.fromisoformat(anterior), timedelta(weeks=1)
        )

    def test_el_rango_incluye_ambos_extremos(self):
        sesiones = [
            sesion("2026-09-14"), sesion("2026-09-20"), sesion("2026-09-21"),
        ]

        dentro = metrics_service._entre(sesiones, "2026-09-14", "2026-09-20")

        self.assertEqual(len(dentro), 2)

    def test_una_fecha_con_hora_se_compara_por_su_dia(self):
        """Las fechas se guardan como cadenas ISO y algunas traen hora."""
        sesiones = [sesion("2026-09-16T08:30:00")]

        dentro = metrics_service._entre(sesiones, "2026-09-14", "2026-09-20")

        self.assertEqual(len(dentro), 1)


class TestGraficoSemanal(unittest.TestCase):

    @patch("src.services.metrics_service.db")
    def test_una_sola_lectura_para_todas_las_semanas(self, mock_db):
        """El servicio original lanzaba una consulta por semana: ocho lecturas
        de Firestore para un grafico de ocho semanas, todas sobre el mismo
        conjunto de sesiones."""
        stream = mock_db.collection.return_value.where.return_value.stream
        stream.return_value = []

        metrics_service.grafico_semanal("u1", semanas=8)

        self.assertEqual(stream.call_count, 1)

    @patch("src.services.metrics_service.db")
    def test_devuelve_una_entrada_por_semana_de_la_mas_antigua_a_la_actual(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = []

        salida = metrics_service.grafico_semanal("u1", semanas=4)

        semanas = [date.fromisoformat(d["semana"]) for d in salida["data"]]
        self.assertEqual(len(semanas), 4)
        self.assertEqual(semanas, sorted(semanas))
        self.assertEqual(semanas[-1], lunes_de(date.today()))


class TestProgresoDeObjetivos(unittest.TestCase):

    @patch("src.services.metrics_service.db")
    def test_sin_objetivos_activos_lo_declara(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = [
            doc({"id": "g1", "userId": "u1", "activo": False, "tipo": "semanal"}),
        ]

        salida = metrics_service.progreso_objetivos("u1")

        self.assertEqual(salida["goals"], [])
        self.assertIn("Sin objetivos", salida["message"])

    @patch("src.services.metrics_service.db")
    def test_un_objetivo_sin_campo_id_no_rompe_el_endpoint(self, mock_db):
        """Los objetivos creados por la API escriben un campo 'id' en el
        cuerpo, pero los que llegan por otras vias -- el script de siembra, una
        carga manual, una migracion -- pueden no tenerlo. El servicio original
        fallaba con un KeyError al encontrarse uno asi, y el endpoint devolvia
        un 500 con el mensaje {"detail": "'id'"}.

        El identificador del documento de Firestore siempre esta disponible."""
        mock_db.collection.return_value.where.return_value.stream.return_value = [
            doc(
                {"userId": "u1", "activo": True, "tipo": "semanal", "kmMeta": 25},
                doc_id="usuario-eval-agente-meta",
            ),
        ]

        salida = metrics_service.progreso_objetivos("u1")

        self.assertEqual(len(salida["goals"]), 1)
        self.assertEqual(salida["goals"][0]["id"], "usuario-eval-agente-meta")

    @patch("src.services.metrics_service.db")
    def test_el_id_del_cuerpo_tiene_prioridad_sobre_el_del_documento(self, mock_db):
        """Cuando ambos existen no deberian diferir, pero si difieren gana el
        del cuerpo: es el que conocen los clientes que crearon el objetivo."""
        mock_db.collection.return_value.where.return_value.stream.return_value = [
            doc(
                {"id": "g-api", "userId": "u1", "activo": True,
                 "tipo": "semanal", "kmMeta": 25},
                doc_id="otro-nombre",
            ),
        ]

        salida = metrics_service.progreso_objetivos("u1")

        self.assertEqual(salida["goals"][0]["id"], "g-api")

    def test_el_objetivo_semanal_acumula_los_kilometros_de_la_semana(self):
        lunes = lunes_de(date.today())
        objetivo = {"id": "g1", "tipo": "semanal", "kmMeta": 25}
        sesiones = [
            sesion(str(lunes), km=8),
            sesion(str(lunes + timedelta(days=2)), km=6),
            sesion(str(lunes - timedelta(days=3)), km=100),
        ]

        r = metrics_service._progreso_semanal(
            objetivo, sesiones, str(lunes), str(lunes + timedelta(days=6))
        )

        self.assertEqual(r["kmAcumulados"], 14)
        self.assertEqual(r["kmRestantes"], 11)
        self.assertEqual(r["porcentajeCompletado"], 56.0)
        self.assertEqual(r["sesiones"], 2)

    def test_el_porcentaje_semanal_no_pasa_de_cien(self):
        lunes = lunes_de(date.today())
        r = metrics_service._progreso_semanal(
            {"id": "g1", "tipo": "semanal", "kmMeta": 10},
            [sesion(str(lunes), km=40)],
            str(lunes), str(lunes + timedelta(days=6)),
        )

        self.assertEqual(r["porcentajeCompletado"], 100)
        self.assertEqual(r["kmRestantes"], 0)

    def test_el_objetivo_de_largo_plazo_mide_la_mejor_sesion_no_la_suma(self):
        """Un objetivo de 'correr 21 km' se cumple corriendo 21 km de una vez,
        no acumulandolos a lo largo de varias salidas."""
        objetivo = {
            "id": "g2", "tipo": "largo_plazo", "distanciaObjetivoKm": 21,
            "createdAt": "2026-01-01T00:00:00",
        }
        sesiones = [sesion("2026-02-01", km=10), sesion("2026-02-08", km=12)]

        r = metrics_service._progreso_largo_plazo(objetivo, sesiones)

        self.assertEqual(r["mejorDistanciaKm"], 12)
        self.assertEqual(r["estado"], "en_progreso")

    def test_las_sesiones_previas_al_objetivo_no_cuentan(self):
        objetivo = {
            "id": "g2", "tipo": "largo_plazo", "distanciaObjetivoKm": 21,
            "createdAt": "2026-02-01T00:00:00",
        }
        sesiones = [sesion("2026-01-15", km=25), sesion("2026-02-10", km=8)]

        r = metrics_service._progreso_largo_plazo(objetivo, sesiones)

        self.assertEqual(r["mejorDistanciaKm"], 8)
        self.assertEqual(r["sesiones"], 1)

    def test_distancia_lograda_con_tiempo_fuera_de_objetivo_se_distingue(self):
        """No es lo mismo no llegar a la distancia que llegar mas lento de lo
        propuesto: son dos situaciones distintas para el corredor."""
        objetivo = {
            "id": "g2", "tipo": "largo_plazo", "distanciaObjetivoKm": 21,
            "tiempoObjetivoMin": 120, "createdAt": "2026-01-01T00:00:00",
        }
        sesiones = [sesion("2026-02-01", km=21, seg=8000)]

        r = metrics_service._progreso_largo_plazo(objetivo, sesiones)

        self.assertEqual(r["estado"], "distancia_lograda_tiempo_no")

    def test_objetivo_logrado_en_distancia_y_tiempo(self):
        objetivo = {
            "id": "g2", "tipo": "largo_plazo", "distanciaObjetivoKm": 21,
            "tiempoObjetivoMin": 150, "createdAt": "2026-01-01T00:00:00",
        }
        sesiones = [sesion("2026-02-01", km=21, seg=8000)]

        r = metrics_service._progreso_largo_plazo(objetivo, sesiones)

        self.assertEqual(r["estado"], "logrado")

    def test_sin_sesiones_el_progreso_es_cero_y_no_rompe(self):
        objetivo = {
            "id": "g2", "tipo": "largo_plazo", "distanciaObjetivoKm": 21,
            "createdAt": "2026-01-01T00:00:00",
        }

        r = metrics_service._progreso_largo_plazo(objetivo, [])

        self.assertEqual(r["mejorDistanciaKm"], 0)
        self.assertEqual(r["porcentajeCompletado"], 0)
        self.assertEqual(r["estado"], "en_progreso")


if __name__ == "__main__":
    unittest.main()
