"""Endpoints de cuenta y perfil del corredor.

QUE SE PROTEGE Y QUE NO

/register queda ABIERTO por necesidad: quien se registra todavia no tiene
cuenta, asi que no puede presentar un token. Es el unico endpoint de la API en
esa situacion, y por eso la dependencia se declara ruta por ruta aqui en vez
de a nivel de router como en los demas modulos.

/user/{uid}, en cambio, expone y modifica el perfil -- nombre, peso, edad,
nivel, ciudad -- y exige que el token pertenezca a ese mismo uid.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from firebase_admin import auth as firebase_auth
from pydantic import BaseModel

from src.api.seguridad import exigir_propiedad
from src.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    nombre: str
    peso: float
    edad: int
    nivel: str


class UpdateProfileRequest(BaseModel):
    nombre: Optional[str] = None
    peso: Optional[float] = None
    edad: Optional[int] = None
    nivel: Optional[str] = None
    # La ciudad habilita consultar_clima, una de las cuatro herramientas del
    # Wellness Coach. Sin ella el agente declara que no puede consultar el
    # clima (hallazgo D del Sprint 2) y esa capacidad queda sin demostrar.
    # Hasta el Sprint 3 el campo solo se podia poblar sembrando datos o
    # editando Firestore a mano: no habia forma de ponerlo desde la interfaz.
    ciudad: Optional[str] = None


@router.post("/register")
def register(data: RegisterRequest):
    try:
        return auth_service.register_user(**data.model_dump())
    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/user/{uid}", dependencies=[Depends(exigir_propiedad)])
def get_user(uid: str):
    try:
        return auth_service.get_user(uid)
    except firebase_auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/user/{uid}", dependencies=[Depends(exigir_propiedad)])
def update_profile(uid: str, data: UpdateProfileRequest):
    try:
        updates = {k: v for k, v in data.model_dump().items() if v is not None}
        return auth_service.update_user(uid, updates)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except firebase_auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
