"""Evaluacion del flujo multiagente (issue S3-06).

Corre el golden set multiagente contra el sistema real -- Vertex AI, Firestore,
ChromaDB y Open-Meteo -- y mide si el orquestador delega donde debe, si la
colaboracion funciona, cuanto cuesta y que se degrada.

DOS LECCIONES DEL SPRINT 2 APLICADAS DESDE EL PRIMER DIA

1. COINCIDENCIA EXACTA, NO SUBCONJUNTO.

   El marco de evaluacion del Sprint 2 consideraba acierto que las herramientas
   esperadas fueran un SUBCONJUNTO de las invocadas. Eso medía recall y no
   precision: invocar de mas no penalizaba. AG-07 paso con cinco herramientas
   donde se esperaban dos, y los casos que esperaban cero herramientas no
   podian fallar nunca, porque el conjunto vacio es subconjunto de cualquier
   cosa. El defecto sobrevivio cinco corridas.

   Aqui la delegacion se evalua por IGUALDAD de conjuntos, y se reportan por
   separado la sobredelegacion y la subdelegacion. Un caso que espera cero
   agentes falla si se delega en alguno.

2. MEMORIA LIMPIA ANTES DE CADA CASO.

   El hallazgo A del Sprint 2 fue que la memoria conversacional se limpiaba
   solo al sembrar y no entre casos, contaminando los resultados. Durante la
   verificacion de S3-04 el problema reaparecio a nivel multiagente: el Coach
   escribio "sigo necesitando esa informacion" refiriendose a una conversacion
   anterior.

   Aqui se limpia antes de cada caso, no solo al inicio de la corrida.

LA CALIDAD SE EVALUA EXPLICITAMENTE, NO SE DEJA IMPLICITA

La primera version media solo la delegacion y guardaba las respuestas para un
analisis cualitativo posterior. El problema de dejarlo asi es que el golden set
declaraba un criterio_aprobacion por caso y ningun resultado decia si ese
criterio se cumplia: la corrida terminaba con "100% de delegacion exacta" y
nadie podia contestar si alguna respuesta era buena.

Y no era una preocupacion teorica. MA-05 exige responder fundamentado en la
base de conocimiento MENCIONANDO su origen. El Coach invoco la herramienta y
respondio correctamente de fondo, pero no cito ningun doc_id, asi que el caso
incumplia su criterio mientras se contaba como acierto. La causa resulto ser
que el prompt del Coach estaba truncado durante esa corrida y las reglas de
citacion eran una de las secciones perdidas.

Ahora cada caso produce un veredicto en dos partes:

1. COMPROBACIONES AUTOMATICAS. El golden set declara, junto al criterio en
   prosa, la parte que una maquina puede verificar: que se citen fuentes o que
   no se cite ninguna, que aparezca un doc_id concreto, que se invoque cierta
   herramienta, que el texto mencione o evite algo. Es un subconjunto del
   criterio, no su sustituto.

2. VEREDICTO MANUAL. Lo que ninguna comprobacion captura -- si la respuesta es
   util, si respeta la frontera, si el reparto de una consulta mixta tiene
   sentido -- se registra a mano en multiagent_calidad_manual.json, con nota y
   fecha. Un caso sin veredicto se reporta como PENDIENTE, no se omite: la
   ausencia de juicio tiene que verse.

QUE SE CUENTA COMO FUENTE CITADA

La union de dos origenes, porque los dos agentes citan distinto. El Nutrition
Agent devuelve sus doc_id en un campo estructurado; el Coach los escribe dentro
de su prosa y su contrato de salida no los expone (limitacion anotada en
_invocar_wellness_coach). Mirar solo la traza daria por no citada toda
respuesta del Coach; mirar solo el texto haria lo mismo con el Nutrition Agent.

USO

    python -m scripts.evaluation.seed_agent_test_user
    python -u -m scripts.evaluation.evaluate_multiagent

    python -m scripts.evaluation.evaluate_multiagent --recalcular

RECALCULAR SIN VOLVER A MEDIR

La segunda forma vuelve a juzgar los resultados ya guardados sin invocar a
ningun agente. No es un atajo para ahorrar llamadas: es lo que mantiene
separada la MEDICION del JUICIO.

El sistema no es determinista, asi que cada corrida produce respuestas
distintas. Si corregir un criterio mal escrito obligara a volver a medir, la
corrida nueva vendria con respuestas nuevas y seria imposible saber si el
cambio de veredicto vino de arreglar el criterio o de que el modelo contesto
otra cosa. Peor: invita a repetir hasta que salga bien.

Recalcular congela las respuestas medidas y aplica sobre ellas el criterio
corregido. La corrida se mide una vez; el juicio se puede revisar las veces
que haga falta.
"""

