"""Orquestador del Wellness Coach Agent 2.0: ciclo ReAct sobre Vertex AI.

No se persiste el objeto ChatSession del SDK entre peticiones HTTP -- no es
serializable a Firestore de forma directa, y cada peticion es stateless. En
su lugar, el historial de turnos anteriores (MemoriaConversacional, #12) se
inyecta como texto dentro del prompt de sistema de cada conversacion nueva.

El ciclo ReAct (Thought -> Action -> Observation) se implementa como un
bucle manual sobre chat.send_message(): mientras el modelo devuelva
llamadas a funcion en su respuesta, se despachan (#13) y se le devuelve el
resultado; se detiene cuando el modelo produce texto sin mas llamadas, o al
alcanzar MAX_ITERACIONES_HERRAMIENTAS (evita ciclos infinitos, exigido por
el criterio de aceptacion de #14).

CORRECCION #15 (hallazgo C, verificacion real con Vertex AI): el modelo a
veces narra la intencion de usar una herramienta ("voy a consultar la base
de conocimiento") o directamente atribuye contenido a ella ("segun la base
de conocimiento...") sin emitir una llamada a funcion real. El ciclo
original cerraba el turno ahi mismo, entregando al usuario una promesa
incumplida o una atribucion falsa -- el mismo problema de cita alucinada
del Sprint 1, en otra superficie.

Se investigo tool_config con FunctionCallingConfig.Mode.ANY como
alternativa estructural (forzar la llamada en vez de detectarla por texto),
pero se descarto: ChatSession.send_message() no acepta tool_config por
mensaje (confirmado contra la documentacion oficial del SDK), y aplicar
ANY a nivel de todo el modelo forzaria una llamada en CADA turno, incluidos
los que legitimamente no requieren ninguna herramienta (por ejemplo un
saludo), rompiendo ese comportamiento correcto. Se opta por una heuristica
textual con un reintento acotado -- ver limitaciones documentadas en
_declara_uso_de_herramienta_sin_invocar().

CORRECCION S2-04 (revision del PR #25): el hallazgo D protegio
consultar_clima contra fallos de Open-Meteo, pero fue una correccion
reactiva sobre el sintoma medido, no sobre el principio. Las otras tres
herramientas dependen de Firestore y ChromaDB, y un fallo en cualquiera de
ellas se propagaba sin control desde despachar() hasta tumbar la
conversacion completa -- el mismo patron del hallazgo D en otra superficie.

El punto de despacho es el unico lugar del sistema por donde pasan TODAS
las herramientas, presentes y futuras. Protegerlo ahi, y no herramienta por
herramienta, es lo que convierte la correccion puntual en una garantia
estructural: cualquier herramienta que se agregue en el Sprint 3 hereda la
degradacion sin tener que acordarse de implementarla.

Se reutiliza deliberadamente el contrato {"disponible": False, "mensaje":
...} que el hallazgo D introdujo para el clima, en vez de definir una forma
de error nueva. El modelo ya demostro empiricamente (AG-07, primera
medicion real) que sabe interpretar ese contrato y seguir conversando con
las fuentes que si tiene; darle un segundo formato para la misma situacion
seria pedirle que aprenda dos convenciones donde basta una.
"""

import logging
from datetime import date
from pathlib import Path

import vertexai
from vertexai.generative_models import GenerativeModel, Part

from src.agents.wellness_coach.memory import MemoriaConversacional
from src.agents.wellness_coach.tools.registro import despachar, obtener_tool_vertexai
from src.data.repositorio_corredor import RepositorioCorredor
from src.utils.config import GCP_LOCATION, GCP_PROJECT, GEMINI_MODEL

logger = logging.getLogger(__name__)

MAX_ITERACIONES_HERRAMIENTAS = 5

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "agents" / "wellness_coach_agent.txt"

