"""Agente Wellness — recomendación de entrenamiento de running.

Soporta dos modos de operación:
    legacy : prompt estático con conocimiento embebido en el código
    rag    : recuperación sobre knowledge base curada + generación fundamentada

El modo dual permite comparación empírica directa entre ambas arquitecturas.

Nota sobre consultas a Firestore: se evita deliberadamente combinar 'where'
con 'order_by' o múltiples 'where' sobre campos distintos, porque Firestore
exige índices compuestos para esos casos. Se filtra por userId y se resuelve
el resto en memoria: con decenas de documentos por usuario el costo es
despreciable y elimina una dependencia de configuración manual.
"""

import json
import time
import uuid
from datetime import datetime, timedelta

import vertexai
from vertexai.generative_models import GenerativeModel

from src.agents.shared.base_agent import BaseAgent
from src.database.firestore_client import db
from src.rag.pipeline.rag_pipeline import ejecutar_rag
from src.utils.prompt_builder import build_wellness_prompt

GCP_PROJECT = "runcoach-ai-496921"
GCP_LOCATION = "us-central1"
GEMINI_MODEL = "gemini-2.5-flash"

MODOS_VALIDOS = ("legacy", "rag")

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
_model = GenerativeModel(GEMINI_MODEL)


class WellnessAgent(BaseAgent):
    """Agente de entrenamiento running con modo legacy y modo RAG."""

    # ── Acceso a datos ───────────────────────────────────────────────────────

    def get_user_profile(self, user_id: str) -> dict:
        doc = db.collection("users").document(user_id).get()
        return doc.to_dict() if doc.exists else {}

    def _sesiones_de_usuario(self, user_id: str) -> list[dict]:
        """Todas las sesiones del usuario, ordenadas por fecha descendente.

        Filtro simple por userId (no requiere índice compuesto) y ordenación
        en memoria.
        """
        from google.cloud.firestore import FieldFilter

        docs = (
            db.collection("sessions")
            .where(filter=FieldFilter("userId", "==", user_id))
            .stream()
        )
        sesiones = [d.to_dict() for d in docs]
        return sorted(sesiones, key=lambda s: str(s.get("fecha", "")), reverse=True)

    def get_last_sessions(self, user_id: str, n: int = 5) -> list:
        return self._sesiones_de_usuario(user_id)[:n]

    def get_weekly_load(self, user_id: str) -> tuple[float, float]:
        """Kilometraje de la semana actual y de la anterior."""
        today = datetime.utcnow().date()
        monday = today - timedelta(days=today.weekday())
        last_monday = monday - timedelta(weeks=1)
        last_sunday = monday - timedelta(days=1)

        sesiones = self._sesiones_de_usuario(user_id)

        def km_entre(inicio, fin) -> float:
            total = 0.0
            for s in sesiones:
                fecha = str(s.get("fecha", ""))[:10]
                if str(inicio) <= fecha <= str(fin):
                    total += s.get("distanciaKm", 0) or 0
            return round(total, 2)

        return km_entre(monday, today), km_entre(last_monday, last_sunday)

    def get_goals(self, user_id: str) -> list:
        """Objetivos activos del usuario. Filtro de 'activo' en memoria."""
        from google.cloud.firestore import FieldFilter

        docs = (
            db.collection("goals")
            .where(filter=FieldFilter("userId", "==", user_id))
            .stream()
        )
        return [g for g in (d.to_dict() for d in docs) if g.get("activo", True)]

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

    def _cargar_estado(self, user_id: str) -> dict | None:
        """Reúne todos los datos del corredor. None si no hay sesiones."""
        sessions = self.get_last_sessions(user_id)
        if not sessions:
            return None

        current_km, previous_km = self.get_weekly_load(user_id)
        perfil = self.get_user_profile(user_id)

        return {
            "sessions": sessions,
            "current_km": current_km,
            "previous_km": previous_km,
            "goals": self.get_goals(user_id),
            "nivel": perfil.get("nivel", "no declarado"),
        }

    def analyze(self, user_id: str, mode: str = "rag", persistir: bool = True) -> dict:
        """Genera una recomendación para el corredor.

        Args:
            user_id: identificador del corredor
            mode: 'rag' (por defecto) o 'legacy'
            persistir: si guarda el resultado en Firestore
        """
        if mode not in MODOS_VALIDOS:
            raise ValueError(f"Modo inválido '{mode}'. Válidos: {MODOS_VALIDOS}")

        estado = self._cargar_estado(user_id)
        if estado is None:
            return {"userId": user_id, "message": "Sin sesiones registradas para analizar"}

        inicio = time.perf_counter()

        if mode == "rag":
            recomendacion = self._analizar_rag(
                estado["nivel"], estado["sessions"],
                estado["current_km"], estado["previous_km"], estado["goals"],
            )
        else:
            recomendacion = self._analizar_legacy(
                estado["sessions"], estado["current_km"],
                estado["previous_km"], estado["goals"],
            )

        latencia_ms = round((time.perf_counter() - inicio) * 1000)

        rec_id = str(uuid.uuid4())
        recomendacion.update({
            "id": rec_id,
            "userId": user_id,
            "modo": mode,
            "latenciaMs": latencia_ms,
            "generadoEn": datetime.utcnow().isoformat(),
            "kmSemanaActual": estado["current_km"],
            "kmSemanaAnterior": estado["previous_km"],
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
        estado = self._cargar_estado(user_id)
        if estado is None:
            return {"userId": user_id, "message": "Sin sesiones registradas para analizar"}

        t0 = time.perf_counter()
        legacy = self._analizar_legacy(
            estado["sessions"], estado["current_km"],
            estado["previous_km"], estado["goals"],
        )
        latencia_legacy = round((time.perf_counter() - t0) * 1000)

        t1 = time.perf_counter()
        rag = self._analizar_rag(
            estado["nivel"], estado["sessions"],
            estado["current_km"], estado["previous_km"], estado["goals"],
        )
        latencia_rag = round((time.perf_counter() - t1) * 1000)

        trazabilidad = rag.pop("_rag", {})
        cambio = (
            round((estado["current_km"] - estado["previous_km"]) / estado["previous_km"] * 100, 1)
            if estado["previous_km"] > 0 else 0.0
        )

        return {
            "userId": user_id,
            "generadoEn": datetime.utcnow().isoformat(),
            "estadoCorredor": {
                "nivel": estado["nivel"],
                "kmSemanaActual": estado["current_km"],
                "kmSemanaAnterior": estado["previous_km"],
                "variacionPct": cambio,
                "objetivosActivos": len(estado["goals"]),
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