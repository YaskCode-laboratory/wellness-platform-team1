"""Gestion de sesiones de entrenamiento y objetivos del corredor.

Migrado desde el microservicio 'sessions' de RunCoach AI, que nunca se habia
incorporado a este repositorio. Hasta ahora la PWA consultaba esos endpoints en
un despliegue externo, de modo que quien clonara el repositorio no podia
levantar la aplicacion completa -- y el criterio de aceptacion de S3-07 exige
que un tercero pueda reproducir la demostracion siguiendo la documentacion.

DOS CAMBIOS RESPECTO AL ORIGINAL

1. SIN INDICES COMPUESTOS. El servicio original combinaba 'where' con
   'order_by' al listar sesiones, y varios 'where' sobre rangos de fecha en las
   metricas. Firestore exige indices compuestos para esos casos, y crearlos es
   configuracion manual en la consola que no queda versionada en el
   repositorio: cualquiera que clonara el proyecto se encontraria con consultas
   que fallan hasta que alguien recuerde crear el indice.

   Se filtra por userId y se resuelve el orden y los rangos en memoria. Con
   decenas de documentos por corredor el costo es despreciable, y elimina una
   dependencia de configuracion externa. Es la misma decision que
   RepositorioCorredor tomo en el issue S2-01.

2. FECHAS CON ZONA HORARIA. El original usaba datetime.utcnow(), deprecado
   desde Python 3.12 por devolver un datetime ingenuo que aparenta ser UTC sin
   declararlo.
"""

import uuid
from datetime import datetime, timezone

from google.cloud.firestore import FieldFilter

from src.database.firestore_client import db

COLECCION_SESIONES = "sessions"
COLECCION_OBJETIVOS = "goals"

LIMITE_SESIONES = 50

TIPOS_OBJETIVO = ("semanal", "largo_plazo")


class OperacionInvalida(Exception):
    """Datos de entrada que no cumplen las reglas del dominio."""


class NoEncontrado(Exception):
    """El documento solicitado no existe."""


class NoAutorizado(Exception):
    """El documento existe pero pertenece a otro corredor."""


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


def _documentos_de(coleccion: str, user_id: str) -> list[dict]:
    """Documentos de una coleccion que pertenecen a un corredor.

    Filtro por un solo campo, a proposito: ver la nota sobre indices compuestos
    en el docstring del modulo.
    """
    docs = (
        db.collection(coleccion)
        .where(filter=FieldFilter("userId", "==", user_id))
        .stream()
    )
    return [d.to_dict() for d in docs]


def _obtener_propio(coleccion: str, user_id: str, doc_id: str):
    """Referencia y datos de un documento, comprobando que sea del corredor.

    La comprobacion de propiedad se hace aqui y no en cada endpoint para que no
    se pueda olvidar en uno: es la unica barrera que impide que un corredor
    lea o modifique los datos de otro conociendo su identificador.
    """
    ref = db.collection(coleccion).document(doc_id)
    doc = ref.get()

    if not doc.exists:
        raise NoEncontrado(doc_id)

    datos = doc.to_dict()
    if datos.get("userId") != user_id:
        raise NoAutorizado(doc_id)

    return ref, datos


# ── Sesiones ─────────────────────────────────────────────────────────────────

def crear_sesion(datos: dict) -> dict:
    sesion_id = str(uuid.uuid4())
    registro = {
        "id": sesion_id,
        "userId": datos["userId"],
        "fecha": datos["fecha"],
        "distanciaKm": datos["distanciaKm"],
        "tiempoSeg": datos["tiempoSeg"],
        "ritmoMin": datos["ritmoMin"],
        "fcPromedio": datos.get("fcPromedio"),
        "notas": datos.get("notas"),
        "createdAt": _ahora(),
    }
    db.collection(COLECCION_SESIONES).document(sesion_id).set(registro)
    return {"id": sesion_id, "userId": datos["userId"], "message": "Sesión registrada"}


def listar_sesiones(user_id: str) -> dict:
    """Sesiones del corredor, de la mas reciente a la mas antigua."""
    sesiones = _documentos_de(COLECCION_SESIONES, user_id)
    sesiones.sort(key=lambda s: str(s.get("fecha", "")), reverse=True)
    recortadas = sesiones[:LIMITE_SESIONES]
    return {"userId": user_id, "total": len(recortadas), "sessions": recortadas}


