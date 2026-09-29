"""Endpoints de metricas de entrenamiento.

Migrados desde el microservicio 'metrics' de RunCoach AI. La logica vive en
src/services/metrics_service.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.seguridad import exigir_propiedad
from src.services import metrics_service

router = APIRouter(
    prefix="/metrics", tags=["metrics"], dependencies=[Depends(exigir_propiedad)]
)


def _ejecutar(operacion):
    try:
        return operacion()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{userId}/weekly")
def weekly_metrics(
    userId: str,
    offset: int = Query(0, ge=0, description="0 es la semana actual, 1 la anterior"),
):
    return _ejecutar(lambda: metrics_service.metricas_semanales(userId, offset))


@router.get("/{userId}/summary")
def summary(
    userId: str,
    semanas: int = Query(4, ge=1, le=52),
):
    return _ejecutar(lambda: metrics_service.resumen_periodo(userId, semanas))


@router.get("/{userId}/weekly-chart")
def weekly_chart(
    userId: str,
    semanas: int = Query(8, ge=1, le=52),
):
    return _ejecutar(lambda: metrics_service.grafico_semanal(userId, semanas))


@router.get("/{userId}/goal-progress")
def goal_progress(userId: str):
    return _ejecutar(lambda: metrics_service.progreso_objetivos(userId))
