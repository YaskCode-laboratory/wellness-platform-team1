"""Orchestrator Agent: coordinador del sistema multiagente (issues S3-02, S3-04).

Recibe la solicitud del corredor, determina que dominios de conocimiento hacen
falta, delega en los agentes competentes y devuelve el resultado junto con la
traza de lo ocurrido.

QUE NO HACE ESTE COMPONENTE

No responde preguntas del corredor por su cuenta, no consulta la base de
conocimiento, no accede a Firestore y no invoca herramientas. Cuando no delega
responde con un texto fijo, no generado.

Tampoco reescribe lo que dicen los agentes. Al consolidar dos respuestas las
une literalmente, atribuyendo cada parte a su especialista, y no parafrasea.
La razon no es de estilo: las citas a la knowledge base se validan
programaticamente contra los fragmentos que recupero cada agente
(validar_fuentes, Sprint 1), y esa validacion aplica al texto que el agente
produjo. Si el orquestador lo reescribiera, la correspondencia entre afirmacion
y fuente dejaria de estar garantizada. Parafrasear romperia la trazabilidad
que sostiene todo el sistema.

El reparto de la consulta tampoco lo hace este componente: lo hace el
clasificador, que ya esta leyendo el mensaje y decidiendo que dominios
intervienen. Partirlo aqui exigiria una segunda llamada al modelo sobre el
mismo texto.

PATRON SUPERVISOR

Un unico punto de decision, que es tambien un unico punto de traza. Cada
solicitud entra y sale por aqui, de modo que responder "que paso con esta
solicitud" no exige correlacionar registros emitidos por varios agentes. La
justificacion frente a Sequential, Hierarchical y Swarm esta en
docs/architecture/multiagent-architecture.md, seccion 3.

QUE AGREGA S3-04 SOBRE S3-02

S3-02 dejo la coordinacion multidominio explicitamente fuera de alcance: el
clasificador DETECTABA la intencion mixta y el orquestador la trataba como
caso previsto, respondiendo que solo podia cubrir una parte. Reconocer no es
atender, y la nota de aquel modulo insistia en no confundirlos.

Este issue cierra esa brecha. Lo que antes faltaba y ahora existe: repartir la
consulta en sub-consultas, delegar en mas de un agente, encadenar el contexto
de uno al siguiente y consolidar varias respuestas en una. Un caso mixto ya no
sale con delegado=False y agentes=[]; sale con los dos agentes en la traza y
sus respuestas atribuidas.

PREVENCION DE CICLOS (S3-04)

Los agentes especializados no delegan: solo el orquestador lo hace, sobre una
lista finita determinada antes de invocar al primero. Un agente que reciba algo
fuera de su alcance lo declara en su respuesta, no lo reenvia. Se refuerza
ademas con una guarda explicita: ningun agente se invoca dos veces dentro de la
misma solicitud.
"""

import logging
import time
import uuid
from datetime import datetime, timezone

from src.orchestration.communication.contratos import RespuestaAgente, SolicitudAgente
from src.orchestration.delegation.registro import RegistroDelegaciones
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

RESPUESTA_DOMINIO_SIN_AGENTE = (
    "Esa pregunta es de un tema que la plataforma cubre pero que todavía no "
    "tiene un asistente asignado. Puedo ayudarte con cualquier duda sobre tu "
    "entrenamiento o tu alimentación."
)

RESPUESTA_AGENTE_FALLO = (
    "No pude completar tu consulta en este momento por un problema técnico. "
    "¿Podrías intentarlo de nuevo en un momento?"
)

# Conector fijo para las respuestas consolidadas. Es texto del orquestador, no
# contenido generado: anuncia la estructura sin afirmar nada del dominio.
INTRO_COLABORACION = (
    "Tu consulta toca más de un área, así que te respondo por partes."
)


