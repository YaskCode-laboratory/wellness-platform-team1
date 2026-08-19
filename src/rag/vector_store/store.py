"""Gestión de la base vectorial ChromaDB."""

import hashlib
import logging
import os
from pathlib import Path

# La telemetría de ChromaDB tiene una incompatibilidad de firma con PostHog
# en esta versión. Se desactiva por entorno y se silencia el logger.
os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)

import chromadb
from chromadb.config import Settings

import chromadb
from chromadb.config import Settings

COLLECTION_NAME = "wellness_knowledge"
VECTOR_STORE_DIR = Path(__file__).resolve().parents[3] / "data" / "vector_store"

_client = None


def get_client() -> chromadb.ClientAPI:
    """Cliente persistente de ChromaDB (lazy singleton)."""
    global _client
    if _client is None:
        VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(VECTOR_STORE_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection():
    """Obtiene o crea la colección configurada con espacio coseno.

    IMPORTANTE: sin hnsw:space=cosine, Chroma usa distancia L2 por defecto.
    """
    return get_client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def chunk_id(doc_id: str, chunk_index: int, texto: str) -> str:
    """ID determinista: mismo contenido produce siempre el mismo ID."""
    huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]
    return f"{doc_id}-{chunk_index:03d}-{huella}"


def borrar_documento(doc_id: str) -> int:
    """Elimina todos los chunks de un documento. Habilita re-indexación limpia."""
    coleccion = get_collection()
    existentes = coleccion.get(where={"doc_id": doc_id})
    ids = existentes.get("ids", [])
    if ids:
        coleccion.delete(ids=ids)
    return len(ids)


def indexar_chunks(chunks: list[dict], vectores: list[list[float]]) -> int:
    """Inserta chunks con sus vectores en la colección."""
    coleccion = get_collection()

    ids = [
        chunk_id(c["metadata"]["doc_id"], c["metadata"]["chunk_index"], c["texto"])
        for c in chunks
    ]

    coleccion.add(
        ids=ids,
        documents=[c["texto"] for c in chunks],
        embeddings=vectores,
        metadatas=[c["metadata"] for c in chunks],
    )
    return len(ids)


def buscar(vector_consulta: list[float], k: int = 5, filtro: dict | None = None) -> list[dict]:
    """Búsqueda por similitud. Devuelve los k chunks más cercanos.

    Chroma devuelve DISTANCIA. En espacio coseno: similitud = 1 - distancia.
    """
    coleccion = get_collection()

    resultado = coleccion.query(
        query_embeddings=[vector_consulta],
        n_results=k,
        where=filtro,
    )

    salida = []
    for i in range(len(resultado["ids"][0])):
        salida.append({
            "id": resultado["ids"][0][i],
            "texto": resultado["documents"][0][i],
            "metadata": resultado["metadatas"][0][i],
            "distancia": resultado["distances"][0][i],
            "similitud": 1 - resultado["distances"][0][i],
        })
    return salida


def estadisticas() -> dict:
    """Estado actual de la colección."""
    coleccion = get_collection()
    total = coleccion.count()
    todos = coleccion.get() if total else {"metadatas": []}

    por_doc: dict[str, int] = {}
    for meta in todos.get("metadatas", []):
        clave = meta.get("doc_id", "?")
        por_doc[clave] = por_doc.get(clave, 0) + 1

    return {"total_chunks": total, "por_documento": por_doc}