MENSAJE_EMPUJE_HERRAMIENTA = (
    "No describas lo que vas a hacer. Si necesitas informacion de una "
    "herramienta para responder, invocala ahora mismo mediante una llamada "
    "a funcion, en lugar de narrar la intencion o dar la respuesta por "
    "hecha sin haberla consultado."
)

RESPUESTA_REINTENTO_FALLIDO = (
    "No logré completar la consulta necesaria para responder con "
    "precisión en este momento. ¿Podrías intentar de nuevo o reformular "
    "tu pregunta?"
)

MENSAJE_HERRAMIENTA_NO_DISPONIBLE = (
    "Esta consulta no está disponible en este momento. Responde con la "
    "información que sí tengas, y di explícitamente que este dato no pudo "
    "consultarse en vez de suponerlo."
)

_FRASES_DECLARACION_SIN_INVOCAR = (
    "voy a consultar",
    "voy a revisar",
    "voy a buscar",
    "permiteme consultar",
    "permíteme consultar",
    "dejame revisar",
    "déjame revisar",
    "un momento mientras",
    "segun la base de conocimiento",
    "según la base de conocimiento",
    "de acuerdo a la base de conocimiento",
    "en nuestra base de conocimiento",
    "segun la informacion que tengo",
    "según la información que tengo",
)

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)


def _declara_uso_de_herramienta_sin_invocar(texto: str) -> bool:
    """Heuristica textual deliberadamente simple, con limitaciones conocidas.

    Detecta frases en espanol donde el modelo narra que va a usar una
    herramienta, o atribuye contenido a la base de conocimiento, sin haber
    emitido una llamada a funcion real en ese mismo turno.

    Limitaciones documentadas (ver tambien docs/agents/wellness-agent.md):
    - Falsos negativos: si el modelo declara la intencion con una frase no
      incluida en esta lista, no se detecta y el turno se cierra igual con
      una promesa incumplida. La lista se amplia empiricamente a medida que
      se observan nuevas formulaciones en evaluaciones futuras.
    - Falsos positivos: si el modelo usa alguna de estas frases de forma
      legitima sin que sea una promesa vacia, se gasta un reintento
      innecesario -- costo aceptable frente al riesgo de dejar pasar una
      atribucion falsa sin corregir.

    Quien llama a esta funcion es responsable de invocarla unicamente
    cuando todavia no se ha despachado ninguna herramienta en el turno
    actual: una vez que el agente si invoco consultar_base_conocimiento,
    decir despues "segun la base de conocimiento" es una cita legitima, no
    una atribucion falsa.
    """
    texto_normalizado = texto.lower()
    return any(frase in texto_normalizado for frase in _FRASES_DECLARACION_SIN_INVOCAR)


def _despachar_con_degradacion(
    nombre_funcion: str, argumentos: dict, user_id: str, ciudad: str | None
) -> tuple[dict, bool]:
    """Despacha una herramienta sin dejar que un fallo suyo tumbe el turno.

    Devuelve (resultado, degradada). Cuando la herramienta falla, el
    resultado es el contrato de no disponibilidad del hallazgo D, de modo
    que el modelo recibe una observacion valida y puede seguir razonando
    con las fuentes que si respondieron.

    Se captura Exception de forma amplia, a proposito: el objetivo no es
    anticipar que puede fallar en Firestore, ChromaDB o un servicio HTTP,
    sino garantizar que nada de lo que pase ahi adentro llegue a romper la
    conversacion. Un fallo de infraestructura y un ValueError por un nombre
    de herramienta que el modelo alucino producen la misma degradacion de
    cara al usuario; la distincion entre ambos vive en el log, no en la
    conversacion.

    El log lleva la excepcion real con traceback (logger.exception), y el
    modelo recibe unicamente un mensaje generico: exponer detalles internos
    de la infraestructura en la superficie conversacional no le sirve al
    corredor y filtra informacion del sistema.
    """
    try:
        return despachar(nombre_funcion, argumentos, user_id=user_id, ciudad=ciudad), False
    except Exception:
        logger.exception(
            "Fallo la herramienta '%s' con argumentos %s; se degrada el turno.",
            nombre_funcion,
            argumentos,
        )
        return {
            "disponible": False,
            "mensaje": MENSAJE_HERRAMIENTA_NO_DISPONIBLE,
        }, True


