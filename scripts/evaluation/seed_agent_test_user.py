"""Siembra el usuario de prueba usado por el golden set de evaluacion del
agente (issues #15 y S3-06). Requiere credenciales de GCP.

Corre este script UNA VEZ antes de evaluar, y de nuevo si se quiere reiniciar
el estado del usuario de prueba a un punto conocido.

IMPORTANTE: re-sembrar antes de cada medicion y antes de la demostracion. Las
sesiones se fechan relativas a la semana en curso, asi que un estado sembrado
hace dos semanas deja al corredor con cero kilometros en la semana actual.

CORRECCION DE REPRODUCIBILIDAD (revision del PR #25): la version original
fechaba las sesiones como hoy-1, hoy-3 y hoy-5 dias. Parece razonable pero no
lo es, porque calcular_carga_semanal() agrupa por semana CALENDARIO -- el rango
[lunes, hoy] -- no por ventana movil de siete dias. Las mismas tres sesiones
caian en semanas distintas segun el dia en que se corriera la evaluacion:

    Dia de ejecucion        Carga "semana actual"
    lunes                   0 km
    martes / miercoles      6 km
    jueves / viernes        14 km   <- la quinta medicion corrio un viernes
    sabado / domingo        19 km

Con 0 km en la semana actual, la premisa de AG-08 ("siento que he corrido
demasiado esta semana") deja de ser cierta y el caso falla sin que nada este
roto. Es el mismo defecto que ya se habia encontrado en el Sprint 1 en
test_calcular_carga_semanal: datos relativos al dia de hoy, comparados contra
una agrupacion por semana calendario.

La correccion ancla las fechas al lunes de cada semana, de modo que la carga
sea 14 km en la semana actual y 5 km en la anterior corra el dia que corra.

REGISTROS COMPLETOS (S3-07): las sesiones se siembran con todos los campos que
escribe el endpoint de la aplicacion -- id, tiempoSeg, ritmoMin, createdAt --
y no solo con los que el agente consulta. Sembrar registros incompletos hacia
que el usuario de prueba se viera roto en la interfaz: el historial mostraba
sesiones sin tiempo ni ritmo. Para que la demostracion sea reproducible, los
datos de prueba tienen que parecerse a los reales.

SEMBRAR SOBRE UNA CUENTA REAL (S3-07)

El usuario por defecto existe en Firestore pero NO tiene cuenta en Firebase
Auth, asi que nadie puede iniciar sesion en la PWA con el. Sirve para la
evaluacion automatizada, que invoca a los agentes directamente, pero no para
una demostracion por la interfaz.

Con --email se resuelve el uid de una cuenta real y se siembran sus datos, de
modo que quien quiera reproducir la demostracion pueda registrarse y luego
poblar su propia cuenta:

    python -m scripts.evaluation.seed_agent_test_user
    python -m scripts.evaluation.seed_agent_test_user --email tu@correo.com

Al sembrar sobre una cuenta real NO se sobrescribe el perfil existente: se
conservan los campos que ya tenga y solo se completan los que los agentes
necesitan y falten (nivel, ciudad, peso). Borrarle el nombre a alguien por
ejecutar un script de siembra seria una sorpresa desagradable.
"""

import argparse
from datetime import date, timedelta

import firebase_admin
from firebase_admin import auth as firebase_auth

from src.agents.wellness_coach.memory import MemoriaConversacional
from src.database.firestore_client import db, init_firebase

USER_ID = "usuario-eval-agente"

PERFIL_POR_DEFECTO = {
    "email": "eval-agente@runcoach.test",
    "nombre": "Usuario de Evaluacion",
    "peso": 68,
    "edad": 30,
    "nivel": "intermedio",
    "ciudad": "Maracaibo",
}

# Campos que los agentes necesitan y que se completan si faltan en una cuenta
# real. El resto del perfil se respeta tal como esta.
CAMPOS_REQUERIDOS_POR_LOS_AGENTES = ("peso", "nivel", "ciudad")

KM_SEMANA_ACTUAL = 14      # 8 + 6, repartidos en dos sesiones
KM_SEMANA_ANTERIOR = 5


def calcular_fechas_sesiones(hoy: date) -> tuple[date, date, date]:
    """Fechas de las tres sesiones sembradas, ancladas a la semana calendario.

    Devuelve (sesion_actual_1, sesion_actual_2, sesion_anterior).

    Las dos primeras caen siempre dentro de [lunes, hoy] y la tercera siempre
    dentro de [lunes_pasado, domingo_pasado], para cualquier dia de la semana
    en que se ejecute el seed.

    El min(lunes + 2, hoy) es lo que sostiene esa garantia: sin el, correr el
    seed un lunes o un martes colocaria la segunda sesion en el futuro, fuera
    del rango [lunes, hoy] que usa calcular_carga_semanal, y la carga semanal
    quedaria incompleta. El efecto secundario es que ejecutado un lunes ambas
    sesiones comparten fecha -- dos entrenamientos el mismo dia, que es
    plausible y no afecta ninguna metrica, porque los documentos de Firestore
    tienen identificadores distintos y la suma sigue siendo 14 km.
    """
    lunes = hoy - timedelta(days=hoy.weekday())
    lunes_pasado = lunes - timedelta(weeks=1)

    return (
        lunes,
        min(lunes + timedelta(days=2), hoy),
        lunes_pasado + timedelta(days=2),
    )


