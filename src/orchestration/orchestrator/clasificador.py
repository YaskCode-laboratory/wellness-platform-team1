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
el SDK garantiza la forma, y los enum se generan desde el registro de agentes,
de modo que el clasificador no puede nombrar una intencion ni un dominio que
el orquestador no sepa resolver.

El parseo es defensivo de todas formas. Una respuesta malformada degrada a
"no_reconocida" con confianza cero, que el orquestador traduce en una peticion
de aclaracion -- nunca en una delegacion equivocada.

LAS SUBCONSULTAS

Saber que una pregunta es mixta no basta para atenderla: hay que saber a
quienes delegar, en que orden, y QUE preguntarle a cada uno.

La primera version de S3-04 entregaba el mensaje completo a los dos agentes.
Funcionaba, pero producia respuestas redundantes: el primer especialista
contestaba su parte y ademas derivaba la ajena al segundo, que respondia justo
debajo en la misma pantalla. El corredor leia "de eso se ocupa el otro
especialista" seguido inmediatamente del otro especialista.

Ahora el clasificador reparte la consulta: cada dominio recibe su propia
pregunta, autonoma y sin la parte que no le toca. El orden que devuelve
determina quien responde primero y cuya respuesta sirve de contexto al
siguiente.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date

import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

from src.utils.fechas import hoy
from src.orchestration.orchestrator.registro_agentes import (
    catalogo_para_prompt,
    intenciones_con_agente,
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
INTENCION_MIXTA = "mixta"

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)


@dataclass(frozen=True)
class SubConsulta:
    """La parte de una consulta mixta que corresponde a un dominio."""

    dominio: str
    mensaje: str


@dataclass
class Clasificacion:
    """Resultado de clasificar un mensaje."""

    intencion: str
    motivo: str
    confianza: float
    subconsultas: list[SubConsulta] = field(default_factory=list)

    @property
    def dominios(self) -> list[str]:
        """Nombres de los dominios implicados, en orden. Para la traza."""
        return [s.dominio for s in self.subconsultas]

    @property
    def es_confiable(self) -> bool:
        return self.confianza >= UMBRAL_CONFIANZA

    @property
    def es_colaboracion(self) -> bool:
        """True si la solicitud requiere mas de un agente y se sabe cuales."""
        return self.intencion == INTENCION_MIXTA and len(self.subconsultas) >= 2


def _esquema_respuesta() -> dict:
    """Esquema JSON que el modelo debe respetar.

    Los enum se construyen desde el registro en cada llamada, no se escriben
    aqui: registrar un agente nuevo amplia el conjunto de intenciones validas
    y de dominios delegables sin tocar este archivo.
    """
    return {
        "type": "object",
        "properties": {
            "intencion": {"type": "string", "enum": intenciones_validas()},
            "motivo": {"type": "string"},
            "confianza": {"type": "number"},
            "dominios": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "dominio": {"type": "string", "enum": intenciones_con_agente()},
                        "mensaje": {"type": "string"},
                    },
                    "required": ["dominio", "mensaje"],
                },
            },
        },
        "required": ["intencion", "motivo", "confianza", "dominios"],
    }


def _construir_prompt(mensaje: str) -> str:
    plantilla = load_prompt_template("clasificador_intencion", subcarpeta="orchestration")
    return plantilla.format(
        fecha_actual=hoy().isoformat(),
        catalogo_agentes=catalogo_para_prompt(),
        mensaje=mensaje,
    )


def _clasificacion_de_respaldo(motivo: str) -> Clasificacion:
    return Clasificacion(intencion=INTENCION_POR_DEFECTO, motivo=motivo, confianza=0.0)


def _subconsultas_validas(crudas, mensaje_original: str) -> list[SubConsulta]:
    """Convierte la lista cruda del modelo en subconsultas utilizables.

    Conserva el orden, porque determina quien responde primero y cuya
    respuesta sirve de contexto al siguiente. Descarta dominios desconocidos y
    repetidos: invocar dos veces al mismo agente en una solicitud no aporta y
    duplica latencia.

    Si el modelo nombra un dominio valido pero deja su mensaje vacio, se usa el
    mensaje original en vez de descartar la delegacion. Un agente con la
    pregunta entera responde de mas; un agente al que no se invoca deja un
    hueco silencioso en la respuesta, que es peor.
    """
    con_agente = intenciones_con_agente()
    vistos: set[str] = set()
    salida: list[SubConsulta] = []

    for cruda in crudas or []:
        if not isinstance(cruda, dict):
            continue
        dominio = str(cruda.get("dominio", ""))
        if dominio not in con_agente or dominio in vistos:
            continue
        vistos.add(dominio)

        submensaje = str(cruda.get("mensaje", "")).strip()
        if not submensaje:
            logger.warning(
                "El clasificador no redacto submensaje para el dominio '%s'; "
                "se usa el mensaje original.",
                dominio,
            )
            submensaje = mensaje_original

        salida.append(SubConsulta(dominio=dominio, mensaje=submensaje))

    return salida


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

    subconsultas = _subconsultas_validas(datos.get("dominios"), mensaje)

    # Una intencion mixta sin al menos dos dominios delegables es incoherente
    # consigo misma: el modelo afirma que hacen falta varios especialistas y no
    # sabe nombrarlos. Se trata como no confiable en vez de adivinar.
    if intencion == INTENCION_MIXTA and len(subconsultas) < 2:
        logger.warning(
            "Clasificacion mixta con dominios insuficientes: %r. Se pedira aclaracion.",
            [s.dominio for s in subconsultas],
        )
        return Clasificacion(
            intencion=INTENCION_MIXTA,
            motivo=str(datos.get("motivo", "")),
            confianza=0.0,
            subconsultas=subconsultas,
        )

    return Clasificacion(
        intencion=intencion,
        motivo=str(datos.get("motivo", "")),
        confianza=max(0.0, min(1.0, confianza)),
        subconsultas=subconsultas,
    )