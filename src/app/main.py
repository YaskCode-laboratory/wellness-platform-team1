from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import agent_routes, auth_routes, orchestrator_routes

app = FastAPI(
    title="Intelligent Wellness Platform",
    description="Plataforma de bienestar inteligente con agentes especializados. Caso de estudio: RunCoach AI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agent_routes.router)
app.include_router(auth_routes.router)
app.include_router(orchestrator_routes.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "wellness-platform",
        "timestamp": datetime.utcnow().isoformat(),
    }