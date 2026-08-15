"""Pipeline RAG completo: recuperación → construcción de contexto → generación."""

import json
from datetime import date
from pathlib import Path

from src.rag.generation.generator import generar
from src.rag.retriever.retriever import recuperar
from src.utils.prompt_builder import (
    calcular_cambio,
    enriquecer_sesiones,
    formatear_objetivos,
    meta_semanal,
)

TOP_K = 5
PROMPT_PATH = Path(__file__).resolve().parents[3] / "prompts" / "rag" / "wellness_rag.txt"

# Umbral de inactividad a partir del cual se considera retorno tras interrupción
DIAS_INACTIVIDAD = 21


def construir_consulta(nivel: str, current_km: float, previous_km: float,
                       cambio: float, goals: list, sessions: list) -> str:
    """Sintetiza una consulta de recuperación a partir del estado del corredor.

    El agente no recibe preguntas, recibe datos. Esta función traduce ese
    estado a lenguaje natural para poder recuperar semánticamente.

    La calidad de la recuperación está limitada por la calidad de esta
    consulta: si describe mal la situación, se recupera conocimiento
    correcto pero irrelevante.
    """
    partes = [
        f"corredor de nivel {nivel}",
        f"volumen semanal actual {current_km} km",
        f"semana anterior {previous_km} km",
        f"variación de carga {cambio}%",
    ]

    # Inactividad reciente: cambia por completo el conocimiento relevante
    dias_ultima = min(
        (s.get("diasAtras") for s in sessions if isinstance(s.get("diasAtras"), int)),
        default=None,
    )

    if dias_ultima is not None and dias_ultima > DIAS_INACTIVIDAD:
        partes.append(
            "retorno tras interrupción prolongada, pérdida de carga crónica, "
            "reanudación gradual"
        )
    elif current_km == 0 and previous_km == 0:
        partes.append("sin actividad reciente, construcción de base aeróbica desde cero")

    # Progresión de carga
    if cambio > 10:
        partes.append("progresión de carga, ACWR y riesgo de lesión por sobreuso")
    elif cambio < -20:
        partes.append("reducción de carga y recuperación")

    # Objetivo de volumen semanal
    meta = meta_semanal(goals)
    if meta:
        partes.append(f"meta de volumen semanal {meta:.0f} km")
        if current_km > meta:
            partes.append("volumen por encima de la meta, gestión de carga")
        elif current_km < meta * 0.5:
            partes.append(
                "volumen muy por debajo de la meta, progresión segura del volumen semanal"
            )

    # El nivel principiante activa factores de riesgo documentados
    if nivel and nivel.lower() == "principiante":
        partes.append(
            "corredor sin experiencia previa, factores de riesgo de lesión en novatos"
        )

    return ", ".join(partes)


def construir_contexto(chunks: list[dict]) -> str:
    """Formatea los chunks recuperados para insertarlos en el prompt."""
    bloques = []
    for n, chunk in enumerate(chunks, 1):
        meta = chunk["metadata"]
        bloques.append(
            f"--- FRAGMENTO {n} "
            f"[{meta['doc_id']}] "
            f"(evidencia: {meta['nivel_evidencia']}, "
            f"similitud: {chunk['similitud']:.3f}) ---\n"
            f"{chunk['texto']}"
        )
    return "\n\n".join(bloques)


def validar_fuentes(fuentes_citadas: list, chunks: list[dict]) -> tuple[list, list]:
    """Separa las fuentes citadas en válidas e inventadas.

    Un LLM puede citar documentos que nunca recibió. En un sistema cuya
    ventaja es la trazabilidad, una cita inventada anula el beneficio.
    La validación debe ser programática: el prompt reduce la frecuencia
    del problema pero no lo elimina.

    Returns:
        (fuentes_validas, fuentes_inventadas)
    """
    disponibles = {c["metadata"]["doc_id"] for c in chunks}
    citadas = [str(f).strip() for f in (fuentes_citadas or [])]

    validas = [f for f in citadas if f in disponibles]
    inventadas = [f for f in citadas if f not in disponibles]

    return validas, inventadas


def ejecutar_rag(
    nivel: str,
    sessions: list,
    current_km: float,
    previous_km: float,
    goals: list,
    k: int = TOP_K,
) -> dict:
    """Ejecuta el pipeline RAG completo."""
    cambio = calcular_cambio(current_km, previous_km)
    sesiones_enriquecidas = enriquecer_sesiones(sessions)

    # 1. Recuperación
    consulta = construir_consulta(nivel, current_km, previous_km, cambio,
                                  goals, sesiones_enriquecidas)
    chunks = recuperar(consulta, k=k)

    # 2. Construcción del prompt con contexto
    plantilla = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = plantilla.format(
        fecha_actual=date.today().isoformat(),
        contexto=construir_contexto(chunks),
        nivel=nivel or "no declarado",
        current_km=current_km,
        previous_km=previous_km,
        cambio=cambio,
        goals_text=formatear_objetivos(goals),
        sessions_text=json.dumps(sesiones_enriquecidas, ensure_ascii=False,
                                 indent=2, default=str),
    )

    # 3. Generación
    recomendacion = generar(prompt)

    # 4. Validación de citas: solo sobreviven las fuentes realmente recuperadas
    validas, inventadas = validar_fuentes(recomendacion.get("fuentes"), chunks)
    recomendacion["fuentes"] = validas

    # 5. Trazabilidad
    recomendacion["_rag"] = {
        "consulta_recuperacion": consulta,
        "chunks_recuperados": [
            {
                "doc_id": c["metadata"]["doc_id"],
                "titulo": c["metadata"]["titulo"],
                "seccion": c["metadata"]["seccion"],
                "similitud": round(c["similitud"], 4),
            }
            for c in chunks
        ],
        "fuentes_inventadas": inventadas,
        "precision_citas": (
            round(len(validas) / (len(validas) + len(inventadas)), 3)
            if (validas or inventadas) else None
        ),
    }

    return recomendacion


if __name__ == "__main__":
    # Caso de prueba con el esquema real: meta de volumen semanal,
    # principiante con incremento del 46% respecto a la semana anterior
    resultado = ejecutar_rag(
        nivel="principiante",
        sessions=[
            {"fecha": "2026-08-10", "distanciaKm": 6, "tipo": "rodaje"},
            {"fecha": "2026-08-08", "distanciaKm": 5, "tipo": "rodaje"},
            {"fecha": "2026-08-06", "distanciaKm": 8, "tipo": "tirada_larga"},
        ],
        current_km=19,
        previous_km=13,
        goals=[{"kmMeta": 30, "tipo": "semanal", "activo": True}],
    )

    print("=" * 78)
    print("RECOMENDACIÓN GENERADA CON RAG")
    print("=" * 78)
    rag_meta = resultado.pop("_rag")
    print(json.dumps(resultado, ensure_ascii=False, indent=2))

    print("\n" + "=" * 78)
    print("TRAZABILIDAD")
    print("=" * 78)
    print(f"Consulta de recuperación:\n  {rag_meta['consulta_recuperacion']}\n")
    for c in rag_meta["chunks_recuperados"]:
        print(f"  [{c['similitud']:.4f}] {c['doc_id']} › {c['seccion']}")

    print(f"\nPrecisión de citas : {rag_meta['precision_citas']}")
    if rag_meta["fuentes_inventadas"]:
        print(f"Fuentes inventadas : {rag_meta['fuentes_inventadas']}  ← descartadas")