def _resolver_uid(email: str) -> str:
    """uid de Firebase Auth a partir del correo de la cuenta."""
    init_firebase()
    try:
        return firebase_auth.get_user_by_email(email).uid
    except firebase_admin.auth.UserNotFoundError:
        raise SystemExit(
            f"No existe una cuenta de Firebase Auth con el correo '{email}'. "
            "Registrate primero en la aplicacion y vuelve a intentarlo."
        )


def _sembrar_perfil(user_id: str, es_cuenta_real: bool) -> None:
    """Perfil del corredor, sin pisar los datos de una cuenta real."""
    ref = db.collection("users").document(user_id)

    if not es_cuenta_real:
        ref.set({"uid": user_id, **PERFIL_POR_DEFECTO})
        return

    existente = ref.get()
    perfil = existente.to_dict() if existente.exists else {}

    faltantes = {
        campo: PERFIL_POR_DEFECTO[campo]
        for campo in CAMPOS_REQUERIDOS_POR_LOS_AGENTES
        if not perfil.get(campo)
    }
    if faltantes:
        ref.set({"uid": user_id, **faltantes}, merge=True)
        print(f"  Perfil completado con: {', '.join(faltantes)}")
    else:
        print("  Perfil existente conservado sin cambios")


def _sesion(user_id: str, indice: int, fecha: date, km: float, ritmo: float, tipo: str) -> dict:
    """Registro de sesion con la misma forma que escribe POST /sessions."""
    return {
        "id": f"{user_id}-sesion-{indice}",
        "userId": user_id,
        "fecha": fecha.isoformat(),
        "distanciaKm": km,
        "tiempoSeg": round(km * ritmo * 60),
        "ritmoMin": ritmo,
        "fcPromedio": None,
        "notas": f"Sesión de {tipo} sembrada para evaluación",
        "tipo": tipo,
        "createdAt": fecha.isoformat(),
    }


def sembrar(user_id: str = USER_ID, es_cuenta_real: bool = False):
    hoy = date.today()
    fecha_a, fecha_b, fecha_anterior = calcular_fechas_sesiones(hoy)

    print(f"Sembrando datos de prueba para '{user_id}'")

    _sembrar_perfil(user_id, es_cuenta_real)
    # NOTA (hallazgo B, verificacion real #15): AG-03 espera que el agente
    # invoque consultar_clima, lo cual solo es posible si el perfil tiene
    # ciudad. Su ausencia hizo que AG-03 fallara en la primera corrida real
    # -- no por un defecto del agente, sino del usuario de prueba.

    # Dos sesiones en la semana calendario actual (14 km) y una en la anterior
    # (5 km). El salto de 5 a 14 km es deliberado: es la premisa de AG-08, que
    # pregunta si es peligroso seguir asi, y un aumento del 180% esta muy por
    # encima de la regla del 10% de la base de conocimiento. Sin ese contraste
    # el caso pierde sentido.
    sesiones = [
        _sesion(user_id, 0, fecha_a, 8, 5.0, "tempo"),
        _sesion(user_id, 1, fecha_b, 6, 5.8, "rodaje"),
        _sesion(user_id, 2, fecha_anterior, 5, 6.5, "recuperacion"),
    ]
    for s in sesiones:
        db.collection("sessions").document(s["id"]).set(s)

    # El campo 'id' en el cuerpo, ademas del nombre del documento, porque es lo
    # que escribe POST /goals y lo que esperan los clientes que consumen la
    # coleccion.
    objetivo_id = f"{user_id}-meta"
    db.collection("goals").document(objetivo_id).set({
        "id": objetivo_id,
        "userId": user_id,
        "kmMeta": 25,
        "tipo": "semanal",
        "activo": True,
        "createdAt": fecha_anterior.isoformat(),
    })

    # Limpia cualquier memoria conversacional de una corrida anterior, para
    # que AG-01 y AG-06 partan de un estado conocido (sin conversacion previa).
    MemoriaConversacional().limpiar_historial(user_id)

    print("  3 sesiones, 1 objetivo activo, memoria conversacional limpia")
    print(f"  Semana actual  : {fecha_a} (8 km) + {fecha_b} (6 km) = {KM_SEMANA_ACTUAL} km")
    print(f"  Semana anterior: {fecha_anterior} = {KM_SEMANA_ANTERIOR} km")


def main():
    parser = argparse.ArgumentParser(
        description="Siembra datos de prueba para la evaluacion y la demostracion."
    )
    parser.add_argument(
        "--email",
        help=(
            "Correo de una cuenta real de Firebase Auth. Sin este argumento se "
            f"siembra el usuario de evaluacion '{USER_ID}', que no tiene cuenta "
            "y por tanto no permite iniciar sesion en la PWA."
        ),
    )
    args = parser.parse_args()

    if args.email:
        sembrar(_resolver_uid(args.email), es_cuenta_real=True)
    else:
        sembrar()


if __name__ == "__main__":
    main()
