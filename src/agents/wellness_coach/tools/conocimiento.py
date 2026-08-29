"""Herramienta que envuelve el retriever RAG del Sprint 1 para exponerlo al
modelo via function calling. No se reimplementa la recuperacion: se
reutiliza src.rag.retriever.retriever.recuperar() sin modificarlo.
"""

from src.rag.retriever.retriever import recuperar

TOP_K_CONVERSACIONAL = 3


def consultar_base_conocimiento(consulta: str) -> dict:
    """Recupera fragmentos relevantes de la knowledge base curada.

    A diferencia del modo RAG de un solo turno, la consulta aqui la formula
    el propio modelo a partir del turno actual y el contexto conversacional
    relevante (ver docs/agents/wellness-agent.md #4), no se sintetiza a
    partir del estado del corredor.
    """
    chunks = recuperar(consulta, k=TOP_K_CONVERSACIONAL)

    if not chunks:
        return {
            "fragmentos": [],
            "mensaje": "No se encontro informacion relevante en la base de conocimiento.",
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