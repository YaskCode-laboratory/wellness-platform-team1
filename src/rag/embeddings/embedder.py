"""Generación de embeddings con Vertex AI."""

import vertexai
from vertexai.language_models import TextEmbeddingInput, TextEmbeddingModel

GCP_PROJECT = "runcoach-ai-496921"
GCP_LOCATION = "us-central1"
EMBEDDING_MODEL = "text-embedding-004"

# El límite de Vertex AI es por TOKENS totales por petición (20.000),
# no por cantidad de textos. Usamos un presupuesto con margen de seguridad.
MAX_TOKENS_LOTE = 15000
MAX_TEXTOS_LOTE = 25
CHARS_POR_TOKEN = 3          # estimación conservadora para español

_model = None


def _get_model() -> TextEmbeddingModel:
    """Inicializa el modelo una sola vez (lazy singleton)."""
    global _model
    if _model is None:
        vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
        _model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL)
    return _model


def _estimar_tokens(texto: str) -> int:
    """Estimación conservadora de tokens a partir de caracteres."""
    return len(texto) // CHARS_POR_TOKEN + 1


def _agrupar_en_lotes(textos: list[str]) -> list[list[str]]:
    """Agrupa respetando el límite de tokens Y el de cantidad."""
    lotes: list[list[str]] = []
    actual: list[str] = []
    tokens_actual = 0

    for texto in textos:
        tokens = _estimar_tokens(texto)

        excede_tokens = tokens_actual + tokens > MAX_TOKENS_LOTE
        excede_cantidad = len(actual) >= MAX_TEXTOS_LOTE

        if actual and (excede_tokens or excede_cantidad):
            lotes.append(actual)
            actual = []
            tokens_actual = 0

        actual.append(texto)
        tokens_actual += tokens

    if actual:
        lotes.append(actual)

    return lotes


def embed_texts(textos: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    """Convierte una lista de textos en una lista de vectores.

    task_type:
        RETRIEVAL_DOCUMENT -> textos que se indexan
        RETRIEVAL_QUERY    -> consultas del usuario
    """
    model = _get_model()
    lotes = _agrupar_en_lotes(textos)
    vectores: list[list[float]] = []

    for n, lote in enumerate(lotes, 1):
        entradas = [TextEmbeddingInput(text=t, task_type=task_type) for t in lote]
        respuesta = model.get_embeddings(entradas)
        vectores.extend(emb.values for emb in respuesta)
        print(f"      lote {n}/{len(lotes)} → {len(vectores)}/{len(textos)} textos")

    return vectores


def embed_query(consulta: str) -> list[float]:
    """Embebe una consulta de usuario. Atajo para el retriever."""
    return embed_texts([consulta], task_type="RETRIEVAL_QUERY")[0]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Similitud coseno entre dos vectores."""
    producto = sum(x * y for x, y in zip(a, b))
    norma_a = sum(x * x for x in a) ** 0.5
    norma_b = sum(y * y for y in b) ** 0.5
    return producto / (norma_a * norma_b)


if __name__ == "__main__":
    print("Generando embeddings de prueba...\n")

    textos = [
        "El tapering implica reducir el volumen entre 41% y 60% antes de competir",
        "¿Cuánto debo bajar los kilómetros las semanas previas a mi maratón?",
        "La regla del 10% carece de respaldo científico sólido",
        "Los hidratos de carbono se consumen a razón de 30 a 60 gramos por hora",
    ]

    docs = embed_texts(textos, task_type="RETRIEVAL_DOCUMENT")

    print(f"\nDimensiones del vector: {len(docs[0])}")
    print(f"Primeros 8 valores    : {[round(v, 4) for v in docs[0][:8]]}\n")

    print("=" * 70)
    print("SIMILITUD COSENO ENTRE PARES")
    print("=" * 70)

    pares = [
        (0, 1, "tapering (afirmación) vs pregunta sobre tapering"),
        (0, 2, "tapering vs regla del 10%"),
        (0, 3, "tapering vs nutrición"),
        (2, 3, "regla del 10% vs nutrición"),
    ]

    for i, j, etiqueta in pares:
        sim = cosine_similarity(docs[i], docs[j])
        barra = "█" * int(sim * 40)
        print(f"{sim:.4f}  {barra:<40s} {etiqueta}")

    print("\n--- EFECTO DE task_type ---")
    query_correcta = embed_query(textos[1])
    print(f"Pregunta como DOCUMENT : {cosine_similarity(docs[0], docs[1]):.4f}")
    print(f"Pregunta como QUERY    : {cosine_similarity(docs[0], query_correcta):.4f}")