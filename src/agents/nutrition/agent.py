"""Nutrition Agent: especialista en alimentacion e hidratacion del corredor.

ALCANCE Y POR QUE ES MAS SIMPLE QUE EL WELLNESS COACH

Este agente se incorpora en el Sprint 3 como segundo participante del sistema
multiagente. El agente especializado asignado al equipo es el Wellness Coach;
el Nutrition Agent existe porque los criterios de aceptacion de S3-04 y S3-06
exigen un escenario verificable de colaboracion entre agentes, y con un unico
agente especializado la delegacion degenera en un enrutador con un solo
destino.

Es deliberadamente mas simple que el Coach: una sola llamada al modelo sobre
contexto recuperado, sin ciclo ReAct, sin tool calling y sin memoria
conversacional. No es una version incompleta de algo que deberia ser mayor:
es lo que su responsabilidad requiere. Una pregunta nutricional se responde
con documentacion curada y el peso del corredor, no con una secuencia de
decisiones sobre que consultar. Anadirle un ciclo de razonamiento seria pagar
latencia y complejidad por una capacidad que no necesita.

Las limitaciones que se derivan de esa simplicidad estan documentadas en
LIMITACIONES, mas abajo, tal como exige el criterio de aceptacion de S3-03.

FRONTERA DE DOMINIO

La recuperacion se restringe a la categoria 'nutricion' (KB-006). Las otras
seis categorias de la taxonomia pertenecen al Wellness Coach y este agente no
puede recuperarlas: la frontera se aplica en el filtro, no solo en el prompt.

MANEJO DE ERRORES

Este agente no captura excepciones propias a proposito. La proteccion vive en
el punto de despacho del orquestador (_delegar), que es por donde pasan todas
las invocaciones a agentes: protegerla ahi significa que cualquier agente que
se registre despues la hereda sin implementarla. Es la misma decision que la
correccion S2-04 tomo un nivel mas abajo para las herramientas.

LIMITACIONES

- Sin memoria conversacional: cada pregunta se responde de forma aislada. No
  recuerda lo dicho en turnos anteriores ni lo que respondio el Coach.
- Sin acceso al historial de entrenamiento: conoce el nivel y el peso del
  corredor, no sus sesiones ni su carga. Una pauta que dependa del volumen
  real de entrenamiento queda fuera de su alcance.
- Una sola fuente documental (KB-006). La cobertura del dominio nutricional
  es, por tanto, estrecha: responde bien sobre carbohidratos, hidratacion y
  reposicion, y declara el vacio en lo demas.
"""

from datetime import date

from src.utils.fechas import hoy
from src.data.repositorio_corredor import RepositorioCorredor
from src.rag.generation.generator import generar
from src.rag.pipeline.rag_pipeline import validar_fuentes
from src.rag.retriever.retriever import recuperar
from src.utils.prompt_builder import load_prompt_template

CATEGORIA_NUTRICION = "nutricion"
TOP_K = 3

MENSAJE_SIN_COBERTURA = (
    "No encontré información sobre eso en la base de conocimiento de nutrición "
    "de la plataforma. Prefiero decírtelo antes que darte una recomendación sin "
    "respaldo. ¿Quieres preguntarme otra cosa sobre alimentación o hidratación?"
)


def _formatear_fragmentos(chunks: list[dict]) -> str:
    """Representacion de los fragmentos recuperados para el prompt."""
    bloques = []
    for c in chunks:
        meta = c["metadata"]
        bloques.append(
            f"[{meta['doc_id']}] {meta['titulo']} — sección: {meta['seccion']}\n"
            f"{c['texto']}"
        )
    return "\n\n".join(bloques)


class NutritionAgent:
    """Agente especializado en nutricion del corredor."""

    def __init__(self) -> None:
        self.repositorio = RepositorioCorredor()

    def responder(self, user_id: str, mensaje: str) -> dict:
        """Responde una pregunta nutricional fundamentada en la knowledge base.

        Devuelve la respuesta junto con las fuentes validadas. La validacion
        es programatica y no depende del prompt: el Sprint 1 documento que un
        modelo puede citar documentos que nunca recibio, y en un sistema cuya
        ventaja es la trazabilidad, una cita inventada anula el beneficio.
        """
        chunks = recuperar(mensaje, k=TOP_K, categoria=CATEGORIA_NUTRICION)

        if not chunks:
            return {
                "respuesta": MENSAJE_SIN_COBERTURA,
                "fuentes": [],
                "fuentesInventadas": [],
                "fragmentosRecuperados": [],
                "cubierto": False,
            }

        perfil = self.repositorio.obtener_perfil(user_id)
        plantilla = load_prompt_template("nutrition_agent")

        prompt = plantilla.format(
            fecha_actual=hoy().isoformat(),
            nivel=perfil.nivel,
            peso=f"{perfil.peso} kg" if perfil.peso else "no registrado",
            fragmentos=_formatear_fragmentos(chunks),
            mensaje=mensaje,
        )

        salida = generar(prompt)

        validas, inventadas = validar_fuentes(salida.get("fuentes", []), chunks)

        return {
            "respuesta": salida.get("respuesta", ""),
            "fuentes": validas,
            "fuentesInventadas": inventadas,
            "fragmentosRecuperados": [c["metadata"]["doc_id"] for c in chunks],
            "cubierto": bool(salida.get("cubierto", True)),
        }