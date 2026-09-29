"""Metricas de entrenamiento del corredor.

Migrado desde el microservicio 'metrics' de RunCoach AI por la misma razon que
sessions_service: la PWA lo consultaba en un despliegue externo, de modo que
quien clonara el repositorio no podia levantar la aplicacion completa.

SIN INDICES COMPUESTOS

El servicio original filtraba por userId y por rango de fechas en la misma
consulta, lo que obliga a Firestore a exigir un indice compuesto. Aqui se
recuperan las sesiones del corredor una sola vez y los rangos se resuelven en
memoria. Ademas de eliminar la dependencia de configuracion manual, evita algo
que el original hacia sin necesidad: weekly-chart lanzaba una consulta por cada
semana del grafico -- ocho consultas para ocho semanas -- cuando todas operan
sobre el mismo conjunto de sesiones.

LA SEMANA EMPIEZA EL LUNES

Todos los calculos semanales usan la semana calendario [lunes, domingo], igual
que RepositorioCorredor.calcular_carga_semanal. Es la misma convencion que el
resto del sistema, y desalinearla produciria que la aplicacion y el agente
reporten cargas distintas para el mismo corredor.
"""

from datetime import date, datetime, timedelta, timezone

from google.cloud.firestore import FieldFilter

from src.database.firestore_client import db

COLECCION_SESIONES = "sessions"
COLECCION_OBJETIVOS = "goals"


def _hoy() -> date:
    return datetime.now(timezone.utc).date()


def _lunes_de_esta_semana() -> date:
    hoy = _hoy()
    return hoy - timedelta(days=hoy.weekday())


def _rango_semana(offset: int = 0) -> tuple[str, str]:
    """Lunes y domingo de la semana indicada. offset 0 es la semana actual."""
    inicio = _lunes_de_esta_semana() - timedelta(weeks=offset)
    return str(inicio), str(inicio + timedelta(days=6))


def _sesiones_del_corredor(user_id: str) -> list[dict]:
    docs = (
        db.collection(COLECCION_SESIONES)
        .where(filter=FieldFilter("userId", "==", user_id))
        .stream()
    )
    return [d.to_dict() for d in docs]


def _entre(sesiones: list[dict], inicio: str, fin: str) -> list[dict]:
    """Sesiones cuya fecha cae en el rango, ambos extremos incluidos.

    Se compara sobre los diez primeros caracteres porque las fechas se guardan
    como cadenas ISO y algunas pueden traer hora: 'YYYY-MM-DD' ordena
    lexicograficamente igual que cronologicamente.
    """
    return [s for s in sesiones if inicio <= str(s.get("fecha", ""))[:10] <= fin]


def _resumen(sesiones: list[dict]) -> dict:
    """Kilometros, tiempo y ritmo promedio de un conjunto de sesiones."""
    km = sum(s.get("distanciaKm", 0) or 0 for s in sesiones)
    segundos = sum(s.get("tiempoSeg", 0) or 0 for s in sesiones)
    ritmo = round(segundos / 60 / km, 2) if km > 0 else 0
    return {
        "sesiones": len(sesiones),
        "kmTotales": round(km, 2),
        "ritmoPromedio": ritmo,
        "tiempoTotalMin": round(segundos / 60, 1),
    }


# ── Endpoints de metricas ────────────────────────────────────────────────────

def metricas_semanales(user_id: str, offset: int = 0) -> dict:
    inicio, fin = _rango_semana(offset)
    sesiones = _entre(_sesiones_del_corredor(user_id), inicio, fin)

    return {
        "userId": user_id,
        "semana": f"{inicio} / {fin}",
        **_resumen(sesiones),
    }


def resumen_periodo(user_id: str, semanas: int = 4) -> dict:
    desde = str(_hoy() - timedelta(weeks=semanas))
    sesiones = [
        s for s in _sesiones_del_corredor(user_id)
        if str(s.get("fecha", ""))[:10] >= desde
    ]

    if not sesiones:
        return {
            "userId": user_id,
            "semanas": semanas,
            "totalKm": 0,
            "totalSesiones": 0,
            "mejorRitmo": 0,
            "promedioKmSemanal": 0,
        }

    total_km = sum(s.get("distanciaKm", 0) or 0 for s in sesiones)
    ritmos = [s["ritmoMin"] for s in sesiones if s.get("ritmoMin")]

    return {
        "userId": user_id,
        "semanas": semanas,
        "totalKm": round(total_km, 2),
        "totalSesiones": len(sesiones),
        "mejorRitmo": round(min(ritmos), 2) if ritmos else 0,
        "promedioKmSemanal": round(total_km / semanas, 2) if semanas else 0,
    }


def grafico_semanal(user_id: str, semanas: int = 8) -> dict:
    """Serie de las ultimas N semanas, de la mas antigua a la actual.

    Una sola lectura de Firestore para todas las semanas. El original lanzaba
    una consulta por semana.
    """
    sesiones = _sesiones_del_corredor(user_id)

    data = []
    for offset in range(semanas - 1, -1, -1):
        inicio, fin = _rango_semana(offset)
        resumen = _resumen(_entre(sesiones, inicio, fin))
        data.append({
            "semana": inicio,
            "kmTotales": resumen["kmTotales"],
            "sesiones": resumen["sesiones"],
            "ritmoPromedio": resumen["ritmoPromedio"],
        })

    return {"userId": user_id, "semanas": semanas, "data": data}