import argparse
import json
import re
import time
from pathlib import Path

from src.agents.wellness_coach.memory import MemoriaConversacional
from src.orchestration.orchestrator.agent import OrchestratorAgent

RAIZ = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = RAIZ / "data" / "evaluation" / "multiagent_golden_set.json"
RESULTADOS_PATH = RAIZ / "data" / "evaluation" / "multiagent_resultados.json"
CALIDAD_MANUAL_PATH = RAIZ / "data" / "evaluation" / "multiagent_calidad_manual.json"

# Los doc_id de la knowledge base tienen la forma KB-001. Es el unico rastro de
# citacion que deja el Coach, que las escribe en su prosa.
PATRON_DOC_ID = re.compile(r"\bKB-\d{3}\b")


def _evaluar_delegacion(esperados: list[str], invocados: list[str]) -> dict:
    """Compara la delegacion realizada contra la esperada.

    Por igualdad de conjuntos, no por subconjunto. Se devuelven ademas las
    diferencias en ambas direcciones porque no son el mismo problema:
    subdelegar deja una parte de la consulta sin responder, mientras que
    sobredelegar duplica latencia y alarga la respuesta sin aportar. Una
    metrica que los sumara ocultaria cual de los dos esta ocurriendo.
    """
    conjunto_esperado = set(esperados)
    conjunto_invocado = set(invocados)

    return {
        "exacta": conjunto_esperado == conjunto_invocado,
        "sobredelegacion": sorted(conjunto_invocado - conjunto_esperado),
        "subdelegacion": sorted(conjunto_esperado - conjunto_invocado),
        "orden_esperado": list(esperados) == list(invocados),
    }


def fuentes_observadas(traza: dict) -> dict:
    """Doc_id que la respuesta acredita haber usado, por los dos caminos.

    El Nutrition Agent los devuelve estructurados; el Coach los escribe dentro
    de su prosa porque su contrato de salida no los expone. Se reportan por
    separado ademas de la union, para que quede visible cual de los dos
    mecanismos esta funcionando en cada caso.
    """
    en_traza = sorted(set(traza["fuentes"]))
    en_texto = sorted(set(PATRON_DOC_ID.findall(traza["respuesta"] or "")))
    return {
        "en_traza": en_traza,
        "en_texto": en_texto,
        "union": sorted(set(en_traza) | set(en_texto)),
    }


