"""Clasificador de intenciones del Orchestrator Agent.

Determina que dominio de conocimiento hace falta para atender un mensaje del
corredor. No responde, no consulta datos, no invoca herramientas: solo
clasifica.

POR QUE UN LLM Y NO REGLAS

Las reglas por palabras clave fallan en los dos casos que mas importan. El
primero son las preguntas mixtas, que son justamente las que S3-04 exige
demostrar: "que como antes de una tirada larga y como ajusto el entrenamiento"
contiene terminos de ambos dominios y una regla tendria que decidir cual pesa
mas. El segundo son las preguntas donde el dominio no aparece en el texto:
"me siento sin energia en los ultimos kilometros" no menciona comida, pero su
respuesta depende del dominio nutricional.

Ademas, el modelo devuelve el motivo de su eleccion, que entra en la traza de
la solicitud. Una regla no explica por que descarto las alternativas.

GARANTIA ESTRUCTURAL SOBRE EL FORMATO

La respuesta se restringe con response_schema, no con instrucciones en el
prompt. El Sprint 2 dejo claro el limite de confiar un contrato al texto: los
hallazgos C, E y F son tres manifestaciones distintas del mismo problema. Aqui
el SDK garantiza la forma, y el enum de intenciones se genera desde el
registro de agentes, de modo que el clasificador no puede inventar una
intencion que el orquestador no sepa resolver.

El parseo es defensivo de todas formas. Una respuesta malformada degrada a
"no_reconocida" con confianza cero, que el orquestador traduce en una peticion
de aclaracion -- nunca en una delegacion equivocada.
"""

import json
import logging
from dataclasses import dataclass
from datetime import date

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from src.orchestration.orchestrator.registro_agentes import (
    catalogo_para_prompt,
    intenciones_validas,
)
from src.utils.config import GCP_LOCATION, GCP_PROJECT, GEMINI_MODEL
from src.utils.prompt_builder import load_prompt_template

logger = logging.getLogger(__name__)

# Por debajo de este valor el orquestador pide aclaracion en vez de delegar.
# Una delegacion equivocada es peor que una pregunta de mas: el corredor
# recibe una respuesta del dominio incorrecto sin saber que fue un error.
UMBRAL_CONFIANZA = 0.5

INTENCION_POR_DEFECTO = "no_reconocida"

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)


@dataclass
class Clasificacion:
    """Resultado de clasificar un mensaje."""

    intencion: str
    motivo: str
    confianza: float

    @property
    def es_confiable(self) -> bool:
        return self.confianza >= UMBRAL_CONFIANZA


def _esquema_respuesta() -> dict:
    """Esquema JSON que el modelo debe respetar.

    El enum se construye desde el registro en cada llamada, no se escribe
    aqui: registrar un agente nuevo amplia el conjunto de intenciones validas
    sin tocar este archivo.
    """
    return {
        "type": "object",
        "properties": {
            "intencion": {"type": "string", "enum": intenciones_validas()},
            "motivo": {"type": "string"},
            "confianza": {"type": "number"},
        },
        "required": ["intencion", "motivo", "confianza"],
    }


def _construir_prompt(mensaje: str) -> str:
    plantilla = load_prompt_template("clasificador_intencion", subcarpeta="orchestration")
    return plantilla.format(
        fecha_actual=date.today().isoformat(),
        catalogo_agentes=catalogo_para_prompt(),
        mensaje=mensaje,
    )


def _clasificacion_de_respaldo(motivo: str) -> Clasificacion:
    return Clasificacion(intencion=INTENCION_POR_DEFECTO, motivo=motivo, confianza=0.0)


def clasificar(mensaje: str) -> Clasificacion:
    """Determina la intencion de un mensaje del corredor.

    Nunca lanza excepcion: un fallo del clasificador degrada a
    "no_reconocida", que el orquestador traduce en una peticion de aclaracion.
    Que el sistema no sepa a quien delegar es recuperable; que se caiga por
    intentar averiguarlo, no.
    """
    modelo = GenerativeModel(
        GEMINI_MODEL,
        generation_config=GenerationConfig(
            # temperature 0: la clasificacion debe ser reproducible. El Sprint 2
            # cerro con una leccion sobre resultados que cambiaban entre
            # corridas identicas, y una decision de enrutamiento no deberia
            # depender del muestreo.
            temperature=0,
            response_mime_type="application/json",
            response_schema=_esquema_respuesta(),
        ),
    )

    try:
        respuesta = modelo.generate_content(_construir_prompt(mensaje))
        datos = json.loads(respuesta.text)
    except Exception:
        logger.exception("Fallo la clasificacion de intencion; se degrada a no_reconocida.")
        return _clasificacion_de_respaldo("No se pudo determinar la intencion: el clasificador no respondio.")

    intencion = datos.get("intencion")
    if intencion not in intenciones_validas():
        logger.error("El clasificador devolvio una intencion desconocida: %r", intencion)
        return _clasificacion_de_respaldo(f"El clasificador devolvio una intencion no reconocida ({intencion!r}).")

    try:
        confianza = float(datos.get("confianza", 0.0))
    except (TypeError, ValueError):
        confianza = 0.0

    return Clasificacion(
        intencion=intencion,
        motivo=str(datos.get("motivo", "")),
        confianza=max(0.0, min(1.0, confianza)),
    )