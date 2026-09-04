"""Agente Wellness — recomendación de entrenamiento de running.

Soporta dos modos de operación:
    legacy : prompt estático con conocimiento embebido en el código
    rag    : recuperación sobre knowledge base curada + generación fundamentada

El modo dual permite comparación empírica directa entre ambas arquitecturas.

El acceso a los datos del corredor (perfil, sesiones, carga semanal,
objetivos) no vive en esta clase: se delega a RepositorioCorredor
(src/data/repositorio_corredor.py), compartido con el Wellness Coach
Agent 2.0. Este agente se limita a construir prompts, generar
recomendaciones y orquestar/persistir el resultado.
"""

import json
import time
import uuid
from datetime import datetime

import vertexai
from vertexai.generative_models import GenerativeModel

from src.agents.shared.base_agent import BaseAgent
from src.data.repositorio_corredor import RepositorioCorredor
from src.database.firestore_client import db
from src.rag.pipeline.rag_pipeline import ejecutar_rag
from src.utils.config import GCP_LOCATION, GCP_PROJECT, GEMINI_MODEL
from src.utils.prompt_builder import build_wellness_prompt

MODOS_VALIDOS = ("legacy", "rag")

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
_model = GenerativeModel(GEMINI_MODEL)


class WellnessAgent(BaseAgent):
    """Agente de entrenamiento running con modo legacy y modo RAG."""

    def __init__(self) -> None:
        self.repositorio = RepositorioCorredor()

    # ── BaseAgent ────────────────────────────────────────────────────────────

    def build_prompt(self, sessions, current_km, previous_km, goals) -> str:
        """Prompt legacy: conocimiento embebido, sin recuperación."""
        return build_wellness_prompt(sessions, current_km, previous_km, goals)

    # ── Modo legacy ──────────────────────────────────────────────────────────

    def _analizar_legacy(self, sessions, current_km, previous_km, goals) -> dict:
        """Flujo original: prompt estático, sin conocimiento externo."""
        prompt = self.build_prompt(sessions, current_km, previous_km, goals)
        respuesta = _model.generate_content(prompt)

        bruto = respuesta.text.strip()
        if bruto.startswith("```"):
            bruto = bruto.split("```")[1]
            if bruto.startswith("json"):
                bruto = bruto[4:]

        return json.loads(bruto)

    # ── Modo RAG ─────────────────────────────────────────────────────────────

    def _analizar_rag(self, nivel, sessions, current_km, previous_km, goals) -> dict:
        """Flujo RAG: recuperación sobre knowledge base + generación fundamentada."""
        return ejecutar_rag(
            nivel=nivel,
            sessions=sessions,
            current_km=current_km,
            previous_km=previous_km,
            goals=goals,
        )

    # ── Orquestación ─────────────────────────────────────────────────────────

    def analyze(self, user_id: str, mode: str = "rag", persistir: bool = True) -> dict:
        """Genera una recomendación para el corredor.

        Args:
            user_id: identificador del corredor
            mode: 'rag' (por defecto) o 'legacy'
            persistir: si guarda el resultado en Firestore
        """
        if mode not in MODOS_VALIDOS:
            raise ValueError(f"Modo inválido '{mode}'. Válidos: {MODOS_VALIDOS}")

        estado = self.repositorio.cargar_estado_corredor(user_id)
        if estado is None:
            return {"userId": user_id, "message": "Sin sesiones registradas para analizar"}

        inicio = time.perf_counter()

        if mode == "rag":
            recomendacion = self._analizar_rag(
                estado.nivel, estado.sessions,
                estado.current_km, estado.previous_km, estado.goals,
            )
        else:
            recomendacion = self._analizar_legacy(
                estado.sessions, estado.current_km,
                estado.previous_km, estado.goals,
            )

        latencia_ms = round((time.perf_counter() - inicio) * 1000)

        rec_id = str(uuid.uuid4())
        recomendacion.update({
            "id": rec_id,
            "userId": user_id,
            "modo": mode,
            "latenciaMs": latencia_ms,
            "generadoEn": datetime.utcnow().isoformat(),
            "kmSemanaActual": estado.current_km,
            "kmSemanaAnterior": estado.previous_km,
        })

        if persistir:
            # La metadata de trazabilidad RAG no se persiste: es voluminosa
            # y solo tiene valor para inspección en vivo.
            a_guardar = {k: v for k, v in recomendacion.items() if k != "_rag"}
            db.collection("recommendations").document(rec_id).set(a_guardar)

        return recomendacion

    def comparar(self, user_id: str) -> dict:
        """Ejecuta ambos modos sobre el mismo estado y devuelve la comparativa.

        No persiste: es una operación de demostración y evaluación.
        """
        estado = self.repositorio.cargar_estado_corredor(user_id)
        if estado is None:
            return {"userId": user_id, "message": "Sin sesiones registradas para analizar"}

        t0 = time.perf_counter()
        legacy = self._analizar_legacy(
            estado.sessions, estado.current_km,
            estado.previous_km, estado.goals,
        )
        latencia_legacy = round((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        rag = self._analizar_rag(
            estado.nivel, estado.sessions,
            estado.current_km, estado.previous_km, estado.goals,
        )
        latencia_rag = round((time.perf_counter() - t1) * 1000)

        trazabilidad = rag.pop("_rag", {})
        cambio = (
            round((estado.current_km - estado.previous_km) / estado.previous_km * 100, 1)
            if estado.previous_km > 0 else 0.0
        )

        return {
            "userId": user_id,
            "generadoEn": datetime.utcnow().isoformat(),
            "estadoCorredor": {
                "nivel": estado.nivel,
                "kmSemanaActual": estado.current_km,
                "kmSemanaAnterior": estado.previous_km,
                "variacionPct": cambio,
                "objetivosActivos": len(estado.goals),
            },
            "legacy": {
                "recomendacion": legacy,
                "latenciaMs": latencia_legacy,
                "fuentes": [],
                "trazable": False,
            },
            "rag": {
                "recomendacion": rag,
                "latenciaMs": latencia_rag,
                "fuentes": rag.get("fuentes", []),
                "trazable": True,
                "chunksRecuperados": trazabilidad.get("chunks_recuperados", []),
                "consultaRecuperacion": trazabilidad.get("consulta_recuperacion", ""),
            },
            "delta": {
                "latenciaMs": latencia_rag - latencia_legacy,
                "documentosConsultados": len(set(rag.get("fuentes", []))),
            },
        }