def progreso_objetivos(user_id: str) -> dict:
    """Avance del corredor sobre cada objetivo activo.

    El identificador se toma del documento de Firestore y solo se usa el campo
    'id' del cuerpo cuando existe. Los objetivos creados por la API escriben
    ese campo, pero los que llegan por otras vias -- el script de siembra de
    evaluacion, una carga manual, una migracion -- pueden no tenerlo, y el
    servicio original fallaba con un KeyError al encontrarse uno asi. El
    identificador del documento siempre esta disponible, de modo que leerlo de
    ahi elimina la dependencia de que el cuerpo este completo.
    """
    docs = (
        db.collection(COLECCION_OBJETIVOS)
        .where(filter=FieldFilter("userId", "==", user_id))
        .stream()
    )

    objetivos = []
    for d in docs:
        datos = d.to_dict() or {}
        if not datos.get("activo"):
            continue
        datos.setdefault("id", d.id)
        objetivos.append(datos)

    if not objetivos:
        return {"userId": user_id, "message": "Sin objetivos definidos", "goals": []}

    sesiones = _sesiones_del_corredor(user_id)
    lunes = str(_lunes_de_esta_semana())
    domingo = str(_lunes_de_esta_semana() + timedelta(days=6))

    resultados = []
    for objetivo in objetivos:
        if objetivo.get("tipo") == "semanal":
            resultados.append(_progreso_semanal(objetivo, sesiones, lunes, domingo))
        elif objetivo.get("tipo") == "largo_plazo":
            resultados.append(_progreso_largo_plazo(objetivo, sesiones))

    return {"userId": user_id, "goals": resultados}


def _progreso_semanal(objetivo: dict, sesiones: list[dict], lunes: str, domingo: str) -> dict:
    de_la_semana = _entre(sesiones, lunes, domingo)
    acumulados = sum(s.get("distanciaKm", 0) or 0 for s in de_la_semana)
    meta = objetivo.get("kmMeta", 0) or 0
    porcentaje = round(acumulados / meta * 100, 1) if meta > 0 else 0

    return {
        "id": objetivo.get("id"),
        "tipo": "semanal",
        "kmMeta": meta,
        "kmAcumulados": round(acumulados, 2),
        "kmRestantes": round(max(meta - acumulados, 0), 2),
        "porcentajeCompletado": min(porcentaje, 100),
        "sesiones": len(de_la_semana),
        "semana": f"{lunes} / {domingo}",
    }


def _progreso_largo_plazo(objetivo: dict, sesiones: list[dict]) -> dict:
    """Progreso hacia una distancia objetivo, medido por la mejor sesion.

    El criterio es la sesion de mayor distancia desde que se creo el objetivo,
    no la suma: un objetivo de 'correr 21 km' se cumple corriendo 21 km de una
    vez, no acumulandolos a lo largo de varias salidas.
    """
    desde = str(objetivo.get("createdAt", ""))[:10]
    posteriores = [s for s in sesiones if str(s.get("fecha", ""))[:10] >= desde]

    mejor = max(posteriores, key=lambda s: s.get("distanciaKm", 0) or 0, default=None)
    mejor_distancia = (mejor.get("distanciaKm", 0) or 0) if mejor else 0
    mejor_tiempo = (mejor.get("tiempoSeg", 0) or 0) if mejor else 0

    objetivo_km = objetivo.get("distanciaObjetivoKm", 0) or 0
    objetivo_seg = (objetivo.get("tiempoObjetivoMin") or 0) * 60

    distancia_lograda = mejor_distancia >= objetivo_km
    tiempo_logrado = mejor_tiempo <= objetivo_seg if objetivo_seg > 0 else True

    if distancia_lograda and tiempo_logrado:
        estado = "logrado"
    elif distancia_lograda:
        estado = "distancia_lograda_tiempo_no"
    else:
        estado = "en_progreso"

    porcentaje = round(mejor_distancia / objetivo_km * 100, 1) if objetivo_km > 0 else 0

    return {
        "id": objetivo.get("id"),
        "tipo": "largo_plazo",
        "distanciaObjetivoKm": objetivo_km,
        "tiempoObjetivoMin": objetivo.get("tiempoObjetivoMin"),
        "fechaLimite": objetivo.get("fechaLimite"),
        "descripcion": objetivo.get("descripcion"),
        "mejorDistanciaKm": round(mejor_distancia, 2),
        "mejorTiempoSeg": mejor_tiempo,
        "kmAcumulados": round(mejor_distancia, 2),
        "kmRestantes": round(max(objetivo_km - mejor_distancia, 0), 2),
        "porcentajeCompletado": min(porcentaje, 100),
        "estado": estado,
        "sesiones": len(posteriores),
    }
