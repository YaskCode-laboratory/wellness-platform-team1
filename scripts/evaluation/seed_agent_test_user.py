"""Siembra el usuario de prueba usado por el golden set de evaluacion del
agente (issue #15). Requiere credenciales de GCP.

Corre este script UNA VEZ antes de evaluar, y de nuevo si se quiere
reiniciar el estado del usuario de prueba a un punto conocido (por ejemplo,
si la memoria conversacional acumulada en corridas anteriores contamina
los resultados de AG-06).

CORRECCION DE REPRODUCIBILIDAD (revision del PR #25): la version original
fechaba las sesiones como hoy-1, hoy-3 y hoy-5 dias. Eso parece razonable
pero no lo es, porque calcular_carga_semanal() agrupa por semana
CALENDARIO -- el rango [lunes, hoy] -- no por ventana movil de siete dias.
Las mismas tres sesiones caian en semanas distintas segun el dia en que se
corriera la evaluacion:

    Dia de ejecucion        Carga "semana actual"
    lunes                   0 km
    martes / miercoles      6 km
    jueves / viernes        14 km   <- la quinta medicion corrio un viernes
    sabado / domingo        19 km

Con 0 km en la semana actual, la premisa de AG-08 ("siento que he corrido
demasiado esta semana") deja de ser cierta y el caso falla sin que nada
este roto. Es decir: el resultado de la evaluacion dependia del dia de la
semana, que es exactamente lo contrario de lo que la seccion 1 de
docs/evaluation/agent-evaluation.md prometia.

Es el mismo defecto que ya se habia encontrado en el Sprint 1 en
test_calcular_carga_semanal, en otro lugar del sistema: datos relativos al
dia de hoy, comparados contra una agrupacion por semana calendario.

La correccion ancla las fechas al lunes de cada semana en vez de a hoy,
de modo que la carga sea 14 km en la semana actual y 5 km en la anterior
corra el dia que corra.
"""

from datetime import date, timedelta

from src.agents.wellness_coach.memory import MemoriaConversacional
from src.database.firestore_client import db

USER_ID = "usuario-eval-agente"

KM_SEMANA_ACTUAL = 14      # 8 + 6, repartidos en dos sesiones
KM_SEMANA_ANTERIOR = 5


def calcular_fechas_sesiones(hoy: date) -> tuple[date, date, date]:
    """Fechas de las tres sesiones sembradas, ancladas a la semana calendario.

    Devuelve (sesion_actual_1, sesion_actual_2, sesion_anterior).

    Las dos primeras caen siempre dentro de [lunes, hoy] y la tercera
    siempre dentro de [lunes_pasado, domingo_pasado], para cualquier dia de
    la semana en que se ejecute el seed.

    El min(lunes + 2, hoy) es lo que sostiene esa garantia: sin el, correr
    el seed un lunes o un martes colocaria la segunda sesion en el futuro,
    fuera del rango [lunes, hoy] que usa calcular_carga_semanal, y la carga
    semanal quedaria incompleta. El efecto secundario es que ejecutado un
    lunes ambas sesiones comparten fecha -- dos entrenamientos el mismo dia,
    que es plausible y no afecta ninguna metrica, porque los documentos de
    Firestore tienen identificadores distintos y la suma sigue siendo 14 km.
    """
    lunes = hoy - timedelta(days=hoy.weekday())
    lunes_pasado = lunes - timedelta(weeks=1)

    return (
        lunes,
        min(lunes + timedelta(days=2), hoy),
        lunes_pasado + timedelta(days=2),
    )


def sembrar():
    hoy = date.today()
    fecha_a, fecha_b, fecha_anterior = calcular_fechas_sesiones(hoy)

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

    # Dos sesiones en la semana calendario actual (14 km) y una en la
    # anterior (5 km). El salto de 5 a 14 km es deliberado: es la premisa
    # de AG-08, que pregunta si es peligroso seguir asi, y un aumento del
    # 180% esta muy por encima de la regla del 10% de la base de
    # conocimiento. Sin ese contraste el caso pierde sentido.
    sesiones = [
        {"fecha": fecha_a.isoformat(), "distanciaKm": 8, "tipo": "tempo"},
        {"fecha": fecha_b.isoformat(), "distanciaKm": 6, "tipo": "rodaje"},
        {"fecha": fecha_anterior.isoformat(), "distanciaKm": 5, "tipo": "recuperacion"},
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
    print(f"  Semana actual  : {fecha_a} (8 km) + {fecha_b} (6 km) = {KM_SEMANA_ACTUAL} km")
    print(f"  Semana anterior: {fecha_anterior} = {KM_SEMANA_ANTERIOR} km")


if __name__ == "__main__":
    sembrar()