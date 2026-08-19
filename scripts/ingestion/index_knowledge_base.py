"""Indexa la knowledge base en ChromaDB.

Idempotente: puede ejecutarse repetidamente sin duplicar contenido.
Cada documento se borra y reinserta, de modo que las modificaciones
se reflejan correctamente.

El orden de operaciones es deliberado: los embeddings se generan ANTES
de tocar el estado persistente, porque son el paso que puede fallar.

Uso:
    python -m scripts.ingestion.index_knowledge_base
"""

from collections import defaultdict
from pathlib import Path

from src.knowledge.chunking.chunker import chunk_knowledge_base
from src.rag.embeddings.embedder import embed_texts
from src.rag.vector_store.store import (
    borrar_documento,
    estadisticas,
    indexar_chunks,
)

RAIZ = Path(__file__).resolve().parents[2]
KB_DIR = RAIZ / "data" / "knowledge_base"


def main() -> None:
    print("=" * 70)
    print("INDEXACIÓN DE LA KNOWLEDGE BASE")
    print("=" * 70)

    print(f"\n[1/4] Chunking desde {KB_DIR.name}/")
    chunks = chunk_knowledge_base(KB_DIR)
    if not chunks:
        print("No hay chunks que indexar.")
        return
    print(f"      Total: {len(chunks)} chunks")

    # Los embeddings van PRIMERO: es el paso que puede fallar.
    # Solo tocamos el estado persistente cuando ya tenemos todo lo necesario.
    print(f"\n[2/4] Generando embeddings ({len(chunks)} textos)")
    vectores = embed_texts([c["texto"] for c in chunks], task_type="RETRIEVAL_DOCUMENT")

    por_doc = defaultdict(list)
    for c in chunks:
        por_doc[c["metadata"]["doc_id"]].append(c)

    print(f"\n[3/4] Limpiando versiones previas de {len(por_doc)} documentos")
    for doc_id in por_doc:
        borrados = borrar_documento(doc_id)
        if borrados:
            print(f"      {doc_id}: {borrados} chunks previos eliminados")

    print(f"\n[4/4] Insertando en ChromaDB")
    total = indexar_chunks(chunks, vectores)
    print(f"      {total} chunks indexados")

    stats = estadisticas()
    print("\n" + "=" * 70)
    print(f"COLECCIÓN: {stats['total_chunks']} chunks")
    print("=" * 70)
    for doc_id, n in sorted(stats["por_documento"].items()):
        print(f"  {doc_id}: {n:3d} chunks")


if __name__ == "__main__":
    main()