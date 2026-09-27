"""Punto de entrada de la API.

NOTA SOBRE LOS HANDLERS SINCRONOS

Ningun endpoint se declara 'async def'. Es deliberado: todos hacen trabajo
bloqueante -- Firestore, Vertex AI, Open-Meteo -- y FastAPI ejecuta los
handlers 'async def' directamente en el bucle de eventos, de modo que cada
peticion lo bloquea entero mientras espera. Los handlers sincronos, en cambio,
se ejecutan en un pool de hilos y no lo bloquean.

La diferencia se midio: con handlers asincronos, la PWA disparaba varias
peticiones en paralelo al cargar y se serializaban todas detras de la mas
lenta. Una clasificacion de intencion que en las mediciones de S3-06 promediaba
2.9 segundos llego a tardar 19.9 solo por esperar su turno.

Si en el futuro algun endpoint pasa a usar clientes asincronos de verdad, ese
si debe declararse 'async def'.
"""

from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import (
    agent_routes,
    auth_routes,
    metrics_routes,
    orchestrator_routes,
    session_routes,
)

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

app.include_router(auth_routes.router)
app.include_router(session_routes.router)
app.include_router(metrics_routes.router)
app.include_router(agent_routes.router)
app.include_router(orchestrator_routes.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "wellness-platform",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