class WellnessCoachAgent:
    """Agente conversacional con memoria de largo plazo y tool calling."""

    def __init__(self) -> None:
        self.repositorio = RepositorioCorredor()
        self.memoria = MemoriaConversacional()

    def _construir_system_instruction(self, nivel: str, ciudad: str | None, historial_texto: str) -> str:
        plantilla = PROMPT_PATH.read_text(encoding="utf-8")
        return plantilla.format(
            fecha_actual=date.today().isoformat(),
            nivel=nivel,
            ciudad=ciudad or "no registrada",
            historial_conversacion=historial_texto,
        )

    def _crear_chat(self, nivel: str, ciudad: str | None, historial_texto: str):
        system_instruction = self._construir_system_instruction(nivel, ciudad, historial_texto)
        model = GenerativeModel(
            GEMINI_MODEL,
            tools=[obtener_tool_vertexai()],
            system_instruction=system_instruction,
        )
        return model.start_chat()

    def conversar(self, user_id: str, mensaje: str) -> dict:
        """Sostiene un turno de conversacion, resolviendo llamadas a
        herramientas antes de producir la respuesta final."""
        perfil = self.repositorio.obtener_perfil(user_id)
        historial = self.memoria.obtener_historial(user_id)
        historial_texto = self.memoria.formatear_para_prompt(historial)

        chat = self._crear_chat(perfil.nivel, perfil.ciudad, historial_texto)
        response = chat.send_message(mensaje)

        herramientas_invocadas: list[dict] = []
        herramientas_degradadas: list[str] = []
        limite_alcanzado = False
        reintento_utilizado = False
        reintento_fallido = False

        for _ in range(MAX_ITERACIONES_HERRAMIENTAS):
            function_calls = response.candidates[0].function_calls

            if not function_calls:
                sin_herramientas_aun = not herramientas_invocadas

                if (
                    sin_herramientas_aun
                    and not reintento_utilizado
                    and _declara_uso_de_herramienta_sin_invocar(response.text)
                ):
                    reintento_utilizado = True
                    response = chat.send_message(MENSAJE_EMPUJE_HERRAMIENTA)
                    continue

                if (
                    sin_herramientas_aun
                    and reintento_utilizado
                    and _declara_uso_de_herramienta_sin_invocar(response.text)
                ):
                    reintento_fallido = True

                break

            partes_respuesta = []
            for fc in function_calls:
                argumentos = dict(fc.args)
                resultado, degradada = _despachar_con_degradacion(
                    fc.name, argumentos, user_id=user_id, ciudad=perfil.ciudad
                )
                herramientas_invocadas.append({"nombre": fc.name, "argumentos": argumentos})
                if degradada:
                    herramientas_degradadas.append(fc.name)
                partes_respuesta.append(
                    Part.from_function_response(name=fc.name, response={"result": resultado})
                )

            response = chat.send_message(partes_respuesta)
        else:
            limite_alcanzado = True

        if limite_alcanzado:
            texto_final = (
                "No pude completar tu solicitud en este momento con la informacion "
                "disponible. ¿Podrias reformular tu pregunta?"
            )
        elif reintento_fallido:
            texto_final = RESPUESTA_REINTENTO_FALLIDO
        else:
            texto_final = response.text

        self.memoria.agregar_turno(user_id, "usuario", mensaje)
        self.memoria.agregar_turno(user_id, "agente", texto_final)

        return {
            "respuesta": texto_final,
            "herramientasInvocadas": herramientas_invocadas,
            "herramientasDegradadas": herramientas_degradadas,
            "limiteAlcanzado": limite_alcanzado,
            "reintentoUtilizado": reintento_utilizado,
            "reintentoFallido": reintento_fallido,
        }