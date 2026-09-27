"""Registro central de herramientas del Wellness Coach Agent.

_HERRAMIENTAS es la fuente de verdad, como diccionarios Python simples que
se pueden inspeccionar libremente (incluido en pruebas). Los objetos del
SDK de Vertex AI (FunctionDeclaration, Tool) estan respaldados por
protobuf y no garantizan lectura de vuelta de los valores con los que se
construyen -- se arman a partir de esta lista unicamente en el momento de
hablar con Gemini, nunca se inspeccionan despues de construidos.
"""

from vertexai.generative_models import FunctionDeclaration, Tool

from src.agents.wellness_coach.tools.clima import consultar_clima
from src.agents.wellness_coach.tools.conocimiento import consultar_base_conocimiento
from src.agents.wellness_coach.tools.historial import (
    consultar_historial_sesiones,
    consultar_progreso_objetivo,
)

_HERRAMIENTAS = [
    {
        "name": "consultar_historial_sesiones",
        "description": "Devuelve las sesiones de entrenamiento mas recientes del corredor.",
        "parameters": {
            "type": "object",
            "properties": {
                "n": {"type": "integer", "description": "Cantidad de sesiones a devolver, por defecto 5"},
            },
        },
    },
    {
        "name": "consultar_progreso_objetivo",
        "description": "Compara la carga semanal actual del corredor contra su meta activa.",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_clima",
        "description": (
            "Devuelve condiciones climaticas actuales de la ciudad del corredor. "
            "Usar solo si la pregunta involucra entrenar hoy o en dias proximos "
            "y el clima es relevante."
        ),
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "consultar_base_conocimiento",
        "description": (
            "Recupera fragmentos verificables de la base de conocimiento sobre "
            "carga de entrenamiento, lesiones, nutricion, tapering, recuperacion "
            "y zonas de intensidad. Usar para cualquier pregunta de dominio."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "consulta": {
                    "type": "string",
                    "description": "Consulta en lenguaje natural, incorporando contexto conversacional relevante.",
                },
            },
            "required": ["consulta"],
        },
    },
]


def obtener_tool_vertexai() -> Tool:
    """Construye el objeto Tool del SDK a partir de _HERRAMIENTAS.

    Se arma en cada llamada, no se cachea como objeto SDK a nivel de modulo,
    para que _HERRAMIENTAS siga siendo la unica fuente de verdad editable.
    """
    declaraciones = [
        FunctionDeclaration(
            name=h["name"],
            description=h["description"],
            parameters=h["parameters"],
        )
        for h in _HERRAMIENTAS
    ]
    return Tool(function_declarations=declaraciones)


def despachar(nombre_funcion: str, argumentos: dict, user_id: str, ciudad: str | None = None) -> dict:
    """Ejecuta la herramienta que el modelo decidio invocar.

    user_id y ciudad no vienen del modelo: se inyectan desde el contexto de
    la conversacion (perfil del corredor ya cargado), para que el modelo no
    pueda ni necesite especificar de que usuario o de que ciudad quiere
    datos -- siempre son los del corredor que esta conversando.
    """
    if nombre_funcion == "consultar_historial_sesiones":
        n = argumentos.get("n", 5)
        return consultar_historial_sesiones(user_id, n=n)

    if nombre_funcion == "consultar_progreso_objetivo":
        return consultar_progreso_objetivo(user_id)

    if nombre_funcion == "consultar_clima":
        return consultar_clima(ciudad)

    if nombre_funcion == "consultar_base_conocimiento":
        consulta = argumentos.get("consulta", "")
        return consultar_base_conocimiento(consulta)

    raise ValueError(f"Herramienta desconocida: '{nombre_funcion}'")