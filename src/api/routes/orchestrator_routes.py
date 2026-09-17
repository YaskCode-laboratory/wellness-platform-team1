"""Endpoint HTTP del sistema multiagente.

Es la primera superficie conversacional del sistema: hasta el Sprint 2 el
Wellness Coach solo se invocaba desde las pruebas y el script de evaluacion,
sin ruta propia. Se expone a traves del orquestador y no de cada agente, que
es lo coherente con el patron Supervisor: el cliente no necesita saber que
agentes existen ni cual le corresponde a su pregunta.

El endpoint de /agent del Sprint 1 permanece intacto, incluido /compare.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.orchestration.orchestrator.agent import OrchestratorAgent

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

orquestador = OrchestratorAgent()


class MensajeEntrada(BaseModel):
    """Cuerpo de la solicitud conversacional."""

    mensaje: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Mensaje del corredor en lenguaje natural",
    )


@router.post("/{userId}/chat")
async def chat(userId: str, entrada: MensajeEntrada):
    """Atiende una solicitud conversacional a traves del sistema multiagente.

    Devuelve la respuesta junto con la traza: que intencion se detecto, a que
    agente se delego y por que, y cuanto costo cada paso. La traza viaja en la
    respuesta a proposito -- es lo que permite que la demo de S3-07 y la
    evaluacion de S3-06 reconstruyan el recorrido de una solicitud sin tener
    que leer los logs del servidor.

    El orquestador no propaga excepciones de los agentes (ver _delegar), asi
    que un 500 aqui indica un fallo del propio orquestador, no de un agente.
    """
    try:
        return orquestador.procesar(userId, entrada.mensaje)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))