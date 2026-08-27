"""Configuración centralizada de la plataforma.

Estas constantes estaban antes declaradas por separado en agent.py,
embedder.py, generator.py y firestore_client.py. Centralizarlas aquí
evita que cambiar de proyecto de GCP implique editar cuatro archivos,
y asegura que el valor real y activo sea siempre el que está en el
entorno (variables de entorno o archivo .env), nunca un literal
enterrado dentro de código de negocio.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga variables desde el archivo .env en la raíz del repo, si existe.
# En un entorno gestionado (por ejemplo Cloud Run) las variables ya
# vienen inyectadas por la plataforma y esta llamada no tiene efecto,
# porque load_dotenv() no sobreescribe variables ya presentes en el
# entorno del proceso.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

GCP_PROJECT = os.getenv("GCP_PROJECT", "runcoach-ai-496921")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")


if __name__ == "__main__":
    print("Configuración activa:")
    print(f"  GCP_PROJECT     = {GCP_PROJECT}")
    print(f"  GCP_LOCATION    = {GCP_LOCATION}")
    print(f"  GEMINI_MODEL    = {GEMINI_MODEL}")
    print(f"  EMBEDDING_MODEL = {EMBEDDING_MODEL}")