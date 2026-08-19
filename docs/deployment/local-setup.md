# Instalación y Ejecución Local

**Plataforma Inteligente Wellness 2.0 — Equipo 1**

---

## 1. Requisitos

| Requisito | Versión | Nota |
|---|---|---|
| Python | 3.11+ | El sistema puede traer 3.9; verificar |
| Node.js | 18+ | Solo para el frontend |
| Google Cloud SDK | Reciente | Requiere Python 3.10–3.14 |
| Acceso a GCP | — | Proyecto `runcoach-ai-496921` |

---

## 2. Backend

### 2.1 Entorno virtual

```bash
git clone https://github.com/computing-laboratory/wellness-platform-team1.git
cd wellness-platform-team1

python3.11 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

python --version                  # debe reportar 3.11.x
```

> **macOS:** el `python3` del sistema suele ser 3.9. Si Homebrew tiene 3.11, invocar la ruta completa: `/opt/homebrew/bin/python3.11 -m venv venv`

### 2.2 Dependencias

```bash
pip install -r requirements.txt
```

Verificación:

```bash
python -c "
import chromadb, yaml
from langchain_text_splitters import RecursiveCharacterTextSplitter
import vertexai
print('chromadb', chromadb.__version__)
print('splitters OK')
print('vertexai OK')
"
```

### 2.3 Credenciales GCP

El sistema emplea Application Default Credentials.

```bash
gcloud config set project runcoach-ai-496921
gcloud auth application-default login
gcloud auth application-default set-quota-project runcoach-ai-496921
```

> **Si `gcloud` falla por versión de Python**, anteponer la variable:
> `CLOUDSDK_PYTHON=/opt/homebrew/bin/python3.11 gcloud auth application-default login`

**Verificar el proyecto activo.** Si las ADC apuntan a otro proyecto, las consultas a Firestore fallarán contra la base equivocada. El proyecto se declara explícitamente en `src/database/firestore_client.py`, pero conviene alinear también la configuración de `gcloud`.

### 2.4 Variables de entorno

```bash
cp .env.example .env
```

Ver `docs/deployment/environment-variables.md` para el detalle.

### 2.5 Indexar la knowledge base

Necesario en la primera ejecución y tras modificar documentos de `data/knowledge_base/`:

```bash
python -m scripts.ingestion.index_knowledge_base
```

Salida esperada:

```
COLECCIÓN: 82 chunks
  KB-001:  13 chunks
  ...
```

El proceso es idempotente: puede ejecutarse repetidamente sin duplicar contenido.

### 2.6 Levantar la API

```bash
python -m uvicorn src.app.main:app --reload --port 8080
```

Documentación interactiva en http://127.0.0.1:8080/docs

> Ejecutar siempre **desde la raíz del repositorio** y usando `python -m`, para que los imports absolutos `from src...` resuelvan correctamente.

---

## 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Disponible en http://localhost:5173

Por defecto apunta al backend desplegado en Cloud Run. Para usar el backend local, ajustar la URL de la API en `frontend/.env`.

---

## 4. Verificación del pipeline

Cada módulo del pipeline puede ejecutarse de forma aislada:

```bash
# Chunking: muestra fragmentos generados y estadísticas
python -m src.knowledge.chunking.chunker

# Embeddings: verifica el espacio semántico con similitud coseno
python -m src.rag.embeddings.embedder

# Recuperación: consultas de ejemplo con resultados y similitudes
python -m src.rag.retriever.retriever

# Pipeline completo: recomendación con trazabilidad
python -m src.rag.pipeline.rag_pipeline

# Evaluación de recuperación
python -m scripts.evaluation.evaluate_retrieval
python -m scripts.evaluation.evaluate_retrieval --k 3
```

---

## 5. Endpoints principales

```
POST /agent/{userId}/analyze?mode=rag       Recomendación con RAG
POST /agent/{userId}/analyze?mode=legacy    Recomendación sin RAG
POST /agent/{userId}/compare                Ambos modos, comparativa
GET  /agent/{userId}/recommendation         Última recomendación
GET  /health                                Estado del servicio
```

---

## 6. Incidencias frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| `ModuleNotFoundError: No module named 'src'` | Ejecución fuera de la raíz | `cd` a la raíz del repositorio |
| `ResolutionImpossible` al instalar | Conflicto de dependencias | Verificar `requirements.txt` sin modificaciones |
| Error de índice de Firestore | Consulta con índice compuesto | Ya evitado en el código; revisar consultas nuevas |
| `The query requires an index` con proyecto ajeno | ADC apunta a otro proyecto | `gcloud auth application-default set-quota-project runcoach-ai-496921` |
| `input token count is N but the model supports up to 20000` | Lote de embeddings excesivo | Ya resuelto por batching; revisar `MAX_TOKENS_LOTE` |
| `Failed to send telemetry event` | Incompatibilidad ChromaDB/PostHog | Inocuo; ya silenciado en `store.py` |
| `UserWarning: This feature is deprecated` | SDK Vertex AI | Inocuo; migración pendiente |

---

## 7. Estructura relevante

```
data/
  knowledge_base/     documentos curados (fuente de verdad)
  vector_store/       índice ChromaDB (regenerable)
  evaluation/         conjunto de referencia y resultados
prompts/
  agents/             plantilla del modo legacy
  rag/                plantilla del modo RAG
src/
  knowledge/          ontología, taxonomía, chunking
  rag/                embeddings, vector store, retriever, pipeline, generación
  agents/wellness/    agente con modo dual
  api/routes/         endpoints REST
scripts/
  ingestion/          indexación de la knowledge base
  evaluation/         evaluación de recuperación
```
