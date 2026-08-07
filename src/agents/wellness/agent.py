import json
import uuid
from datetime import datetime, timedelta

import vertexai
from vertexai.generative_models import GenerativeModel

from src.agents.shared.base_agent import BaseAgent
from src.database.firestore_client import db
from src.utils.prompt_builder import build_wellness_prompt

GCP_PROJECT = "runcoach-ai-496921"
GCP_LOCATION = "us-central1"
GEMINI_MODEL = "gemini-2.5-flash"

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
_model = GenerativeModel(GEMINI_MODEL)


class WellnessAgent(BaseAgent):
    """Running / fitness wellness agent powered by Gemini via Vertex AI."""

    # ── Data helpers ─────────────────────────────────────────────────────────

    def get_last_sessions(self, user_id: str, n: int = 5) -> list:
        from google.cloud.firestore import FieldFilter, Query

        docs = (
            db.collection("sessions")
            .where(filter=FieldFilter("userId", "==", user_id))
            .order_by("fecha", direction=Query.DESCENDING)
            .limit(n)
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    def get_weekly_load(self, user_id: str) -> tuple[float, float]:
        from google.cloud.firestore import FieldFilter

        today = datetime.utcnow().date()
        monday = today - timedelta(days=today.weekday())
        last_monday = monday - timedelta(weeks=1)

        def km_range(start, end) -> float:
            docs = (
                db.collection("sessions")
                .where(filter=FieldFilter("userId", "==", user_id))
                .where(filter=FieldFilter("fecha", ">=", str(start)))
                .where(filter=FieldFilter("fecha", "<=", str(end)))
                .stream()
            )
            return sum(d.to_dict().get("distanciaKm", 0) for d in docs)

        current = km_range(monday, today)
        previous = km_range(last_monday, monday - timedelta(days=1))
        return current, previous

    def get_goals(self, user_id: str) -> list:
        from google.cloud.firestore import FieldFilter

        docs = (
            db.collection("goals")
            .where(filter=FieldFilter("userId", "==", user_id))
            .where(filter=FieldFilter("activo", "==", True))
            .stream()
        )
        return [doc.to_dict() for doc in docs]

    # ── BaseAgent interface ───────────────────────────────────────────────────

    def build_prompt(self, sessions, current_km, previous_km, goals) -> str:
        return build_wellness_prompt(sessions, current_km, previous_km, goals)

    def analyze(self, user_id: str) -> dict:
        sessions = self.get_last_sessions(user_id)
        if not sessions:
            return {"userId": user_id, "message": "Sin sesiones registradas para analizar"}

        current_km, previous_km = self.get_weekly_load(user_id)
        goals = self.get_goals(user_id)
        prompt = self.build_prompt(sessions, current_km, previous_km, goals)

        response = _model.generate_content(prompt)
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]

        recommendation = json.loads(raw)
        rec_id = str(uuid.uuid4())
        recommendation.update(
            {
                "id": rec_id,
                "userId": user_id,
                "generadoEn": datetime.utcnow().isoformat(),
                "kmSemanaActual": current_km,
                "kmSemanaAnterior": previous_km,
            }
        )

        db.collection("recommendations").document(rec_id).set(recommendation)
        return recommendation
