"""Contrato de mensajes entre el orquestador y los agentes especializados.

Hasta S3-03 la comunicacion usaba diccionarios sueltos: cada adaptador del
registro devolvia las claves que le parecian y el orquestador confiaba en que
estuvieran. Funciona con dos agentes y se vuelve fragil con mas, porque nada
declara que debe viajar ni que puede faltar.

Estas dos estructuras fijan ese contrato. No son una capa de transporte: los
agentes viven en el mismo proceso y la invocacion es una llamada de funcion.
Son la definicion de QUE informacion acompana una delegacion y QUE informacion
vuelve, que es lo que el issue S3-04 pide definir y lo que haria falta
serializar si alguna vez estos agentes se separan en servicios distintos
(ver docs/architecture/interoperabilidad-mcp-a2a.md).

POR QUE EL user_id VIAJA EN LA SOLICITUD Y NO EN EL MENSAJE

Misma decision que el Sprint 2 tomo para despachar(): el identificador del
corredor lo inyecta el orquestador desde el contexto de la peticion, nunca
proviene del texto que escribio el usuario ni de una salida del modelo. Elimina
por construccion que un mensaje pueda inducir a consultar datos de otro
corredor.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SolicitudAgente:
    """Lo que el orquestador envia a un agente especializado.

    Attributes:
        traza_id: identificador de la solicitud completa del corredor. Es el
            mismo para todas las delegaciones originadas por un unico mensaje,
            de modo que un flujo con dos agentes se puede reconstruir entero
            correlacionando por este campo.
        user_id: corredor que origina la solicitud. Lo inyecta el orquestador.
        mensaje: texto dirigido al agente.
        intencion: categoria detectada por el clasificador.
        contexto: informacion que el agente necesita y no puede deducir por su
            cuenta. En un flujo de colaboracion lleva lo que aporto el agente
            anterior, para que el segundo no repita ni contradiga al primero.
        paso: posicion de esta delegacion dentro del flujo, empezando en 1. Con
            un solo agente siempre es 1; en colaboracion distingue quien fue
            primero.
    """

    traza_id: str
    user_id: str
    mensaje: str
    intencion: str
    contexto: str = ""
    paso: int = 1

    def mensaje_con_contexto(self) -> str:
        """Mensaje listo para entregar al agente, con el contexto antepuesto.

        El contexto se antepone al texto en vez de pasarse por un parametro
        aparte porque los agentes existentes reciben un unico mensaje: el
        Wellness Coach viene del Sprint 2 con la firma conversar(user_id,
        mensaje), y cambiarla obligaria a tocar su ciclo ReAct, sus pruebas y
        el script de evaluacion por una razon que no es suya.

        La alternativa -- un parametro 'contexto' en cada agente -- se deja
        anotada como mejora para cuando haya mas de dos agentes y el contexto
        deje de ser un bloque de texto.
        """
        if not self.contexto:
            return self.mensaje
        return (
            f"{self.mensaje}\n\n"
            f"---\n"
            f"CONTEXTO DE OTRO AGENTE DE LA PLATAFORMA\n"
            f"Otro especialista ya respondio la parte de la consulta que le "
            f"corresponde. Complementa esa respuesta desde tu dominio: no la "
            f"repitas, no la contradigas, y no invadas su especialidad.\n\n"
            f"{self.contexto}"
        )


@dataclass
class RespuestaAgente:
    """Lo que un agente especializado devuelve al orquestador.

    Attributes:
        agente: quien produjo la respuesta.
        texto: respuesta en lenguaje natural.
        herramientas_invocadas: nombres de las herramientas usadas. Vacia no
            significa que falte el dato: el Nutrition Agent no usa tool
            calling por diseno.
        fuentes: doc_id realmente recuperados, heredando la regla de citacion
            del Sprint 1.
        degradado: si alguna capacidad fallo durante la ejecucion. NO se marca
            cuando la base de conocimiento simplemente no cubre la pregunta:
            eso es el sistema funcionando y viaja en detalle.
        detalle: informacion especifica del agente, para trazabilidad.
        latencia_ms: cuanto tardo este agente en particular.
    """

    agente: str
    texto: str
    herramientas_invocadas: list[str] = field(default_factory=list)
    fuentes: list[str] = field(default_factory=list)
    degradado: bool = False
    detalle: dict = field(default_factory=dict)
    latencia_ms: int = 0