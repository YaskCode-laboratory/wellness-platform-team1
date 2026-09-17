"""Recuperación semántica sobre la knowledge base wellness."""

from src.rag.embeddings.embedder import embed_query
from src.rag.vector_store.store import buscar

TOP_K = 5


def recuperar(
    consulta: str,
    k: int = TOP_K,
    categoria: str | None = None,
    categorias: list[str] | None = None,
    nivel_evidencia: str | None = None,
) -> list[dict]:
    """Recupera los k chunks más relevantes para una consulta.

    Args:
        consulta: pregunta o contexto en lenguaje natural
        k: número de chunks a recuperar
        categoria: filtra por una categoría de la taxonomía (opcional)
        categorias: filtra por varias categorías a la vez (opcional)
        nivel_evidencia: filtra por nivel de evidencia (opcional)

    El filtro por varias categorías se agrega en el Sprint 3 (issue S3-03)
    para sostener la frontera de responsabilidad entre agentes. El Wellness
    Coach accede a seis de las siete categorías de la taxonomía y el Nutrition
    Agent a la restante, de modo que ninguno puede recuperar documentos del
    dominio del otro. Esa frontera vive aquí y no solo en el prompt: los
    hallazgos E y F del Sprint 2 mostraron que una instrucción de texto
    describe el comportamiento deseado pero no lo garantiza.

    Returns:
        Lista de chunks ordenados por similitud descendente.
    """
    if categoria and categorias:
        raise ValueError(
            "Usa 'categoria' para una sola categoría o 'categorias' para varias, "
            "no ambas: combinarlas haría ambiguo el filtro resultante."
        )

    # La consulta se embebe con RETRIEVAL_QUERY, distinto de los documentos
    vector = embed_query(consulta)

    # Filtro de metadata para ChromaDB.
    # Con más de una condición hay que envolverlas en $and
    condiciones = []
    if categoria:
        condiciones.append({"categoria": categoria})
    if categorias:
        condiciones.append({"categoria": {"$in": list(categorias)}})
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

    # Demostración de la frontera entre agentes (S3-03): la misma consulta
    # restringida a las categorías del Wellness Coach no devuelve nutrición.
    print("\n\n" + "=" * 78)
    print("MISMA CONSULTA, RESTRINGIDA A LAS CATEGORÍAS DEL WELLNESS COACH")
    print("=" * 78)
    resultados = recuperar(
        "cuánto debo consumir al entrenar",
        k=3,
        categorias=[
            "carga_entrenamiento",
            "zonas_fisiologicas",
            "distribucion_intensidad",
            "prevencion_lesiones",
            "tapering",
            "recuperacion",
        ],
    )
    print(formatear_resultados(resultados))