class OrchestratorAgent:
    """Coordinador del sistema multiagente."""

    def __init__(self, registro: RegistroDelegaciones | None = None) -> None:
        # Se inyecta para poder sustituirlo en pruebas sin tocar Firestore, y
        # para que un despliegue pueda cambiar el destino de las trazas sin
        # modificar el orquestador.
        self.registro = registro if registro is not None else RegistroDelegaciones()

    def procesar(self, user_id: str, mensaje: str) -> dict:
        """Atiende una solicitud del corredor de principio a fin.

        Devuelve siempre un diccionario con la misma forma, delegue en cero,
        uno o varios agentes, de modo que quien lo consume no tenga que
        distinguir casos. La traza indica que ocurrio.
        """
        traza_id = str(uuid.uuid4())
        inicio = time.perf_counter()

        t0 = time.perf_counter()
        clasificacion = clasificar(mensaje)
        latencia_clasificacion = round((time.perf_counter() - t0) * 1000)

        logger.info(
            "[%s] intencion=%s dominios=%s confianza=%.2f motivo=%s",
            traza_id,
            clasificacion.intencion,
            clasificacion.dominios,
            clasificacion.confianza,
            clasificacion.motivo,
        )

        plan = self._planificar(clasificacion, mensaje)
        ejecutadas, respuestas = self._ejecutar_plan(
            plan["delegaciones"], user_id, traza_id
        )

        traza = self._componer(
            traza_id=traza_id,
            clasificacion=clasificacion,
            plan=plan,
            ejecutadas=ejecutadas,
            respuestas=respuestas,
            latencia_clasificacion=latencia_clasificacion,
            latencia_total=round((time.perf_counter() - inicio) * 1000),
        )

        # Registrar es auxiliar: si falla, la solicitud sigue siendo valida.
        self.registro.registrar(traza)

        return traza

    # ── Planificacion ────────────────────────────────────────────────────────

    def _planificar(self, clasificacion: Clasificacion, mensaje: str) -> dict:
        """Traduce una clasificacion en un plan de delegacion.

        Devuelve la lista ordenada de delegaciones -- cada una con el agente y
        el mensaje que le corresponde -- o vacia cuando no procede delegar,
        junto con el texto con el que responder en ese caso.

        Es logica pura: no toca red ni modelo, asi que toda la politica de
        cuando delegar, en quien y en que orden se puede leer de un vistazo y
        probar exhaustivamente sin mockear nada. Es lo que sostiene el criterio
        de que la delegacion no dependa de reglas dispersas.

        El orden de las comprobaciones importa. La confianza se evalua primero:
        una intencion clara pero poco confiable no debe delegarse aunque tenga
        agente disponible, porque una delegacion equivocada entrega al corredor
        una respuesta del dominio incorrecto sin avisarle del error.
        """
        if not clasificacion.es_confiable:
            return self._sin_delegacion(RESPUESTA_NO_RECONOCIDA, "confianza_insuficiente")

        if clasificacion.intencion == "fuera_de_dominio":
            return self._sin_delegacion(RESPUESTA_FUERA_DE_DOMINIO, "fuera_de_dominio")

        if clasificacion.intencion == "no_reconocida":
            return self._sin_delegacion(RESPUESTA_NO_RECONOCIDA, "intencion_no_reconocida")

        if clasificacion.es_colaboracion:
            delegaciones = []
            for sub in clasificacion.subconsultas:
                agente = resolver(sub.dominio)
                if agente is not None:
                    delegaciones.append({"agente": agente, "mensaje": sub.mensaje})

            if len(delegaciones) < 2:
                # El clasificador ya filtra los dominios contra el registro, asi
                # que llegar aqui significa que algo cambio entre la
                # clasificacion y la resolucion. Pedir aclaracion es preferible
                # a atender media consulta sin decirlo.
                logger.error(
                    "Colaboracion planificada con %d agentes resolubles: %s",
                    len(delegaciones),
                    clasificacion.dominios,
                )
                return self._sin_delegacion(
                    RESPUESTA_NO_RECONOCIDA, "colaboracion_sin_agentes_suficientes"
                )

            return {"delegaciones": delegaciones, "texto": None, "motivo_no_delegacion": None}

        agente = resolver(clasificacion.intencion)
        if agente is not None:
            # Delegacion simple: el agente recibe el mensaje intacto. No hay
            # nada que repartir y reformularlo solo podria perder matices.
            return {
                "delegaciones": [{"agente": agente, "mensaje": mensaje}],
                "texto": None,
                "motivo_no_delegacion": None,
            }

        if es_dominio_sin_agente(clasificacion.intencion):
            return self._sin_delegacion(RESPUESTA_DOMINIO_SIN_AGENTE, "dominio_sin_agente")

        # Inalcanzable mientras el enum del clasificador se genere desde el
        # registro. Se contempla igual: si alguien agrega una intencion sin
        # agente ni dominio declarado, el sistema pide aclaracion, no se rompe.
        logger.error(
            "Intencion valida sin destino: %r. Revisar registro_agentes.",
            clasificacion.intencion,
        )
        return self._sin_delegacion(RESPUESTA_NO_RECONOCIDA, "intencion_sin_destino")

    @staticmethod
    def _sin_delegacion(texto: str, motivo: str) -> dict:
        return {"delegaciones": [], "texto": texto, "motivo_no_delegacion": motivo}

    # ── Ejecucion del plan ───────────────────────────────────────────────────

    def _ejecutar_plan(
        self, delegaciones: list[dict], user_id: str, traza_id: str
    ) -> tuple[list[dict], list[RespuestaAgente]]:
        """Invoca a los agentes del plan en orden, encadenando el contexto.

        Cada agente recibe su parte de la consulta y lo que respondio el
        anterior, para que complemente en vez de repetir. El orden lo fija el
        clasificador: primero el dominio cuya respuesta sirve de contexto al
        siguiente.

        POR QUE DEVUELVE TAMBIEN LAS DELEGACIONES EJECUTADAS

        Porque no tienen por que ser las planificadas. La guarda contra
        repeticion puede omitir una, y entonces el plan y las respuestas dejan
        de tener la misma longitud.

        Antes se devolvian solo las respuestas y _componer() reconstruia el
        mensaje entregado indexando el PLAN por la posicion de la RESPUESTA
        (delegaciones[i - 1]). Con una omision intermedia, ese indice se
        desplaza y la traza atribuye a un agente un mensaje que nunca recibio.
        Una traza equivocada es peor que una traza ausente: se lee como
        evidencia. Y era doblemente grave porque solo ocurria cuando actuaba
        una proteccion, que es justo cuando hace falta poder auditar.

        Devolviendo las delegaciones efectivamente ejecutadas, ambas listas
        quedan alineadas por construccion y la traza no puede desfasarse.
        """
        ejecutadas: list[dict] = []
        respuestas: list[RespuestaAgente] = []
        invocados: set[str] = set()
        contexto = ""

        for paso, delegacion in enumerate(delegaciones, start=1):
            agente = delegacion["agente"]
            nombre = agente["nombre"]

            # Guarda explicita contra ciclos. El clasificador ya elimina
            # duplicados y los agentes no pueden delegar, asi que esto no
            # deberia dispararse nunca: esta por si una de esas dos
            # protecciones se debilita en el futuro.
            if nombre in invocados:
                logger.error(
                    "[%s] Se intento invocar dos veces a '%s'. Se omite.",
                    traza_id,
                    nombre,
                )
                continue
            invocados.add(nombre)

            solicitud = SolicitudAgente(
                traza_id=traza_id,
                user_id=user_id,
                mensaje=delegacion["mensaje"],
                intencion=agente["intencion"],
                contexto=contexto,
                paso=paso,
            )

            t0 = time.perf_counter()
            respuesta = self._delegar(agente, solicitud)
            respuesta.latencia_ms = round((time.perf_counter() - t0) * 1000)

            ejecutadas.append(delegacion)
            respuestas.append(respuesta)

            logger.info(
                "[%s] paso=%d agente=%s degradado=%s fallo=%s latencia=%dms",
                traza_id,
                paso,
                nombre,
                respuesta.degradado,
                respuesta.fallo,
                respuesta.latencia_ms,
            )

            contexto = self._contexto_para_el_siguiente(agente, respuesta)

        return ejecutadas, respuestas

    @staticmethod
    def _contexto_para_el_siguiente(agente: dict, respuesta: RespuestaAgente) -> str:
        """Prepara lo que el siguiente agente recibira del anterior.

        UN FALLO NO SE ENCADENA COMO SI FUERA UNA RESPUESTA

        Cuando un agente falla, _delegar() devuelve una RespuestaAgente cuyo
        'texto' es RESPUESTA_AGENTE_FALLO: un mensaje del orquestador dirigido
        al corredor, no contenido de dominio. Encadenarlo con la formula
        habitual producia "Wellness Coach Agent respondió: No pude completar tu
        consulta...", y mensaje_con_contexto() se lo entrega al siguiente
        agente pidiendole que lo COMPLEMENTE y no lo CONTRADIGA.

        El efecto es doble y ninguno es bueno: el segundo agente trata un
        mensaje de error como aportacion de un especialista, y puede acabar
        disculpandose por algo que no le corresponde o evitando un tema que el
        primero nunca llego a cubrir. Ademas invierte el sentido de la
        degradacion: S3-01 la definio como conservar lo que si funciono, y asi
        el fallo de uno contaminaba al otro.

        Se declara explicitamente que el especialista anterior no produjo
        informacion utilizable. El siguiente agente conserva el dato de que
        hubo un paso previo -- que es lo que evita respuestas incoherentes con
        el flujo -- sin recibir un error disfrazado de contenido.

        'degradado' no basta para decidir esto: un Coach que respondio bien
        pero no pudo consultar el clima viene degradado y su texto SI es
        contexto util. El discriminante es 'fallo'.
        """
        if respuesta.fallo:
            return (
                f"{agente['titulo']} no pudo completar su parte por un problema "
                f"tecnico y no aporto informacion de su dominio. No supongas lo "
                f"que habria dicho ni respondas por el: limitate a tu "
                f"especialidad."
            )
        return f"{agente['titulo']} respondió:\n{respuesta.texto}"

    def _delegar(self, agente: dict, solicitud: SolicitudAgente) -> RespuestaAgente:
        """Invoca a un agente sin dejar que un fallo suyo tumbe la solicitud.

        Misma decision que la correccion S2-04 tomo para el despacho de
        herramientas, un nivel mas arriba: el punto por donde pasan todas las
        invocaciones a agentes es el unico lugar donde hay que protegerlas, y
        cualquier agente que se registre despues hereda la proteccion.

        En un flujo de colaboracion esto importa mas todavia: si el primer
        agente falla, el segundo se invoca igual y el corredor recibe la mitad
        que si funciono, declarada como tal, en vez de perder la consulta
        entera.
        """
        try:
            return agente["invocador"](solicitud)
        except Exception:
            logger.exception(
                "[%s] Fallo el agente '%s' al atender la solicitud.",
                solicitud.traza_id,
                agente["nombre"],
            )
            return RespuestaAgente(
                agente=agente["nombre"],
                texto=RESPUESTA_AGENTE_FALLO,
                degradado=True,
                # Unico lugar del sistema que marca 'fallo'. Distingue "no
                # produjo nada" de "produjo algo con una capacidad caida", y
                # de ello depende que este texto se encadene o no al siguiente
                # agente: ver _contexto_para_el_siguiente().
                fallo=True,
                detalle={"error": "el agente no pudo completar la solicitud"},
            )

    # ── Consolidacion ────────────────────────────────────────────────────────

    def _consolidar(self, ejecutadas: list[dict], respuestas: list[RespuestaAgente]) -> str:
        """Une las respuestas de los agentes en un solo texto, sin reescribirlas.

        Con un agente, su texto tal cual. Con varios, cada respuesta bajo una
        etiqueta que indica quien la aporto. No se parafrasea ni se resume:
        ver la nota sobre trazabilidad en el docstring del modulo.

        Recibe las delegaciones EJECUTADAS y no las planificadas. Aqui las
        etiquetas se buscan por nombre de agente, asi que un desfase no
        produciria una atribucion incorrecta, pero tomar el plan como si fuera
        lo ocurrido es la misma confusion que causo el defecto de la traza.
        Una sola fuente de verdad sobre lo que paso.
        """
        if len(respuestas) == 1:
            return respuestas[0].texto

        etiquetas = {d["agente"]["nombre"]: d["agente"]["etiqueta"] for d in ejecutadas}
        bloques = [
            f"**{etiquetas.get(r.agente, r.agente)}**\n{r.texto}" for r in respuestas
        ]
        return f"{INTRO_COLABORACION}\n\n" + "\n\n".join(bloques)

    # ── Composicion de la traza ──────────────────────────────────────────────

    def _componer(
        self,
        traza_id: str,
        clasificacion: Clasificacion,
        plan: dict,
        ejecutadas: list[dict],
        respuestas: list[RespuestaAgente],
        latencia_clasificacion: int,
        latencia_total: int,
    ) -> dict:
        """Arma la respuesta unica del orquestador, con su traza.

        La traza responde las preguntas que S3-06 necesita poder contestar
        sobre cualquier solicitud: que se entendio, a quien se delego, en que
        orden, que se le pidio a cada agente, que consulto y cuanto costo.

        Los pasos se construyen a partir de 'ejecutadas', no de
        plan["delegaciones"]: es lo que garantiza que mensajeDelegado sea el
        mensaje que ese agente recibio de verdad. Ver _ejecutar_plan().
        """
        delegado = bool(respuestas)
        nombres = [r.agente for r in respuestas]

        # Invariante del que depende toda la traza. Si se rompe, cada paso
        # queda atribuido al agente equivocado, y eso se lee como evidencia.
        assert len(ejecutadas) == len(respuestas), (
            "las delegaciones ejecutadas y las respuestas deben ir emparejadas"
        )

        pasos = [
            {
                "paso": i,
                "agente": r.agente,
                "mensajeDelegado": ejecutadas[i - 1]["mensaje"],
                "herramientasInvocadas": r.herramientas_invocadas,
                "fuentes": r.fuentes,
                "degradado": r.degradado,
                "fallo": r.fallo,
                "latenciaMs": r.latencia_ms,
                "detalle": r.detalle,
            }
            for i, r in enumerate(respuestas, start=1)
        ]

        herramientas = [h for r in respuestas for h in r.herramientas_invocadas]
        fuentes = [f for r in respuestas for f in r.fuentes]

        return {
            "trazaId": traza_id,
            "generadoEn": datetime.now(timezone.utc).isoformat(),
            "respuesta": (
                self._consolidar(ejecutadas, respuestas) if delegado else plan["texto"]
            ),
            "delegado": delegado,
            "colaboracion": len(respuestas) > 1,
            "agente": nombres[0] if nombres else None,
            "agentes": nombres,
            "intencion": clasificacion.intencion,
            "dominios": clasificacion.dominios,
            "motivoClasificacion": clasificacion.motivo,
            "confianza": clasificacion.confianza,
            "motivoNoDelegacion": plan["motivo_no_delegacion"],
            "degradado": any(r.degradado for r in respuestas),
            "herramientasInvocadas": herramientas,
            "fuentes": fuentes,
            "pasos": pasos,
            "latencias": {
                "clasificacionMs": latencia_clasificacion,
                "agentesMs": sum(r.latencia_ms for r in respuestas),
                "totalMs": latencia_total,
            },
        }