def obtener_sesion(user_id: str, sesion_id: str) -> dict:
    _, datos = _obtener_propio(COLECCION_SESIONES, user_id, sesion_id)
    return datos


def actualizar_sesion(user_id: str, sesion_id: str, cambios: dict) -> dict:
    ref, _ = _obtener_propio(COLECCION_SESIONES, user_id, sesion_id)
    actualizaciones = {k: v for k, v in cambios.items() if v is not None}
    actualizaciones["updatedAt"] = _ahora()
    ref.update(actualizaciones)
    return {"message": "Sesión actualizada", "id": sesion_id}


def eliminar_sesion(user_id: str, sesion_id: str) -> dict:
    ref, _ = _obtener_propio(COLECCION_SESIONES, user_id, sesion_id)
    ref.delete()
    return {"message": "Sesión eliminada", "id": sesion_id}


# ── Objetivos ────────────────────────────────────────────────────────────────

def crear_objetivo(datos: dict) -> dict:
    """Crea un objetivo semanal o de largo plazo.

    Los campos obligatorios dependen del tipo, asi que la validacion no puede
    vivir solo en el modelo de entrada: un objetivo semanal necesita kmMeta y
    uno de largo plazo necesita distancia y fecha limite.
    """
    tipo = datos.get("tipo")
    if tipo not in TIPOS_OBJETIVO:
        raise OperacionInvalida(f"tipo debe ser uno de {TIPOS_OBJETIVO}")

    objetivo_id = str(uuid.uuid4())
    registro = {
        "id": objetivo_id,
        "userId": datos["userId"],
        "tipo": tipo,
        "activo": True,
        "createdAt": _ahora(),
    }

    if tipo == "semanal":
        if not datos.get("kmMeta"):
            raise OperacionInvalida("kmMeta es requerido para un objetivo semanal")
        registro["kmMeta"] = datos["kmMeta"]
    else:
        if not datos.get("distanciaObjetivoKm") or not datos.get("fechaLimite"):
            raise OperacionInvalida(
                "distanciaObjetivoKm y fechaLimite son requeridos para un objetivo de largo plazo"
            )
        registro["distanciaObjetivoKm"] = datos["distanciaObjetivoKm"]
        registro["fechaLimite"] = datos["fechaLimite"]
        if datos.get("tiempoObjetivoMin"):
            registro["tiempoObjetivoMin"] = datos["tiempoObjetivoMin"]
        if datos.get("descripcion"):
            registro["descripcion"] = datos["descripcion"]

    db.collection(COLECCION_OBJETIVOS).document(objetivo_id).set(registro)
    return {
        "id": objetivo_id,
        "userId": datos["userId"],
        "message": "Objetivo creado",
        "goal": registro,
    }


def listar_objetivos(user_id: str) -> dict:
    """Objetivos activos del corredor.

    El filtro de 'activo' se aplica en memoria para no necesitar un indice
    compuesto sobre userId + activo.
    """
    objetivos = [
        o for o in _documentos_de(COLECCION_OBJETIVOS, user_id) if o.get("activo")
    ]
    return {"userId": user_id, "total": len(objetivos), "goals": objetivos}


def obtener_objetivo(user_id: str, objetivo_id: str) -> dict:
    _, datos = _obtener_propio(COLECCION_OBJETIVOS, user_id, objetivo_id)
    return datos


def actualizar_objetivo(user_id: str, objetivo_id: str, cambios: dict) -> dict:
    ref, _ = _obtener_propio(COLECCION_OBJETIVOS, user_id, objetivo_id)
    actualizaciones = {k: v for k, v in cambios.items() if v is not None}
    actualizaciones["updatedAt"] = _ahora()
    ref.update(actualizaciones)
    return {"message": "Objetivo actualizado", "id": objetivo_id}


def eliminar_objetivo(user_id: str, objetivo_id: str) -> dict:
    """Baja logica: el objetivo se marca inactivo, no se borra.

    Las metricas historicas y las recomendaciones pasadas se calcularon contra
    objetivos que pueden haber sido dados de baja; borrarlos dejaria esas
    referencias sin destino.
    """
    ref, _ = _obtener_propio(COLECCION_OBJETIVOS, user_id, objetivo_id)
    ref.update({"activo": False, "deletedAt": _ahora()})
    return {"message": "Objetivo eliminado", "id": objetivo_id}
