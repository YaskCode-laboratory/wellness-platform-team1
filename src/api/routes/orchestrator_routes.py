"""Endpoint HTTP del sistema multiagente.

Es la primera superficie conversacional del sistema: hasta el Sprint 2 el
Wellness Coach solo se invocaba desde las pruebas y el script de evaluacion,
sin ruta propia. Se expone a traves del orquestador y no de cada agente, que
es lo coherente con el patron Supervisor: el cliente no necesita saber que
agentes existen ni cual le corresponde a su pregunta.

El endpoint de /agent del Sprint 1 permanece intacto, incluido /compare.
"""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.agents.wellness_coach.memory import MAX_TURNOS_PERSISTIDOS, MemoriaConversacional
from src.orchestration.orchestrator.agent import OrchestratorAgent

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])

orquestador = OrchestratorAgent()
memoria = MemoriaConversacional()


class MensajeEntrada(BaseModel):
    """Cuerpo de la solicitud conversacional."""

    mensaje: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Mensaje del corredor en lenguaje natural",
    )


@router.post("/{userId}/chat")
def chat(userId: str, entrada: MensajeEntrada):
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


@router.get("/{userId}/history")
def history(
    userId: str,
    n: int = Query(MAX_TURNOS_PERSISTIDOS, ge=1, le=MAX_TURNOS_PERSISTIDOS),
):
    """Turnos persistidos de la conversacion del corredor.

    La memoria conversacional vive en Firestore desde el issue S2-03 y
    sobrevive a recargas y a cierres de sesion, pero hasta ahora no tenia
    forma de consultarse: el agente la usaba como contexto y nadie mas la
    veia. El resultado era desconcertante -- el corredor volvia a la pantalla,
    encontraba el chat vacio, y aun asi el agente recordaba lo hablado.

    Por defecto devuelve la ventana completa persistida, no la de contexto: al
    modelo se le inyectan los ultimos turnos para no inflar el prompt, pero a
    quien reabre la conversacion le interesa ver todo lo que se guardo.
    """
    try:
        turnos = memoria.obtener_historial(userId, n=n)
        return {
            "userId": userId,
            "total": len(turnos),
            "turnos": [asdict(t) for t in turnos],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{userId}/history")
def clear_history(userId: str):
    """Reinicia la conversacion del corredor.

    Necesario para la demostracion: sin esto, ensayar el recorrido dos veces
    deja al agente arrastrando el contexto del ensayo anterior, que es
    exactamente la contaminacion que el hallazgo A del Sprint 2 documento en
    las mediciones.
    """
    try:
        memoria.limpiar_historial(userId)
        return {"userId": userId, "message": "Conversación reiniciada"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))