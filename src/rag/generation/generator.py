"""Generación de respuestas con Gemini a partir de contexto recuperado."""

import json

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from src.utils.config import GCP_LOCATION, GCP_PROJECT, GEMINI_MODEL

_model = None


def _get_model() -> GenerativeModel:
    """Inicializa el modelo generativo una sola vez."""
    global _model
    if _model is None:
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        _model = GenerativeModel(GEMINI_MODEL)
    return _model


def _limpiar_json(bruto: str) -> str:
    """Elimina el cercado markdown que a veces envuelve la respuesta."""
    texto = bruto.strip()
    if texto.startswith("```"):
        texto = texto.split("```")[1]
        if texto.startswith("json"):
            texto = texto[4:]
    return texto.strip()


def generar(prompt: str, temperatura: float = 0.2) -> dict:
    """Ejecuta el prompt contra Gemini y devuelve el JSON parseado.

    Temperatura baja: buscamos consistencia, no creatividad.
    """
    model = _get_model()

    respuesta = model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            temperature=temperatura,
            response_mime_type="application/json",
        ),
    )

    bruto = _limpiar_json(respuesta.text)

    try:
        return json.loads(bruto)
    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini no devolvió JSON válido: {e}\nRespuesta: {bruto[:400]}")