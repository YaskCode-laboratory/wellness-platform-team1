"""Herramienta que envuelve el retriever RAG del Sprint 1 para exponerlo al
modelo via function calling. No se reimplementa la recuperacion: se
reutiliza src.rag.retriever.retriever.recuperar() sin modificar su logica.

FRONTERA DE DOMINIO (issue S3-03)

La recuperacion queda restringida a las categorias que corresponden al
dominio del Wellness Coach. La categoria 'nutricion' (KB-006) pertenece al
Nutrition Agent y no se incluye aqui.

Esto no es una optimizacion de la busqueda: es la frontera de responsabilidad
entre agentes, aplicada donde el modelo no tiene margen de interpretacion. El
prompt tambien lo dice, pero el prompt describe el comportamiento deseado y
no lo garantiza -- los hallazgos E y F del Sprint 2 documentan tres rondas de
medicion corrigiendo una conducta que el prompt ya describia correctamente.
Aqui, aunque el prompt fallara, los fragmentos de nutricion no llegan al
contexto del Coach y por lo tanto no puede citarlos.
"""

from src.rag.retriever.retriever import recuperar

TOP_K_CONVERSACIONAL = 3

# Seis de las siete categorias de la taxonomia del Sprint 1. La septima,
# 'nutricion', es del Nutrition Agent.
CATEGORIAS_COACH = [
    "carga_entrenamiento",
    "zonas_fisiologicas",
    "distribucion_intensidad",
    "prevencion_lesiones",
    "tapering",
    "recuperacion",
]


def consultar_base_conocimiento(consulta: str) -> dict:
    """Recupera fragmentos relevantes del dominio de entrenamiento.

    A diferencia del modo RAG de un solo turno, la consulta aqui la formula
    el propio modelo a partir del turno actual y el contexto conversacional
    relevante (ver docs/agents/wellness-agent.md #4), no se sintetiza a
    partir del estado del corredor.
    """
    chunks = recuperar(
        consulta,
        k=TOP_K_CONVERSACIONAL,
        categorias=CATEGORIAS_COACH,
    )

    if not chunks:
        return {
            "fragmentos": [],
            "mensaje": (
                "No se encontro informacion relevante en la base de conocimiento "
                "de entrenamiento. Si la pregunta es de nutricion, corresponde a "
                "otro agente de la plataforma."
            ),
        }

    return {
        "fragmentos": [
            {
                "doc_id": c["metadata"]["doc_id"],
                "titulo": c["metadata"]["titulo"],
                "texto": c["texto"],
                "similitud": round(c["similitud"], 4),
            }
            for c in chunks
        ],
        "doc_ids_disponibles": [c["metadata"]["doc_id"] for c in chunks],
    }