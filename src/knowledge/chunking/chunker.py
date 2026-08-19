"""Chunking de documentos de la knowledge base wellness.

Estrategia híbrida consciente de la estructura:
  1. Corte primario por encabezados '##' (fronteras semánticas reales)
  2. Subdivisión por tamaño solo si la sección excede el límite
  3. Propagación de metadata del front-matter a cada chunk
"""

import re
from pathlib import Path

import yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120

# Campos del front-matter que se propagan como metadata de cada chunk.
# ChromaDB solo acepta str | int | float | bool, por eso las listas se aplanan.
CAMPOS_METADATA = ["doc_id", "titulo", "categoria", "nivel_evidencia"]
CAMPOS_LISTA = ["referencias", "entidades_ontologia", "conceptos_taxonomia"]

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
    separators=["\n\n", "\n", ". ", " ", ""],
    length_function=len,
)


def parse_front_matter(raw: str) -> tuple[dict, str]:
    """Separa el front-matter YAML del cuerpo markdown."""
    if not raw.lstrip().startswith("---"):
        return {}, raw

    partes = raw.split("---", 2)
    if len(partes) < 3:
        return {}, raw

    try:
        meta = yaml.safe_load(partes[1]) or {}
    except yaml.YAMLError:
        meta = {}

    return meta, partes[2].strip()


def split_by_headers(body: str) -> list[tuple[str, str]]:
    """Divide el cuerpo en secciones usando encabezados de nivel 2 ('##')."""
    piezas = re.split(r"^## (.+)$", body, flags=re.MULTILINE)

    secciones: list[tuple[str, str]] = []

    # piezas[0] es el texto anterior al primer '##'. Suele contener solo el
    # título H1, que no aporta contenido recuperable: lo descartamos.
    preambulo = re.sub(r"^#\s+.*$", "", piezas[0], flags=re.MULTILINE).strip()
    if len(preambulo) >= 50:
        secciones.append(("Introducción", preambulo))

    # A partir de ahí la lista alterna: titulo, cuerpo, titulo, cuerpo...
    for i in range(1, len(piezas), 2):
        titulo = piezas[i].strip()
        cuerpo = piezas[i + 1].strip() if i + 1 < len(piezas) else ""
        if cuerpo:
            secciones.append((titulo, cuerpo))

    return secciones

def _construir_metadata(front_matter: dict) -> dict:
    """Aplana el front-matter a un dict compatible con ChromaDB."""
    meta = {}

    for campo in CAMPOS_METADATA:
        meta[campo] = str(front_matter.get(campo, ""))

    for campo in CAMPOS_LISTA:
        valor = front_matter.get(campo, [])
        meta[campo] = "; ".join(str(v) for v in valor) if valor else ""

    return meta


def chunk_document(path: Path) -> list[dict]:
    """Convierte un documento markdown en una lista de chunks con metadata."""
    raw = path.read_text(encoding="utf-8")
    front_matter, body = parse_front_matter(raw)

    meta_base = _construir_metadata(front_matter)
    meta_base["archivo"] = path.name

    chunks: list[dict] = []

    for titulo_seccion, contenido in split_by_headers(body):
        # Solo subdividimos si la sección excede el tamaño objetivo
        if len(contenido) <= CHUNK_SIZE:
            fragmentos = [contenido]
        else:
            fragmentos = _splitter.split_text(contenido)

        for fragmento in fragmentos:
            fragmento = fragmento.strip()
            if len(fragmento) < 50:      # descarta residuos sin valor semántico
                continue

            metadata = dict(meta_base)
            metadata["seccion"] = titulo_seccion
            metadata["chunk_index"] = len(chunks)

            # Prefijo contextual: evita que el chunk pierda su referencia
            texto_contextualizado = (
                f"[{meta_base['titulo']} › {titulo_seccion}]\n\n{fragmento}"
            )

            chunks.append({"texto": texto_contextualizado, "metadata": metadata})

    return chunks


def chunk_knowledge_base(kb_dir: Path) -> list[dict]:
    """Procesa todos los .md del directorio de knowledge base."""
    todos: list[dict] = []

    for path in sorted(kb_dir.glob("*.md")):
        chunks = chunk_document(path)
        todos.extend(chunks)
        print(f"  {path.name:45s} → {len(chunks):3d} chunks")

    return todos


if __name__ == "__main__":
    kb = Path(__file__).resolve().parents[3] / "data" / "knowledge_base"

    print(f"Knowledge base: {kb}\n")
    chunks = chunk_knowledge_base(kb)

    if not chunks:
        print("\nNo se generaron chunks. ¿Hay archivos .md en data/knowledge_base/?")
        raise SystemExit(1)

    tamanos = [len(c["texto"]) for c in chunks]
    print(f"\n{'='*60}")
    print(f"Total chunks    : {len(chunks)}")
    print(f"Tamaño promedio : {sum(tamanos) // len(tamanos)} chars")
    print(f"Mínimo / Máximo : {min(tamanos)} / {max(tamanos)} chars")
    print(f"{'='*60}\n")

    print("--- PRIMER CHUNK ---")
    print("METADATA:", chunks[0]["metadata"])
    print("\nTEXTO:")
    print(chunks[0]["texto"][:400])