def _evaluar_comprobaciones(comprobaciones: dict, traza: dict, fuentes: dict) -> dict:
    """Verifica la parte del criterio que una maquina puede decidir.

    Devuelve una entrada por comprobacion declarada, con lo esperado y lo
    observado, para que un fallo se pueda leer sin abrir la respuesta entera.
    Solo se evalua lo que el caso declara: un caso sin comprobaciones no
    aprueba por omision, queda sin senal automatica y depende del veredicto
    manual.
    """
    resultados = {}
    texto = (traza["respuesta"] or "").lower()

    if "cita_fuentes" in comprobaciones:
        esperado = comprobaciones["cita_fuentes"]
        observado = bool(fuentes["union"])
        resultados["cita_fuentes"] = {
            "esperado": esperado,
            "observado": observado,
            "cumple": observado == esperado,
            "doc_ids": fuentes["union"],
        }

    if "fuentes_esperadas" in comprobaciones:
        esperadas = set(comprobaciones["fuentes_esperadas"])
        faltantes = sorted(esperadas - set(fuentes["union"]))
        resultados["fuentes_esperadas"] = {
            "esperado": sorted(esperadas),
            "observado": fuentes["union"],
            "cumple": not faltantes,
            "faltantes": faltantes,
        }

    if "herramientas_requeridas" in comprobaciones:
        requeridas = set(comprobaciones["herramientas_requeridas"])
        invocadas = set(traza["herramientasInvocadas"])
        faltantes = sorted(requeridas - invocadas)
        resultados["herramientas_requeridas"] = {
            "esperado": sorted(requeridas),
            "observado": sorted(invocadas),
            "cumple": not faltantes,
            "faltantes": faltantes,
        }

    if "menciona" in comprobaciones:
        ausentes = [f for f in comprobaciones["menciona"] if f.lower() not in texto]
        resultados["menciona"] = {
            "esperado": comprobaciones["menciona"],
            "cumple": not ausentes,
            "ausentes": ausentes,
        }

    if "no_menciona" in comprobaciones:
        presentes = [f for f in comprobaciones["no_menciona"] if f.lower() in texto]
        resultados["no_menciona"] = {
            "esperado": comprobaciones["no_menciona"],
            "cumple": not presentes,
            "presentes": presentes,
        }

    return resultados


def _evaluar_calidad(caso: dict, traza: dict, fuentes: dict, manual: dict) -> dict:
    """Veredicto explicito de calidad para un caso.

    Combina las comprobaciones automaticas con el veredicto manual registrado
    en multiagent_calidad_manual.json. El resultado final es conservador: si
    alguna comprobacion automatica falla, el caso NO cumple aunque alguien lo
    haya marcado a mano como correcto. Un veredicto manual puede reprobar algo
    que las comprobaciones aprobaron, pero no al reves: la senal automatica es
    la que no depende de quien la mire.

    Sin veredicto manual el caso queda 'pendiente', nunca 'cumple'. Una
    evaluacion de calidad a la que le falta juicio humano debe declararlo, no
    disimularlo aprobando por defecto.
    """
    automaticas = _evaluar_comprobaciones(caso.get("comprobaciones", {}), traza, fuentes)
    fallidas = sorted(n for n, r in automaticas.items() if not r["cumple"])

    entrada_manual = manual.get(caso["id"], {})
    veredicto_manual = entrada_manual.get("cumple")

    if fallidas:
        veredicto = "no_cumple"
    elif veredicto_manual is True:
        veredicto = "cumple"
    elif veredicto_manual is False:
        veredicto = "no_cumple"
    else:
        veredicto = "pendiente"

    return {
        "veredicto": veredicto,
        "comprobaciones_automaticas": automaticas,
        "comprobaciones_fallidas": fallidas,
        "veredicto_manual": veredicto_manual,
        "nota_manual": entrada_manual.get("nota"),
        "evaluado_por": entrada_manual.get("evaluado_por"),
        "fecha_manual": entrada_manual.get("fecha"),
    }


