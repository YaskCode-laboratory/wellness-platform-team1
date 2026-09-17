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

LOS ADAPTADORES (S3-04)

Cada agente tiene un invocador que recibe una SolicitudAgente y devuelve una
RespuestaAgente. Es el unico lugar del sistema que conoce la forma concreta en
que habla cada agente: el Coach devuelve las claves camelCase que definio el
Sprint 2, el Nutrition Agent devuelve las suyas, y el orquestador no ve
ninguna de las dos.

Esa traduccion es lo que sostiene el criterio de aceptacion de S3-02 sobre
separar la coordinacion de los agentes. Sin ella, cambiar el contrato interno
de un agente obligaria a tocar el orquestador.

DOMINIOS PREVISTOS SIN AGENTE

_DOMINIOS_SIN_AGENTE declara dominios que pertenecen a la plataforma pero que
todavia no tienen agente, para que el clasificador distinga un dominio propio
sin atender de un tema ajeno a la plataforma. Esta vacia al cerrar S3-03: la
nutricion, su unica entrada en S3-02, paso a _AGENTES. El mecanismo se conserva
para los agentes de motivacion y analitica que contempla el roadmap.
"""

from src.agents.nutrition.agent import NutritionAgent
from src.agents.wellness_coach.agent import WellnessCoachAgent
from src.orchestration.communication.contratos import RespuestaAgente, SolicitudAgente

_instancias: dict[str, object] = {}


def _obtener_instancia(clave: str, constructor):
    """Construye el agente la primera vez que se necesita y lo memoriza."""
    if clave not in _instancias:
        _instancias[clave] = constructor()
    return _instancias[clave]


def _invocar_wellness_coach(solicitud: SolicitudAgente) -> RespuestaAgente:
    """Adaptador del Wellness Coach.

    LIMITACION CONOCIDA: el Coach no expone sus fuentes de forma estructurada.
    Cita los doc_id dentro de su prosa, gobernado por las reglas de citacion de
    su prompt, pero su contrato de salida no las devuelve como lista. Por eso
    'fuentes' queda vacia aqui, y no porque no haya citado nada.

    Extraerlas exigiria cambiar el contrato de salida del ciclo ReAct del
    Sprint 2, que es trabajo de ese componente y no de este adaptador. Se anota
    para S3-06, donde la trazabilidad de fuentes se va a medir.
    """
    agente = _obtener_instancia("wellness_coach", WellnessCoachAgent)
    resultado = agente.conversar(solicitud.user_id, solicitud.mensaje_con_contexto())

    return RespuestaAgente(
        agente="wellness_coach",
        texto=resultado["respuesta"],
        herramientas_invocadas=[h["nombre"] for h in resultado["herramientasInvocadas"]],
        fuentes=[],
        degradado=bool(resultado["herramientasDegradadas"]),
        detalle={
            "herramientas_degradadas": resultado["herramientasDegradadas"],
            "limite_alcanzado": resultado["limiteAlcanzado"],
            "reintento_utilizado": resultado["reintentoUtilizado"],
            "reintento_fallido": resultado["reintentoFallido"],
        },
    )


def _invocar_nutrition(solicitud: SolicitudAgente) -> RespuestaAgente:
    """Adaptador del Nutrition Agent.

    'herramientas_invocadas' queda vacia por diseno: este agente recupera y
    responde en una sola llamada, sin tool calling. Lo que consulto viaja en
    'fuentes' y en el detalle.

    QUE CUENTA COMO DEGRADACION Y QUE NO

    Solo una cita inventada degrada. Desde la correccion S2-04, 'degradado'
    significa que una capacidad fallo. Que la base de conocimiento no cubra una
    pregunta NO es una degradacion: es el sistema funcionando: el agente
    comprobo que no alcanzaba y lo declaro en vez de rellenarlo con
    conocimiento no verificado. Contarlo como fallo registraria la conducta
    correcta igual que un error y contaminaria la medicion de S3-06. La
    cobertura viaja en el detalle, para medirse por separado: es una senal
    sobre la knowledge base, no sobre el agente.
    """
    agente = _obtener_instancia("nutrition", NutritionAgent)
    resultado = agente.responder(solicitud.user_id, solicitud.mensaje_con_contexto())

    return RespuestaAgente(
        agente="nutrition",
        texto=resultado["respuesta"],
        herramientas_invocadas=[],
        fuentes=resultado["fuentes"],
        degradado=bool(resultado["fuentesInventadas"]),
        detalle={
            "fuentes_inventadas": resultado["fuentesInventadas"],
            "fragmentos_recuperados": resultado["fragmentosRecuperados"],
            "cubierto": resultado["cubierto"],
        },
    )


_AGENTES = [
    {
        "nombre": "wellness_coach",
        "intencion": "entrenamiento",
        "titulo": "Wellness Coach Agent",
        "etiqueta": "Sobre tu entrenamiento",
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
        "etiqueta": "Sobre tu alimentacion",
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
    """Devuelve la entrada del agente que atiende esa intencion, o None."""
    for a in _AGENTES:
        if a["intencion"] == intencion:
            return a
    return None


def es_dominio_sin_agente(intencion: str) -> bool:
    """True si la intencion es un dominio de la plataforma aun sin agente."""
    return any(d["intencion"] == intencion for d in _DOMINIOS_SIN_AGENTE)