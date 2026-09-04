"""Herramientas que envuelven RepositorioCorredor para exponerlo al modelo
via function calling. La logica de acceso a datos no se duplica: se
reutiliza integramente la implementada en el issue #10."""

from src.data.repositorio_corredor import RepositorioCorredor

_repo = RepositorioCorredor()


def consultar_historial_sesiones(user_id: str, n: int = 5) -> dict:
    """Devuelve las sesiones de entrenamiento mas recientes del corredor."""
    sesiones = _repo.obtener_sesiones_recientes(user_id, n=n)
    if not sesiones:
        return {"sesiones": [], "mensaje": "Sin sesiones registradas."}
    return {"sesiones": sesiones, "total": len(sesiones)}


def consultar_progreso_objetivo(user_id: str) -> dict:
    """Compara la carga semanal actual del corredor contra su meta activa."""
    current_km, previous_km = _repo.calcular_carga_semanal(user_id)
    objetivos = _repo.obtener_objetivos_activos(user_id)

    if not objetivos:
        return {
            "kmSemanaActual": current_km,
            "kmSemanaAnterior": previous_km,
            "objetivo": None,
            "mensaje": "El corredor no tiene objetivos activos definidos.",
        }

    meta = next((o.get("kmMeta") for o in objetivos if o.get("kmMeta")), None)
    progreso_pct = round(current_km / meta * 100, 1) if meta else None

    return {
        "kmSemanaActual": current_km,
        "kmSemanaAnterior": previous_km,
        "metaSemanal": meta,
        "progresoPct": progreso_pct,
    }