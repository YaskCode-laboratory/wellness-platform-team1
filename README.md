# Intelligent Wellness Platform

## Descripción

Plataforma de bienestar inteligente basada en agentes de IA especializados. El proyecto académico toma como caso de estudio **RunCoach AI**, una PWA de gestión de entrenamiento de running, y lo evoluciona hacia una arquitectura multi-agente con RAG (Retrieval-Augmented Generation).

Desarrollado como proyecto de la asignatura **Sistemas Inteligentes** — Maestría en Tecnologías de Información y Comunicación, Universidad del Zulia (LUZ).

## Objetivos

- Implementar un pipeline RAG sobre conocimiento de entrenamiento deportivo y bienestar
- Desarrollar agentes especializados: wellness (running), nutrición, motivación y analítica
- Orquestar los agentes mediante patrones A2A y MCP
- Evaluar la calidad de recuperación y generación con métricas estándar

## Arquitectura general

```
frontend/          React 18 + Vite PWA (RunCoach AI)
src/
  app/             FastAPI entry point
  agents/
    wellness/      Agente de entrenamiento running (RunCoach)
    nutrition/     Agente de nutrición deportiva
    motivation/    Agente de motivación y adherencia
    analytics/     Agente de análisis de rendimiento
    shared/        Base agent y utilidades comunes
  api/routes/      Endpoints REST
  database/        Cliente Firestore
  services/        Lógica de negocio (auth, etc.)
  rag/             Pipeline RAG: embeddings, retriever, generation
  orchestration/   Orquestador multi-agente, A2A, MCP
  knowledge/       Ingesta, chunking, ontología, taxonomía
  memory/          Memoria de agentes
  utils/           Prompt builder y helpers
prompts/agents/    Templates de prompts por agente
data/              Knowledge base, vector store, datasets
tests/             Unit, integración, RAG, multi-agente
```

## Tecnologías utilizadas

- **Backend:** Python 3.11, FastAPI, Uvicorn
- **IA/LLM:** Gemini 2.5 Flash via Vertex AI (GCP)
- **Base de datos:** Cloud Firestore (Firebase)
- **Autenticación:** Firebase Auth
- **Frontend:** React 18, Vite, TailwindCSS, PWA
- **Infraestructura:** GCP Cloud Run, Firebase Hosting

## Instalación y ejecución

```bash
# 1. Clonar el repositorio
git clone https://github.com/computing-laboratory/wellness-platform-team1.git
cd wellness-platform-team1

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configurar credenciales GCP
cp .env.example .env
# Editar .env con los valores correctos
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# 4. Ejecutar la API
uvicorn src.app.main:app --reload

# 5. Frontend (carpeta frontend/)
cd frontend
npm install
npm run dev
```

## Equipo

**Team 1**
- José Francisco Urdaneta Sánchez — Backend, infraestructura, IA
- Julio César Matute — Frontend, UI/UX

## Estado del proyecto

| Sprint | Tema | Estado |
|--------|------|--------|
| Sprint 1 | RAG / Knowledge Engineering | Entregado |
| Sprint 2 | Agentes Inteligentes | En progreso |
| Sprint 3 | Sistemas Multi-Agente | Pendiente |
