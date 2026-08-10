import json
from pathlib import Path


def load_prompt_template(agent_name: str) -> str:
    """Load a prompt template from prompts/agents/<agent_name>.txt"""
    path = Path(__file__).resolve().parents[2] / "prompts" / "agents" / f"{agent_name}.txt"
    return path.read_text(encoding="utf-8")


def build_wellness_prompt(sessions: list, current_km: float, previous_km: float, goals: list) -> str:
    """Build the prompt for the wellness (running) agent."""
    template = load_prompt_template("wellness_agent")
    sessions_text = json.dumps(sessions, ensure_ascii=False, indent=2)
    goals_text = json.dumps(goals, ensure_ascii=False) if goals else "Sin objetivos definidos"
    cambio = round(((current_km - previous_km) / previous_km * 100), 1) if previous_km > 0 else 0

    return template.format(
        sessions_text=sessions_text,
        current_km=current_km,
        previous_km=previous_km,
        cambio=cambio,
        goals_text=goals_text,
    )
