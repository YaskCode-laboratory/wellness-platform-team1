"""Siembra el usuario de prueba usado por el golden set de evaluacion del
agente (issue #15). Requiere credenciales de GCP.

Corre este script UNA VEZ antes de evaluar, y de nuevo si se quiere
reiniciar el estado del usuario de prueba a un punto conocido (por ejemplo,
si la memoria conversacional acumulada en corridas anteriores contamina
los resultados de AG-06).
"""

from datetime import date, timedelta

from src.agents.wellness_coach.memory import MemoriaConversacional
from src.database.firestore_client import db

USER_ID = "usuario-eval-agente"


def sembrar():
    hoy = date.today()

    db.collection("users").document(USER_ID).set({
        "uid": USER_ID,
        "email": "eval-agente@runcoach.test",
        "nombre": "Usuario de Evaluacion",
        "peso": 68,
        "edad": 30,
        "nivel": "intermedio",
        "ciudad": "Maracaibo",
    })
    # NOTA (hallazgo B, verificacion real #15): AG-03 espera que el agente
    # invoque consultar_clima, lo cual solo es posible si el perfil tiene
    # ciudad. Este campo ya estaba aqui, pero se documenta explicitamente
    # porque su ausencia hizo que AG-03 fallara en la primera corrida real
    # -- no por un defecto del agente, sino del usuario de prueba.

    # Tres sesiones en la semana actual, para que consultar_progreso_objetivo
    # y consultar_historial_sesiones tengan datos reales que devolver.
    sesiones = [
        {"fecha": (hoy - timedelta(days=1)).isoformat(), "distanciaKm": 6, "tipo": "rodaje"},
        {"fecha": (hoy - timedelta(days=3)).isoformat(), "distanciaKm": 8, "tipo": "tempo"},
        {"fecha": (hoy - timedelta(days=5)).isoformat(), "distanciaKm": 5, "tipo": "recuperacion"},
    ]
    for i, s in enumerate(sesiones):
        db.collection("sessions").document(f"{USER_ID}-sesion-{i}").set({
            "userId": USER_ID,
            **s,
        })

    db.collection("goals").document(f"{USER_ID}-meta").set({
        "userId": USER_ID,
        "kmMeta": 25,
        "tipo": "semanal",
        "activo": True,
    })

    # Limpia cualquier memoria conversacional de una corrida anterior, para
    # que AG-01 y AG-06 partan de un estado conocido (sin conversacion previa).
    memoria = MemoriaConversacional()
    memoria.limpiar_historial(USER_ID)

    print(f"Usuario de prueba '{USER_ID}' sembrado: perfil, 3 sesiones, 1 objetivo activo, memoria limpia.")


if __name__ == "__main__":
    sembrar()