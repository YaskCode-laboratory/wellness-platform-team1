"""Endpoint HTTP del sistema multiagente.

Es la primera superficie conversacional del sistema: hasta el Sprint 2 el
Wellness Coach solo se invocaba desde las pruebas y el script de evaluacion,
sin ruta propia. Se expone a traves del orquestador y no de cada agente, que
es lo coherente con el patron Supervisor: el cliente no necesita saber que
agentes existen ni cual le corresponde a su pregunta.

El endpoint de /agent del Sprint 1 permanece intacto, incluido /compare.

QUE SE LE DICE AL CLIENTE CUANDO ALGO FALLA

Un mensaje fijo, y el detalle tecnico solo al log. La version anterior
devolvia str(e) en el campo 'detail', que es una fuga: el texto de una
excepcion de Python arrastra rutas del sistema de archivos, nombres de
colecciones de Firestore, identificadores de proyecto de GCP y fragmentos de
consulta, y ese cuerpo de respuesta viaja hasta el navegador del corredor.

Quien depura necesita el detalle y tiene el log; quien usa la aplicacion
necesita saber que no se pudo y que puede reintentar. Son dos audiencias
distintas y se les responde distinto.

Los tres endpoints comparten ese tratamiento a traves de _ejecutar(). Repetir
el try/except en cada uno invita a que el proximo que se agregue lo copie mal,
que es exactamente como aparecio la fuga original.

NINGUN HANDLER ES 'async def'

Todos hacen trabajo bloqueante -- Firestore, Vertex AI -- y FastAPI ejecuta los
handlers asincronos directamente en el bucle de eventos, de modo que cada
peticion lo bloquea entero mientras espera. Ver la nota de src/app/main.py.
"""

import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.api.seguridad import exigir_propiedad
from src.agents.wellness_coach.memory import MAX_TURNOS_PERSISTIDOS, MemoriaConversacional
from src.orchestration.orchestrator.agent import OrchestratorAgent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/orchestrator",
    tags=["orchestrator"],
    dependencies=[Depends(exigir_propiedad)],
)

orquestador = OrchestratorAgent()
memoria = MemoriaConversacional()

ERROR_INTERNO = (
    "No pudimos procesar tu mensaje en este momento. Intenta de nuevo en unos "
    "instantes."
)


def _ejecutar(operacion, contexto: str):
    """Ejecuta una operacion registrando el detalle y sin exponerlo.

    'contexto' identifica que se estaba haciendo y para quien, y va solo al
    log: es lo que permite encontrar la peticion concreta sin que el cliente
    reciba nada de eso.
    """
    try:
        return operacion()
    except Exception:
        logger.exception("Fallo %s", contexto)
        raise HTTPException(status_code=500, detail=ERROR_INTERNO)


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
    Por eso se registra con logger.exception y no como una advertencia: si esto
    ocurre, hay algo que arreglar en el coordinador.
    """
    return _ejecutar(
        lambda: orquestador.procesar(userId, entrada.mensaje),
        f"el orquestador atendiendo a userId={userId}",
    )


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
    def consultar():
        turnos = memoria.obtener_historial(userId, n=n)
        return {
            "userId": userId,
            "total": len(turnos),
            "turnos": [asdict(t) for t in turnos],
        }

    return _ejecutar(consultar, f"la consulta de historial de userId={userId}")


@router.delete("/{userId}/history")
def clear_history(userId: str):
    """Reinicia la conversacion del corredor.

    Necesario para la demostracion: sin esto, ensayar el recorrido dos veces
    deja al agente arrastrando el contexto del ensayo anterior, que es
    exactamente la contaminacion que el hallazgo A del Sprint 2 documento en
    las mediciones.
    """
    def limpiar():
        memoria.limpiar_historial(userId)
        return {"userId": userId, "message": "Conversación reiniciada"}

    return _ejecutar(limpiar, f"el reinicio de historial de userId={userId}")
