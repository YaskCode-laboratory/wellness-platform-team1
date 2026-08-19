"""Métricas de evaluación para recuperación de información."""


def precision_at_k(docs_recuperados: list[str], docs_esperados: list[str], k: int) -> float:
    """Proporción de los k recuperados que son relevantes.

    Responde: de lo que traje, ¿cuánto sirve?
    """
    if k == 0:
        return 0.0
    top_k = docs_recuperados[:k]
    aciertos = sum(1 for d in top_k if d in docs_esperados)
    return aciertos / len(top_k)


def recall_at_k(docs_recuperados: list[str], docs_esperados: list[str], k: int) -> float:
    """Proporción de los documentos esperados que aparecen en los k recuperados.

    Responde: de lo que debía traer, ¿cuánto traje?
    """
    if not docs_esperados:
        return 0.0
    top_k = set(docs_recuperados[:k])
    encontrados = sum(1 for d in set(docs_esperados) if d in top_k)
    return encontrados / len(set(docs_esperados))


def reciprocal_rank(docs_recuperados: list[str], docs_esperados: list[str]) -> float:
    """Inverso de la posición del primer resultado relevante.

    Penaliza que lo relevante aparezca abajo. Si el primer acierto está en
    posición 1 vale 1.0; en posición 3 vale 0.333; si no aparece, 0.
    """
    for posicion, doc in enumerate(docs_recuperados, start=1):
        if doc in docs_esperados:
            return 1.0 / posicion
    return 0.0


def hit_rate(docs_recuperados: list[str], docs_esperados: list[str], k: int) -> float:
    """1.0 si al menos un documento esperado aparece en el top-k, 0.0 si no.

    Métrica binaria: mide si el sistema 'no falló del todo'.
    """
    top_k = set(docs_recuperados[:k])
    return 1.0 if any(d in top_k for d in docs_esperados) else 0.0


def evaluar_caso(docs_recuperados: list[str], docs_esperados: list[str], k: int) -> dict:
    """Calcula todas las métricas para un caso individual."""
    return {
        "precision_at_k": round(precision_at_k(docs_recuperados, docs_esperados, k), 4),
        "recall_at_k": round(recall_at_k(docs_recuperados, docs_esperados, k), 4),
        "reciprocal_rank": round(reciprocal_rank(docs_recuperados, docs_esperados), 4),
        "hit": hit_rate(docs_recuperados, docs_esperados, k),
    }


def agregar(resultados: list[dict]) -> dict:
    """Promedia las métricas sobre todos los casos.

    El promedio de reciprocal_rank sobre el conjunto es el MRR
    (Mean Reciprocal Rank).
    """
    if not resultados:
        return {}

    n = len(resultados)
    return {
        "n_casos": n,
        "precision_at_k": round(sum(r["precision_at_k"] for r in resultados) / n, 4),
        "recall_at_k": round(sum(r["recall_at_k"] for r in resultados) / n, 4),
        "mrr": round(sum(r["reciprocal_rank"] for r in resultados) / n, 4),
        "hit_rate": round(sum(r["hit"] for r in resultados) / n, 4),
    }