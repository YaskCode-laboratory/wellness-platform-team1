"""Recuperación semántica sobre la knowledge base wellness."""

from src.rag.embeddings.embedder import embed_query
from src.rag.vector_store.store import buscar

TOP_K = 5


def recuperar(
    consulta: str,
    k: int = TOP_K,
    categoria: str | None = None,
    nivel_evidencia: str | None = None,
) -> list[dict]:
    """Recupera los k chunks más relevantes para una consulta.

    Args:
        consulta: pregunta o contexto en lenguaje natural
        k: número de chunks a recuperar
        categoria: filtra por categoría de la taxonomía (opcional)
        nivel_evidencia: filtra por nivel de evidencia (opcional)

    Returns:
        Lista de chunks ordenados por similitud descendente.
    """
    # La consulta se embebe con RETRIEVAL_QUERY, distinto de los documentos
    vector = embed_query(consulta)

    # Filtro de metadata para ChromaDB.
    # Con más de una condición hay que envolverlas en $and
    condiciones = []
    if categoria:
        condiciones.append({"categoria": categoria})
    if nivel_evidencia:
        condiciones.append({"nivel_evidencia": nivel_evidencia})

    if len(condiciones) == 1:
        filtro = condiciones[0]
    elif len(condiciones) > 1:
        filtro = {"$and": condiciones}
    else:
        filtro = None

    return buscar(vector, k=k, filtro=filtro)


def formatear_resultados(resultados: list[dict], ancho: int = 78) -> str:
    """Representación legible de los resultados para inspección manual."""
    lineas = []
    for n, r in enumerate(resultados, 1):
        meta = r["metadata"]
        barra = "█" * int(r["similitud"] * 30)
        lineas.append(f"\n[{n}] similitud {r['similitud']:.4f}  {barra}")
        lineas.append(f"    documento : {meta['titulo']}")
        lineas.append(f"    sección   : {meta['seccion']}")
        lineas.append(f"    categoría : {meta['categoria']}  |  evidencia: {meta['nivel_evidencia']}")
        texto = r["texto"].replace("\n", " ")[:ancho * 2]
        lineas.append(f"    texto     : {texto}...")
    return "\n".join(lineas)


if __name__ == "__main__":
    consultas = [
        "¿Es cierto que no debo aumentar más de 10% mi kilometraje semanal?",
        "Cuánto tengo que bajar el volumen antes de mi maratón",
        "Me duele la rodilla cuando corro, qué hago",
        "Cuántas horas debo dormir si entreno fuerte",
        "Qué es la zona 2 y para qué sirve",
    ]

    for consulta in consultas:
        print("\n" + "=" * 78)
        print(f"CONSULTA: {consulta}")
        print("=" * 78)
        resultados = recuperar(consulta, k=3)
        print(formatear_resultados(resultados))

    # Demostración de filtrado por metadata
    print("\n\n" + "=" * 78)
    print("MISMA CONSULTA, FILTRADA POR CATEGORÍA = nutricion")
    print("=" * 78)
    resultados = recuperar("cuánto debo consumir al entrenar", k=3, categoria="nutricion")
    print(formatear_resultados(resultados))