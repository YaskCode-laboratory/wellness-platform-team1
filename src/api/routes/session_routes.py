"""Endpoints de sesiones de entrenamiento y objetivos del corredor.

Migrados desde el microservicio 'sessions' de RunCoach AI. La logica vive en
src/services/sessions_service.py; aqui solo se validan las entradas y se
traducen los errores de dominio a codigos HTTP.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.seguridad import exigir_mismo_uid, exigir_propiedad
from src.services import sessions_service
from src.services.sessions_service import NoAutorizado, NoEncontrado, OperacionInvalida

router = APIRouter(tags=["sessions"], dependencies=[Depends(exigir_propiedad)])


class SessionRequest(BaseModel):
    userId: str
    fecha: str
    distanciaKm: float = Field(..., gt=0)
    tiempoSeg: int = Field(..., gt=0)
    ritmoMin: float = Field(..., gt=0)
    fcPromedio: Optional[int] = None
    notas: Optional[str] = None


class SessionUpdate(BaseModel):
    distanciaKm: Optional[float] = Field(None, gt=0)
    tiempoSeg: Optional[int] = Field(None, gt=0)
    ritmoMin: Optional[float] = Field(None, gt=0)
    fcPromedio: Optional[int] = None
    notas: Optional[str] = None


class GoalRequest(BaseModel):
    userId: str
    tipo: str
    kmMeta: Optional[float] = Field(None, gt=0)
    distanciaObjetivoKm: Optional[float] = Field(None, gt=0)
    tiempoObjetivoMin: Optional[int] = Field(None, gt=0)
    fechaLimite: Optional[str] = None
    descripcion: Optional[str] = None


class GoalUpdate(BaseModel):
    fechaLimite: Optional[str] = None
    descripcion: Optional[str] = None


def _ejecutar(operacion):
    """Traduce los errores de dominio del servicio a codigos HTTP.

    Se centraliza para que los nueve endpoints no repitan el mismo bloque de
    except, y para que agregar un tipo de error nuevo no exija recordar
    actualizarlos uno por uno.
    """
    try:
        return operacion()
    except OperacionInvalida as e:
        raise HTTPException(status_code=400, detail=str(e))
    except NoEncontrado:
        raise HTTPException(status_code=404, detail="No encontrado")
    except NoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Sesiones ─────────────────────────────────────────────────────────────────

@router.post("/sessions")
def create_session(data: SessionRequest, uid: str = Depends(exigir_propiedad)):
    # El userId viaja en el cuerpo y no en la ruta, asi que la dependencia del
    # router solo pudo autenticar. La comprobacion de propiedad se completa
    # aqui: sin ella, un corredor autenticado podria registrar sesiones en la
    # cuenta de otro cambiando un campo del JSON.
    exigir_mismo_uid(uid, data.userId)
    return _ejecutar(lambda: sessions_service.crear_sesion(data.model_dump()))


@router.get("/sessions/{userId}")
def get_sessions(userId: str):
    return _ejecutar(lambda: sessions_service.listar_sesiones(userId))


@router.get("/sessions/{userId}/{session_id}")
def get_session(userId: str, session_id: str):
    return _ejecutar(lambda: sessions_service.obtener_sesion(userId, session_id))


@router.put("/sessions/{userId}/{session_id}")
def update_session(userId: str, session_id: str, data: SessionUpdate):
    return _ejecutar(
        lambda: sessions_service.actualizar_sesion(userId, session_id, data.model_dump())
    )


@router.delete("/sessions/{userId}/{session_id}")
def delete_session(userId: str, session_id: str):
    return _ejecutar(lambda: sessions_service.eliminar_sesion(userId, session_id))


# ── Objetivos ────────────────────────────────────────────────────────────────

@router.post("/goals")
def create_goal(data: GoalRequest, uid: str = Depends(exigir_propiedad)):
    # Mismo caso que create_session: el userId viene en el cuerpo.
    exigir_mismo_uid(uid, data.userId)
    return _ejecutar(lambda: sessions_service.crear_objetivo(data.model_dump()))


@router.get("/goals/{userId}")
def get_goals(userId: str):
    return _ejecutar(lambda: sessions_service.listar_objetivos(userId))


@router.get("/goals/{userId}/{goal_id}")
def get_goal(userId: str, goal_id: str):
    return _ejecutar(lambda: sessions_service.obtener_objetivo(userId, goal_id))


@router.put("/goals/{userId}/{goal_id}")
def update_goal(userId: str, goal_id: str, data: GoalUpdate):
    return _ejecutar(
        lambda: sessions_service.actualizar_objetivo(userId, goal_id, data.model_dump())
    )


@router.delete("/goals/{userId}/{goal_id}")
def delete_goal(userId: str, goal_id: str):
    return _ejecutar(lambda: sessions_service.eliminar_objetivo(userId, goal_id))
