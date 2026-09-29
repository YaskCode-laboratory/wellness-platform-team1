"""Registro de agentes participantes del sistema multiagente.

_AGENTES es la fuente de verdad, como diccionarios Python simples que se
pueden inspeccionar libremente (incluido en pruebas). Es el mismo patron que
_HERRAMIENTAS del Sprint 2 (src/agents/wellness_coach/tools/registro.py), y
por la misma razon: la lista declarativa es lo que se lee para construir el
catalogo del clasificador, y lo que se recorre para resolver una delegacion.
Agregar un agente es agregar una entrada, no tocar el orquestador.

Las instancias se crean de forma perezosa y se memorizan. Construir un agente
abre conexiones reales (Firestore, Vertex AI), y el registro se importa desde
las pruebas del orquestador, que no deben tocar la red -- misma leccion que el
cliente perezoso de Firestore del issue #10.

DOMINIOS PREVISTOS SIN AGENTE

_DOMINIOS_SIN_AGENTE declara dominios que pertenecen a la plataforma pero que
todavia no tienen un agente que los atienda, para que el clasificador pueda
distinguir tres situaciones que no son lo mismo: un dominio propio sin agente,
un tema ajeno a la plataforma, y un mensaje sin intencion clasificable. Sin esa
distincion, una pregunta de un dominio previsto se clasificaria como fuera de
dominio y el corredor recibiria una redireccion incorrecta.

La lista esta vacia al cerrar S3-03: la nutricion, que era su unica entrada en
S3-02, paso a _AGENTES al implementarse el Nutrition Agent. El mecanismo se
conserva porque el roadmap de la plataforma contempla agentes de motivacion y
analitica, y porque graduar un dominio de una lista a la otra es exactamente el
camino previsto para incorporarlos.

ESTADO EN S3-03

Dos agentes registrados: el Wellness Coach (agente especializado asignado al
equipo, construido en el Sprint 2) y el Nutrition Agent (segundo participante,
necesario para que exista colaboracion que verificar). La delegacion sigue
siendo a un solo agente por solicitud; la intencion mixta se reconoce pero su
atencion corresponde a S3-04.
"""

from src.agents.nutrition.agent import NutritionAgent
from src.agents.wellness_coach.agent import WellnessCoachAgent

_instancias: dict[str, object] = {}


def _obtener_instancia(clave: str, constructor):
    """Construye el agente la primera vez que se necesita y lo memoriza."""
    if clave not in _instancias:
        _instancias[clave] = constructor()
    return _instancias[clave]


def _invocar_wellness_coach(user_id: str, mensaje: str) -> dict:
    """Adaptador entre el contrato del orquestador y el del Wellness Coach.

    El Coach devuelve las claves que definio el Sprint 2 (respuesta,
    herramientasInvocadas, herramientasDegradadas...). El orquestador no
    deberia conocer esa forma: cada agente puede tener la suya. Este
    adaptador traduce, y es el unico lugar del sistema que sabe como habla
    este agente en particular.

    Es lo que mantiene separada la logica de orquestacion de la logica de los
    agentes, que es criterio de aceptacion de S3-02.
    """
    agente = _obtener_instancia("wellness_coach", WellnessCoachAgent)
    resultado = agente.conversar(user_id, mensaje)

    return {
        "texto": resultado["respuesta"],
        "herramientas_invocadas": [h["nombre"] for h in resultado["herramientasInvocadas"]],
        "degradado": bool(resultado["herramientasDegradadas"]),
        "detalle_agente": {
            "herramientas_degradadas": resultado["herramientasDegradadas"],
            "limite_alcanzado": resultado["limiteAlcanzado"],
            "reintento_utilizado": resultado["reintentoUtilizado"],
            "reintento_fallido": resultado["reintentoFallido"],
        },
    }