def evaluar_caso(orquestador: OrchestratorAgent, memoria: MemoriaConversacional,
                 user_id: str, caso: dict, manual: dict) -> dict:
    """Ejecuta un caso con memoria limpia y recoge todo lo observable."""
    memoria.limpiar_historial(user_id)

    inicio = time.perf_counter()
    traza = orquestador.procesar(user_id, caso["mensaje"])
    latencia_respuesta = round((time.perf_counter() - inicio) * 1000)

    delegacion = _evaluar_delegacion(caso["agentes_esperados"], traza["agentes"])
    fuentes = fuentes_observadas(traza)

    return {
        "id": caso["id"],
        "tipo": caso["tipo"],
        "mensaje": caso["mensaje"],
        "criterio_aprobacion": caso["criterio_aprobacion"],

        "intencion_esperada": caso["intencion_esperada"],
        "intencion_obtenida": traza["intencion"],
        "intencion_coincide": traza["intencion"] == caso["intencion_esperada"],
        "motivo_clasificacion": traza["motivoClasificacion"],
        "confianza": traza["confianza"],

        "agentes_esperados": caso["agentes_esperados"],
        "agentes_invocados": traza["agentes"],
        "delegacion": delegacion,
        "motivo_no_delegacion": traza["motivoNoDelegacion"],
        "colaboracion": traza["colaboracion"],

        "calidad": _evaluar_calidad(caso, traza, fuentes, manual),

        "respuesta": traza["respuesta"],
        "degradado": traza["degradado"],
        "herramientas_invocadas": traza["herramientasInvocadas"],
        "fuentes": fuentes,

        "pasos": traza["pasos"],
        "traza_id": traza["trazaId"],

        # DOS MEDIDAS DE LATENCIA, Y NO MIDEN LO MISMO.
        #
        # 'latencia_respuesta_ms' es la que se publica: el tiempo que tarda una
        # solicitud completa medido desde fuera del orquestador, que es lo que
        # percibe quien llama. Es la cifra que debe citarse como tiempo total
        # de respuesta.
        #
        # 'latencias_internas' es la contabilidad del propio orquestador --
        # clasificacion, agentes, total -- y sirve para repartir ese tiempo
        # entre sus partes, no para reportarlo. Su 'totalMs' es
        # necesariamente algo menor que la medida externa porque no incluye la
        # entrada ni la salida de procesar().
        #
        # Ninguna de las dos incluye la capa HTTP: se invoca al orquestador
        # directamente, sin pasar por FastAPI.
        "latencia_respuesta_ms": latencia_respuesta,
        "latencias_internas": traza["latencias"],
    }


def calcular_metricas(resultados: list[dict]) -> dict:
    total = len(resultados)
    if total == 0:
        return {"total_casos": 0}

    exactas = sum(1 for r in resultados if r["delegacion"]["exacta"])
    sobre = [r["id"] for r in resultados if r["delegacion"]["sobredelegacion"]]
    sub = [r["id"] for r in resultados if r["delegacion"]["subdelegacion"]]
    orden_incorrecto = [
        r["id"]
        for r in resultados
        if r["delegacion"]["exacta"] and not r["delegacion"]["orden_esperado"]
    ]
    intencion_ok = sum(1 for r in resultados if r["intencion_coincide"])
    degradados = [r["id"] for r in resultados if r["degradado"]]
    colaboraciones = [r["id"] for r in resultados if r["colaboracion"]]

    por_tipo: dict[str, dict] = {}
    for r in resultados:
        entrada = por_tipo.setdefault(r["tipo"], {"total": 0, "aciertos": 0})
        entrada["total"] += 1
        if r["delegacion"]["exacta"]:
            entrada["aciertos"] += 1

    confianzas = sorted({r["confianza"] for r in resultados})

    # Calidad: se reportan las tres categorias por separado en vez de una sola
    # tasa. Una tasa que sumara los pendientes a los aprobados o a los
    # reprobados escondería exactamente lo que hay que ver.
    cumplen = [r["id"] for r in resultados if r["calidad"]["veredicto"] == "cumple"]
    no_cumplen = [r["id"] for r in resultados if r["calidad"]["veredicto"] == "no_cumple"]
    pendientes = [r["id"] for r in resultados if r["calidad"]["veredicto"] == "pendiente"]

    fallos_por_comprobacion: dict[str, list[str]] = {}
    for r in resultados:
        for nombre in r["calidad"]["comprobaciones_fallidas"]:
            fallos_por_comprobacion.setdefault(nombre, []).append(r["id"])

    return {
        "total_casos": total,
        "tasa_delegacion_exacta": round(exactas / total, 3),
        "tasa_intencion_correcta": round(intencion_ok / total, 3),
        "casos_con_sobredelegacion": sobre,
        "casos_con_subdelegacion": sub,
        "casos_con_orden_incorrecto": orden_incorrecto,
        "casos_degradados": degradados,
        "casos_con_colaboracion": colaboraciones,

        "calidad": {
            "cumplen": cumplen,
            "no_cumplen": no_cumplen,
            "pendientes_de_veredicto_manual": pendientes,
            "tasa_calidad": round(len(cumplen) / total, 3),
            "fallos_por_comprobacion": fallos_por_comprobacion,
        },

        # La cifra publicable de tiempo de respuesta es la medida externa.
        # 'orquestador' es su desglose interno y no debe citarse como total.
        "latencia_respuesta_promedio_ms": round(
            sum(r["latencia_respuesta_ms"] for r in resultados) / total
        ),
        "latencia_clasificacion_promedio_ms": round(
            sum(r["latencias_internas"]["clasificacionMs"] for r in resultados) / total
        ),
        "latencia_agentes_promedio_ms": round(
            sum(r["latencias_internas"]["agentesMs"] for r in resultados) / total
        ),
        # Valores distintos de confianza observados en toda la corrida. Si sale
        # uno solo, el modelo no esta calibrando: esta emitiendo un valor por
        # defecto, y el umbral que decide si delegar es una salvaguarda que
        # nunca se activa. Se detecto en S3-02 y se mide aqui.
        "valores_de_confianza_observados": confianzas,
        "por_tipo": por_tipo,
    }


