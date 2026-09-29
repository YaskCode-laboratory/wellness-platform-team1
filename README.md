# Intelligent Wellness Platform

## Descripción

Plataforma de bienestar inteligente basada en agentes de IA especializados. El proyecto académico toma como caso de estudio **RunCoach AI**, una PWA de gestión de entrenamiento de running, y lo evoluciona hacia una arquitectura multiagente con RAG (Retrieval-Augmented Generation).

Desarrollado como proyecto de la asignatura **Sistemas Inteligentes** — Maestría en Tecnologías de Información y Comunicación, Universidad del Zulia (LUZ).

## Estado del proyecto

| Sprint | Tema | Estado |
|--------|------|--------|
| Sprint 1 | Ingeniería del conocimiento y RAG | Entregado |
| Sprint 2 | Agentes inteligentes | Entregado |
| Sprint 3 | Sistemas multiagente | Entregado |

## Qué hace el sistema hoy

Un **Orchestrator Agent** recibe cada consulta del corredor, determina qué dominio de conocimiento hace falta y delega en el agente competente. Cuando la consulta toca dos dominios, la reparte entre ambos y consolida las respuestas atribuyendo qué aportó cada especialista.

| Agente | Dominio |
|---|---|
| **Wellness Coach** | Entrenamiento de running: carga, intensidad, lesiones, tapering, recuperación, progreso |
| **Nutrition** | Alimentación e hidratación del corredor |

Las respuestas se fundamentan en una **knowledge base curada de siete documentos** con nivel de evidencia declarado, y las citas se validan programáticamente contra los fragmentos realmente recuperados.

Cada solicitud produce una **traza completa** —intención detectada, agente elegido y por qué, qué se le pidió a cada uno, qué consultó, cuánto tardó— que viaja en la respuesta y se persiste en Firestore.

El agente de recomendación del Sprint 1 sigue disponible en su endpoint propio, con sus dos modos (`legacy` y `rag`) y el endpoint `/compare` que los contrasta sobre el mismo estado del corredor.

## Arquitectura

```
frontend/          React 18 + Vite PWA (RunCoach AI)
src/
  app/             FastAPI entry point
  agents/
    wellness/      Agente de recomendación de un turno (Sprint 1)
    wellness_coach/  Agente conversacional: memoria, herramientas, ReAct (Sprint 2)
    nutrition/     Agente de nutrición (Sprint 3)
    shared/        BaseAgent y utilidades comunes
  orchestration/
    orchestrator/  Clasificación de intención, delegación, consolidación
    communication/ Contrato de mensajes entre agentes
    delegation/    Registro persistente de delegaciones
  data/            RepositorioCorredor: acceso a datos del corredor
  rag/             Pipeline RAG: chunking, embeddings, retriever, generación
  api/routes/      Endpoints REST
  database/        Cliente Firestore
  services/        Lógica de negocio (auth)
  utils/           Configuración y construcción de prompts
prompts/
  agents/          Prompts de cada agente
  orchestration/   Prompt del clasificador de intención
data/
  knowledge_base/  Siete documentos curados con front-matter
  vector_store/    Índice ChromaDB persistente
  evaluation/      Golden sets y resultados de cada corrida
scripts/
  evaluation/      Siembra y evaluación de los agentes
  verificacion/    Comprobación de las integraciones externas
  ingestion/       Indexación de la knowledge base
tests/unit/        Suite de pruebas con mocks
docs/              Documentación técnica — ver docs/README.md
```

Diagramas del flujo multiagente: `docs/architecture/orchestration-flow.md`

## Tecnologías

- **Backend:** Python 3.11, FastAPI, Uvicorn
- **IA/LLM:** Gemini 2.5 Flash y text-embedding-004 vía Vertex AI (GCP)
- **Vector store:** ChromaDB (persistente, espacio coseno)
- **Base de datos:** Cloud Firestore
- **Autenticación:** Firebase Auth
- **API externa:** Open-Meteo (clima, sin autenticación)
- **Frontend:** React 18, Vite, TailwindCSS, PWA
- **CI:** GitHub Actions

## Instalación y ejecución

```bash
# 1. Clonar
git clone https://github.com/YaskCode-laboratory/wellness-platform-team1.git
cd wellness-platform-team1

# 2. Entorno virtual (Python 3.11) e instalación
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configuración
cp .env.example .env
# Editar .env. Para desarrollo local basta con Application Default Credentials:
gcloud auth application-default login
gcloud auth application-default set-quota-project <tu-proyecto>

# 4. Indexar la knowledge base (una sola vez)
python -m scripts.ingestion.index_knowledge_base

# 5. Comprobar que las integraciones responden
python -m scripts.evaluation.seed_agent_test_user
python -m scripts.verificacion.verificar_integraciones

# 6. Levantar la API
python -m uvicorn src.app.main:app --reload

# 7. Frontend
cd frontend
npm install
npm run dev
```

Detalle completo en `docs/deployment/local-setup.md`.

## Uso

```bash
# Conversación a través del sistema multiagente
curl -s -X POST "http://localhost:8000/orchestrator/{userId}/chat" \
  -H "Content-Type: application/json" \
  -d '{"mensaje": "Como voy esta semana respecto a mi meta?"}' | python -m json.tool

# Recomendación de un turno, comparando los modos legacy y RAG
curl -s -X POST "http://localhost:8000/agent/{userId}/compare" | python -m json.tool
```

## Pruebas y evaluación

```bash
# Suite completa (con mocks, no requiere credenciales)
python -m unittest discover -s tests -p "test_*.py" -v

# Evaluación del flujo multiagente contra servicios reales
python -m scripts.evaluation.seed_agent_test_user
python -u -m scripts.evaluation.evaluate_multiagent
```

La suite corre también en GitHub Actions ante cada PR hacia `develop` o `main`, sin secrets de GCP: las pruebas usan mocks y no tocan ningún servicio externo.

Resultados y hallazgos de cada sprint en `docs/evaluation/`.

## Equipo

**Team 1**
- José Francisco Urdaneta Sánchez — Backend, infraestructura, IA
- Julio César Matute — Frontend, UI/UX

Docente: **Dra. Yaskelly Yedra** — Sistemas Inteligentes

## Documentación

Índice completo en **`docs/README.md`**, que incluye además qué rutas del scaffold quedaron sin usar y por qué.
