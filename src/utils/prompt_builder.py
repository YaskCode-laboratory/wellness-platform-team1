"""Construcción de prompts y utilidades compartidas por los agentes."""

import json
from datetime import date, datetime
from pathlib import Path

from src.utils.fechas import dias_desde, hoy


# ── Carga de plantillas ──────────────────────────────────────────────────────

def load_prompt_template(nombre: str, subcarpeta: str = "agents") -> str:
    """Carga una plantilla desde prompts/<subcarpeta>/<nombre>.txt"""
    path = Path(__file__).resolve().parents[2] / "prompts" / subcarpeta / f"{nombre}.txt"
    return path.read_text(encoding="utf-8")


# ── Fechas ───────────────────────────────────────────────────────────────────

def dias_desde(fecha_str) -> int | None:
    """Días transcurridos desde una fecha ISO hasta hoy. None si no es parseable."""
    if not fecha_str:
        return None
    try:
        fecha = datetime.fromisoformat(str(fecha_str)[:10]).date()
    except ValueError:
        return None
    return dias_desde(fecha)


def enriquecer_sesiones(sessions: list) -> list:
    """Agrega 'diasAtras' a cada sesión.

    Los LLM no razonan bien con fechas absolutas ni conocen la fecha actual.
    Explicitar la antigüedad evita que asuman que toda sesión es reciente.
    """
    enriquecidas = []
    for s in sessions:
        copia = dict(s)
        dias = dias_desde(s.get("fecha"))
        copia["diasAtras"] = dias if dias is not None else "desconocido"
        enriquecidas.append(copia)
    return enriquecidas


# ── Carga ────────────────────────────────────────────────────────────────────

def calcular_cambio(current_km: float, previous_km: float) -> float:
    """Variación porcentual de carga semanal."""
    if previous_km <= 0:
        return 0.0
    return round((current_km - previous_km) / previous_km * 100, 1)


# ── Objetivos ────────────────────────────────────────────────────────────────
# El modelo de datos de la plataforma define objetivos como metas de volumen
# (kmMeta + tipo), no como objetivos de competición con fecha meta.

def meta_semanal(goals: list) -> float | None:
    """Extrae la meta de volumen semanal de los objetivos activos."""
    for objetivo in goals:
        km = objetivo.get("kmMeta")
        if not km:
            continue
        tipo = (objetivo.get("tipo") or "semanal").lower()
        if tipo == "semanal":
            return float(km)
        if tipo == "mensual":
            return float(km) / 4.345      # semanas promedio por mes
    return None


def formatear_objetivos(goals: list) -> str:
    """Representación legible de los objetivos para el prompt."""
    if not goals:
        return "Sin objetivos definidos"

    lineas = []
    for objetivo in goals:
        km = objetivo.get("kmMeta")
        tipo = objetivo.get("tipo", "semanal")
        if km:
            lineas.append(f"- Meta de volumen {tipo}: {km} km")
        else:
            lineas.append(f"- {json.dumps(objetivo, ensure_ascii=False, default=str)}")
    return "\n".join(lineas)


# ── Prompt legacy ────────────────────────────────────────────────────────────

def build_wellness_prompt(sessions: list, current_km: float,
                          previous_km: float, goals: list) -> str:
    """Prompt legacy del agente wellness (sin recuperación)."""
    template = load_prompt_template("wellness_agent")

    return template.format(
        fecha_actual=hoy().isoformat(),
        sessions_text=json.dumps(enriquecer_sesiones(sessions), ensure_ascii=False,
                                 indent=2, default=str),
        current_km=current_km,
        previous_km=previous_km,
        cambio=calcular_cambio(current_km, previous_km),
        goals_text=formatear_objetivos(goals),
    )