def cargar_calidad_manual() -> dict:
    """Veredictos de calidad registrados a mano, si los hay.

    Vive en un archivo aparte a proposito. El golden set describe QUE se
    espera y no debe reescribirse tras cada corrida; los veredictos son
    observaciones sobre una corrida concreta y cambian. Mezclarlos invitaria a
    ajustar el criterio despues de ver el resultado.
    """
    if not CALIDAD_MANUAL_PATH.exists():
        print(f"  Aviso: no existe {CALIDAD_MANUAL_PATH.name}.")
        print("         Todos los casos quedaran como PENDIENTE de veredicto manual.\n")
        return {}
    return json.loads(CALIDAD_MANUAL_PATH.read_text(encoding="utf-8")).get("casos", {})


def main() -> None:
    golden = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    user_id = golden["usuario_prueba"]
    casos = golden["casos"]
    manual = cargar_calidad_manual()

    orquestador = OrchestratorAgent()
    memoria = MemoriaConversacional()

    resultados = []
    for i, caso in enumerate(casos, start=1):
        print(f"[{i}/{len(casos)}] {caso['id']} ({caso['tipo']}) — {caso['mensaje'][:60]}")
        resultado = evaluar_caso(orquestador, memoria, user_id, caso, manual)
        resultados.append(resultado)

        marca = "OK     " if resultado["delegacion"]["exacta"] else "REVISAR"
        veredicto = {
            "cumple": "calidad OK",
            "no_cumple": "CALIDAD NO CUMPLE",
            "pendiente": "calidad pendiente",
        }[resultado["calidad"]["veredicto"]]
        print(
            f"    -> {marca} | intencion={resultado['intencion_obtenida']}"
            f" | agentes={resultado['agentes_invocados']}"
            f" | {resultado['latencia_respuesta_ms']} ms"
            f" | {veredicto}"
        )
        if resultado["delegacion"]["sobredelegacion"]:
            print(f"       sobredelegacion: {resultado['delegacion']['sobredelegacion']}")
        if resultado["delegacion"]["subdelegacion"]:
            print(f"       subdelegacion  : {resultado['delegacion']['subdelegacion']}")
        for nombre in resultado["calidad"]["comprobaciones_fallidas"]:
            detalle = resultado["calidad"]["comprobaciones_automaticas"][nombre]
            print(f"       calidad: falla '{nombre}' -> {detalle}")

    _guardar_y_reportar(resultados)