def _invocar_nutrition(user_id: str, mensaje: str) -> dict:
    """Adaptador entre el contrato del orquestador y el del Nutrition Agent.

    El Nutrition Agent no invoca herramientas: recupera y responde en una sola
    llamada. 'herramientas_invocadas' queda vacia a proposito, y no es un dato
    ausente sino una caracteristica de su diseno. La trazabilidad de lo que
    consulto viaja en 'fragmentos_recuperados'.

    QUE CUENTA COMO DEGRADACION Y QUE NO

    Solo una cita inventada degrada. Desde la correccion S2-04, 'degradado'
    significa en este sistema que una capacidad fallo: un servicio caido, una
    consulta que no se pudo completar, una fuente que el agente afirma haber
    usado y nunca recibio.

    Que la base de conocimiento no cubra una pregunta NO es una degradacion.
    Es el sistema funcionando como debe: el agente recupero lo que habia,
    comprobo que no alcanzaba, y lo declaro en vez de rellenarlo con
    conocimiento general no verificado. Contar eso como fallo haria que la
    conducta correcta se registrara igual que un error, y contaminaria la
    medicion de S3-06 -- exactamente el problema que agent-evaluation.md
    documento sobre las metricas que mezclan situaciones distintas.

    La cobertura viaja en 'cubierto', dentro del detalle, para que pueda
    medirse por separado: es una senal sobre la knowledge base, no sobre el
    agente.
    """
    agente = _obtener_instancia("nutrition", NutritionAgent)
    resultado = agente.responder(user_id, mensaje)

    return {
        "texto": resultado["respuesta"],
        "herramientas_invocadas": [],
        "degradado": bool(resultado["fuentesInventadas"]),
        "detalle_agente": {
            "fuentes": resultado["fuentes"],
            "fuentes_inventadas": resultado["fuentesInventadas"],
            "fragmentos_recuperados": resultado["fragmentosRecuperados"],
            "cubierto": resultado["cubierto"],
        },
    }


_AGENTES = [
    {
        "nombre": "wellness_coach",
        "intencion": "entrenamiento",
        "titulo": "Wellness Coach Agent",
        "descripcion": (
            "Entrenamiento de running: carga semanal y su progresion, zonas de "
            "intensidad y umbrales, distribucion de intensidad, prevencion de "
            "lesiones por sobreuso, tapering, recuperacion y sueno, progreso "
            "respecto a objetivos, y condiciones climaticas para entrenar."
        ),
        "invocador": _invocar_wellness_coach,
    },
    {
        "nombre": "nutrition",
        "intencion": "nutricion",
        "titulo": "Nutrition Agent",
        "descripcion": (
            "Alimentacion e hidratacion del corredor: que comer antes, durante "
            "y despues de entrenar, reposicion de carbohidratos y electrolitos, "
            "hidratacion, y pautas nutricionales para resistencia."
        ),
        "invocador": _invocar_nutrition,
    },
]

_DOMINIOS_SIN_AGENTE: list[dict] = []

# Intenciones que no corresponden a un dominio concreto de la plataforma.
# El orquestador las resuelve por su cuenta, sin delegar.
INTENCIONES_GENERICAS = ("mixta", "fuera_de_dominio", "no_reconocida")


def intenciones_con_agente() -> list[str]:
    """Intenciones que hoy tienen un agente registrado que las atienda."""
    return [a["intencion"] for a in _AGENTES]


def intenciones_validas() -> list[str]:
    """Todas las intenciones que el clasificador puede devolver."""
    return (
        intenciones_con_agente()
        + [d["intencion"] for d in _DOMINIOS_SIN_AGENTE]
        + list(INTENCIONES_GENERICAS)
    )


def catalogo_para_prompt() -> str:
    """Descripcion de los dominios disponibles, para el prompt del clasificador.

    Se genera a partir de las listas declarativas en vez de escribirse a mano
    en el prompt: asi registrar un agente nuevo lo hace visible al clasificador
    automaticamente, sin que nadie tenga que acordarse de editar el texto. En
    el Sprint 2, dos de los seis hallazgos fueron desajustes entre lo que el
    prompt describia y lo que el codigo hacia.

    Los dominios sin agente se anuncian igual: el clasificador debe poder
    reconocerlos para que el orquestador responda con honestidad en vez de
    tratarlos como temas ajenos a la plataforma.
    """
    lineas = []
    for a in _AGENTES:
        lineas.append(f'- intencion "{a["intencion"]}" -> {a["titulo"]}')
        lineas.append(f'  {a["descripcion"]}')
    for d in _DOMINIOS_SIN_AGENTE:
        lineas.append(f'- intencion "{d["intencion"]}" -> {d["titulo"]}')
        lineas.append(f'  {d["descripcion"]}')
    return "\n".join(lineas)


def resolver(intencion: str) -> dict | None:
    """Devuelve la entrada del agente que atiende esa intencion, o None.

    None significa dos cosas distintas que el orquestador diferencia: que la
    intencion es generica (no le corresponde ningun dominio) o que es un
    dominio previsto sin agente todavia.
    """
    for a in _AGENTES:
        if a["intencion"] == intencion:
            return a
    return None


def es_dominio_sin_agente(intencion: str) -> bool:
    """True si la intencion es un dominio de la plataforma aun sin agente."""
    return any(d["intencion"] == intencion for d in _DOMINIOS_SIN_AGENTE)