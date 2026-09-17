"""Orchestrator Agent: coordinador del sistema multiagente (issue S3-02).

Recibe la solicitud del corredor, determina que dominio de conocimiento hace
falta, delega en el agente competente y devuelve el resultado junto con la
traza de lo ocurrido.

QUE NO HACE ESTE COMPONENTE

No responde preguntas del corredor por su cuenta, no consulta la base de
conocimiento, no accede a Firestore y no invoca herramientas. Cuando no
delega -- porque la intencion es ajena al dominio, ambigua, o corresponde a un
dominio que aun no tiene agente -- responde con un texto fijo, no generado.

Esa restriccion es deliberada y es criterio de aceptacion de S3-02: la logica
de coordinacion queda separada de la de los agentes. Si el orquestador
empezara a resolver casos por su cuenta, dejaria de ser un coordinador para
convertirse en un agente mas, y la frontera entre ambas responsabilidades se
volveria difusa.

PATRON SUPERVISOR

Un unico punto de decision, que es tambien un unico punto de traza. Cada
solicitud entra y sale por aqui, de modo que responder "que paso con esta
solicitud" no exige correlacionar registros emitidos por varios agentes. La
justificacion completa frente a Sequential, Hierarchical y Swarm esta en
docs/architecture/multiagent-architecture.md, seccion 3.

ALCANCE DE S3-02

Se delega a lo sumo en un agente por solicitud. La intencion "mixta", que
requiere combinar dos dominios, se reconoce y se responde con honestidad pero
todavia no se atiende: la delegacion multiple y la consolidacion de respuestas
corresponden a S3-04.
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from src.orchestration.orchestrator.clasificador import Clasificacion, clasificar
from src.orchestration.orchestrator.registro_agentes import (
    es_dominio_sin_agente,
    resolver,
)

logger = logging.getLogger(__name__)

RESPUESTA_FUERA_DE_DOMINIO = (
    "Soy el asistente de entrenamiento de RunCoach, así que me limito a temas "
    "de running, salud deportiva y bienestar del corredor. Si tienes alguna "
    "pregunta sobre tu entrenamiento, con gusto te ayudo."
)

RESPUESTA_NO_RECONOCIDA = (
    "No terminé de entender qué necesitas. ¿Podrías contarme un poco más? "
    "Puedo ayudarte con tu entrenamiento, tu progreso o cualquier duda sobre "
    "cómo estás corriendo."
)

RESPUESTA_MIXTA_NO_SOPORTADA = (
    "Tu pregunta combina entrenamiento y nutrición, y por ahora solo puedo "
    "responder la parte de entrenamiento. Si me la haces por separado, te "
    "ayudo con esa mitad."
)

RESPUESTA_DOMINIO_SIN_AGENTE = (
    "Esa pregunta es de nutrición, un tema que la plataforma cubre pero que "
    "todavía no tiene un asistente asignado. Puedo ayudarte con cualquier duda "
    "sobre tu entrenamiento."
)

RESPUESTA_AGENTE_FALLO = (
    "No pude completar tu consulta en este momento por un problema técnico. "
    "¿Podrías intentarlo de nuevo en un momento?"
)


class OrchestratorAgent:
    """Coordinador del sistema multiagente."""

    def procesar(self, user_id: str, mensaje: str) -> dict:
        """Atiende una solicitud del corredor de principio a fin.

        Devuelve siempre un diccionario con la misma forma, delegue o no, de
        modo que quien lo consume no tenga que distinguir casos. La traza
        indica que ocurrio.
        """
        traza_id = str(uuid.uuid4())
        inicio = time.perf_counter()

        t0 = time.perf_counter()
        clasificacion = clasificar(mensaje)
        latencia_clasificacion = round((time.perf_counter() - t0) * 1000)

        logger.info(
            "[%s] intencion=%s confianza=%.2f motivo=%s",
            traza_id,
            clasificacion.intencion,
            clasificacion.confianza,
            clasificacion.motivo,
        )

        decision = self._decidir(clasificacion)
        resultado_agente = None
        latencia_agente = 0

        if decision["agente"] is not None:
            t1 = time.perf_counter()
            resultado_agente = self._delegar(
                decision["agente"], user_id, mensaje, traza_id
            )
            latencia_agente = round((time.perf_counter() - t1) * 1000)

        return self._componer(
            traza_id=traza_id,
            clasificacion=clasificacion,
            decision=decision,
            resultado_agente=resultado_agente,
            latencia_clasificacion=latencia_clasificacion,
            latencia_agente=latencia_agente,
            latencia_total=round((time.perf_counter() - inicio) * 1000),
        )

    # ── Decision ─────────────────────────────────────────────────────────────

    def _decidir(self, clasificacion: Clasificacion) -> dict:
        """Traduce una clasificacion en una decision de delegacion.

        Devuelve el agente a invocar, o el texto con el que responder cuando
        no corresponde delegar. Se separa de procesar() porque es logica pura:
        no toca la red y se puede probar sin mockear nada.

        El orden de las comprobaciones importa. La confianza se evalua
        primero: una intencion clara pero poco confiable no debe delegarse
        aunque tenga agente disponible, porque una delegacion equivocada
        entrega al corredor una respuesta del dominio incorrecto sin avisarle
        de que hubo un error.
        """
        if not clasificacion.es_confiable:
            return {
                "agente": None,
                "texto": RESPUESTA_NO_RECONOCIDA,
                "motivo_no_delegacion": "confianza_insuficiente",
            }

        if clasificacion.intencion == "fuera_de_dominio":
            return {
                "agente": None,
                "texto": RESPUESTA_FUERA_DE_DOMINIO,
                "motivo_no_delegacion": "fuera_de_dominio",
            }

        if clasificacion.intencion == "no_reconocida":
            return {
                "agente": None,
                "texto": RESPUESTA_NO_RECONOCIDA,
                "motivo_no_delegacion": "intencion_no_reconocida",
            }

        if clasificacion.intencion == "mixta":
            return {
                "agente": None,
                "texto": RESPUESTA_MIXTA_NO_SOPORTADA,
                "motivo_no_delegacion": "delegacion_multiple_no_implementada",
            }

        agente = resolver(clasificacion.intencion)
        if agente is not None:
            return {"agente": agente, "texto": None, "motivo_no_delegacion": None}

        if es_dominio_sin_agente(clasificacion.intencion):
            return {
                "agente": None,
                "texto": RESPUESTA_DOMINIO_SIN_AGENTE,
                "motivo_no_delegacion": "dominio_sin_agente",
            }

        # Inalcanzable mientras el enum del clasificador se genere desde el
        # registro. Se contempla igual: si alguien agrega una intencion al
        # registro sin agente ni dominio declarado, el sistema debe pedir
        # aclaracion, no romperse.
        logger.error(
            "Intencion valida sin destino: %r. Revisar registro_agentes.",
            clasificacion.intencion,
        )
        return {
            "agente": None,
            "texto": RESPUESTA_NO_RECONOCIDA,
            "motivo_no_delegacion": "intencion_sin_destino",
        }

    # ── Delegacion ───────────────────────────────────────────────────────────

    def _delegar(self, agente: dict, user_id: str, mensaje: str, traza_id: str) -> dict:
        """Invoca al agente sin dejar que un fallo suyo tumbe la solicitud.

        Misma decision que la correccion S2-04 tomo para el despacho de
        herramientas, un nivel mas arriba: el punto por donde pasan todas las
        invocaciones a agentes es el unico lugar donde hay que protegerlas, y
        cualquier agente que se registre despues hereda la proteccion.

        Se captura Exception de forma amplia a proposito. El objetivo no es
        anticipar como puede fallar cada agente, sino garantizar que ninguno
        pueda romper la solicitud completa. La excepcion real va al log con
        traza; el corredor recibe un mensaje generico.
        """
        try:
            return agente["invocador"](user_id, mensaje)
        except Exception:
            logger.exception(
                "[%s] Fallo el agente '%s' al atender la solicitud.",
                traza_id,
                agente["nombre"],
            )
            return {
                "texto": RESPUESTA_AGENTE_FALLO,
                "herramientas_invocadas": [],
                "degradado": True,
                "detalle_agente": {"error": "el agente no pudo completar la solicitud"},
            }

    # ── Composicion de la respuesta ──────────────────────────────────────────

    def _componer(
        self,
        traza_id: str,
        clasificacion: Clasificacion,
        decision: dict,
        resultado_agente: dict | None,
        latencia_clasificacion: int,
        latencia_agente: int,
        latencia_total: int,
    ) -> dict:
        """Arma la respuesta unica del orquestador, con su traza.

        La traza responde tres preguntas que S3-06 necesita poder contestar
        sobre cualquier solicitud: que se entendio, a quien se delego y por
        que, y cuanto costo cada paso.
        """
        delegado = resultado_agente is not None
        agente_nombre = decision["agente"]["nombre"] if decision["agente"] else None

        return {
            "trazaId": traza_id,
            "generadoEn": datetime.now(timezone.utc).isoformat(),
            "respuesta": resultado_agente["texto"] if delegado else decision["texto"],
            "delegado": delegado,
            "agente": agente_nombre,
            "intencion": clasificacion.intencion,
            "motivoClasificacion": clasificacion.motivo,
            "confianza": clasificacion.confianza,
            "motivoNoDelegacion": decision["motivo_no_delegacion"],
            "degradado": resultado_agente["degradado"] if delegado else False,
            "herramientasInvocadas": (
                resultado_agente["herramientas_invocadas"] if delegado else []
            ),
            "detalleAgente": resultado_agente["detalle_agente"] if delegado else None,
            "latencias": {
                "clasificacionMs": latencia_clasificacion,
                "agenteMs": latencia_agente,
                "totalMs": latencia_total,
            },
        }