def recalcular() -> None:
    """Vuelve a juzgar los resultados guardados sin invocar a ningun agente.

    Reconstruye para cada caso la parte de la traza que la evaluacion de
    calidad necesita -- respuesta, fuentes, herramientas -- a partir de lo que
    ya se guardo, y le aplica el golden set y los veredictos manuales
    actuales.

    Lo que NO se recalcula: la delegacion, las latencias y la clasificacion.
    Son observaciones de la corrida, no juicios, y reinterpretarlas seria
    reescribir la medicion.
    """
    guardado = json.loads(RESULTADOS_PATH.read_text(encoding="utf-8"))
    golden = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    manual = cargar_calidad_manual()

    casos_por_id = {c["id"]: c for c in golden["casos"]}

    resultados = []
    for r in guardado["resultados"]:
        caso = casos_por_id.get(r["id"])
        if caso is None:
            print(f"  Aviso: {r['id']} ya no esta en el golden set. Se conserva tal cual.")
            resultados.append(r)
            continue

        traza_parcial = {
            "respuesta": r["respuesta"],
            # 'fuentes' quedo guardado como el desglose de fuentes_observadas.
            # Se vuelve a la forma de traza para no duplicar la logica de
            # extraccion, que es la que define que cuenta como cita.
            "fuentes": r["fuentes"]["en_traza"] if isinstance(r["fuentes"], dict) else r["fuentes"],
            "herramientasInvocadas": r["herramientas_invocadas"],
        }
        fuentes = fuentes_observadas(traza_parcial)

        r = dict(r)
        r["criterio_aprobacion"] = caso["criterio_aprobacion"]
        r["fuentes"] = fuentes
        r["calidad"] = _evaluar_calidad(caso, traza_parcial, fuentes, manual)
        resultados.append(r)

    print("Recalculado sobre las respuestas ya medidas. No se invoco a ningun agente.\n")
    _guardar_y_reportar(resultados)


def _guardar_y_reportar(resultados: list[dict]) -> None:
    metricas = calcular_metricas(resultados)

    RESULTADOS_PATH.write_text(
        json.dumps({"resultados": resultados, "metricas": metricas},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"  Casos evaluados                : {metricas['total_casos']}")
    print(f"  Tasa de delegacion exacta      : {metricas['tasa_delegacion_exacta'] * 100:.1f}%")
    print(f"  Tasa de intencion correcta     : {metricas['tasa_intencion_correcta'] * 100:.1f}%")
    print(f"  Casos con sobredelegacion      : {metricas['casos_con_sobredelegacion'] or 'ninguno'}")
    print(f"  Casos con subdelegacion        : {metricas['casos_con_subdelegacion'] or 'ninguno'}")
    print(f"  Casos con orden incorrecto     : {metricas['casos_con_orden_incorrecto'] or 'ninguno'}")
    print(f"  Casos degradados               : {metricas['casos_degradados'] or 'ninguno'}")
    print(f"  Casos con colaboracion         : {metricas['casos_con_colaboracion'] or 'ninguno'}")
    print()
    calidad = metricas["calidad"]
    print(f"  Calidad - cumplen              : {len(calidad['cumplen'])}/{metricas['total_casos']}")
    print(f"  Calidad - no cumplen           : {calidad['no_cumplen'] or 'ninguno'}")
    print(f"  Calidad - pendientes de juicio : {calidad['pendientes_de_veredicto_manual'] or 'ninguno'}")
    if calidad["fallos_por_comprobacion"]:
        for nombre, ids in calidad["fallos_por_comprobacion"].items():
            print(f"      falla '{nombre}': {ids}")
    print()
    print(f"  Tiempo de respuesta promedio   : {metricas['latencia_respuesta_promedio_ms']} ms")
    print(f"      del cual clasificacion     : {metricas['latencia_clasificacion_promedio_ms']} ms")
    print(f"      del cual agentes           : {metricas['latencia_agentes_promedio_ms']} ms")
    print(f"  Confianzas observadas          : {metricas['valores_de_confianza_observados']}")
    print()
    print("  Por tipo:")
    for tipo, datos in metricas["por_tipo"].items():
        print(f"    {tipo:20} {datos['aciertos']}/{datos['total']}")
    print()
    print(f"  Resultados completos: {RESULTADOS_PATH}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--recalcular",
        action="store_true",
        help=(
            "Vuelve a juzgar la calidad de los resultados ya guardados sin "
            "invocar a ningun agente. Sirve para corregir un criterio mal "
            "escrito sin cambiar las respuestas medidas."
        ),
    )
    argumentos = parser.parse_args()

    recalcular() if argumentos.recalcular else main()