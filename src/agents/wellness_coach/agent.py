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
"""

from datetime import date
from pathlib import Path

import vertexai
from vertexai.generative_models import GenerativeModel, Part

from src.agents.wellness_coach.memory import MemoriaConversacional
from src.agents.wellness_coach.tools.registro import despachar, obtener_tool_vertexai
from src.data.repositorio_corredor import RepositorioCorredor
from src.utils.config import GCP_LOCATION, GCP_PROJECT, GEMINI_MODEL

MAX_ITERACIONES_HERRAMIENTAS = 5

PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "agents" / "wellness_coach_agent.txt"

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)


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
        limite_alcanzado = False

        for _ in range(MAX_ITERACIONES_HERRAMIENTAS):
            function_calls = response.candidates[0].function_calls
            if not function_calls:
                break

            partes_respuesta = []
            for fc in function_calls:
                argumentos = dict(fc.args)
                resultado = despachar(fc.name, argumentos, user_id=user_id, ciudad=perfil.ciudad)
                herramientas_invocadas.append({"nombre": fc.name, "argumentos": argumentos})
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
        else:
            texto_final = response.text

        self.memoria.agregar_turno(user_id, "usuario", mensaje)
        self.memoria.agregar_turno(user_id, "agente", texto_final)

        return {
            "respuesta": texto_final,
            "herramientasInvocadas": herramientas_invocadas,
            "limiteAlcanzado": limite_alcanzado,
        }