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

QUE NO MIDE ESTE SCRIPT

La calidad de las respuestas. La tasa de delegacion dice a quien se pregunto,
no si lo que contesto sirve. Las respuestas completas se guardan en el archivo
de resultados para el analisis cualitativo, que es donde se juzga si la
respuesta es util, si respeta las fronteras y si cita lo que dice citar.

USO

    python -m scripts.evaluation.seed_agent_test_user
    python -u -m scripts.evaluation.evaluate_multiagent
"""

import json
import time
from pathlib import Path

from src.agents.wellness_coach.memory import MemoriaConversacional
from src.orchestration.orchestrator.agent import OrchestratorAgent

RAIZ = Path(__file__).resolve().parents[2]
GOLDEN_SET_PATH = RAIZ / "data" / "evaluation" / "multiagent_golden_set.json"
RESULTADOS_PATH = RAIZ / "data" / "evaluation" / "multiagent_resultados.json"


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


def evaluar_caso(orquestador: OrchestratorAgent, memoria: MemoriaConversacional,
                 user_id: str, caso: dict) -> dict:
    """Ejecuta un caso con memoria limpia y recoge todo lo observable."""
    memoria.limpiar_historial(user_id)

    inicio = time.perf_counter()
    traza = orquestador.procesar(user_id, caso["mensaje"])
    latencia_medida = round((time.perf_counter() - inicio) * 1000)

    delegacion = _evaluar_delegacion(caso["agentes_esperados"], traza["agentes"])

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

        "respuesta": traza["respuesta"],
        "degradado": traza["degradado"],
        "herramientas_invocadas": traza["herramientasInvocadas"],
        "fuentes": traza["fuentes"],

        "pasos": traza["pasos"],
        "traza_id": traza["trazaId"],
        "latencias": traza["latencias"],
        "latencia_medida_ms": latencia_medida,
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

    return {
        "total_casos": total,
        "tasa_delegacion_exacta": round(exactas / total, 3),
        "tasa_intencion_correcta": round(intencion_ok / total, 3),
        "casos_con_sobredelegacion": sobre,
        "casos_con_subdelegacion": sub,
        "casos_con_orden_incorrecto": orden_incorrecto,
        "casos_degradados": degradados,
        "casos_con_colaboracion": colaboraciones,
        "latencia_total_promedio_ms": round(
            sum(r["latencias"]["totalMs"] for r in resultados) / total
        ),
        "latencia_clasificacion_promedio_ms": round(
            sum(r["latencias"]["clasificacionMs"] for r in resultados) / total
        ),
        # Valores distintos de confianza observados en toda la corrida. Si sale
        # uno solo, el modelo no esta calibrando: esta emitiendo un valor por
        # defecto, y el umbral que decide si delegar es una salvaguarda que
        # nunca se activa. Se detecto en S3-02 y se mide aqui.
        "valores_de_confianza_observados": confianzas,
        "por_tipo": por_tipo,
    }


def main() -> None:
    golden = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    user_id = golden["usuario_prueba"]
    casos = golden["casos"]

    orquestador = OrchestratorAgent()
    memoria = MemoriaConversacional()

    resultados = []
    for i, caso in enumerate(casos, start=1):
        print(f"[{i}/{len(casos)}] {caso['id']} ({caso['tipo']}) — {caso['mensaje'][:60]}")
        resultado = evaluar_caso(orquestador, memoria, user_id, caso)
        resultados.append(resultado)

        marca = "OK     " if resultado["delegacion"]["exacta"] else "REVISAR"
        print(
            f"    -> {marca} | intencion={resultado['intencion_obtenida']}"
            f" | agentes={resultado['agentes_invocados']}"
            f" | {resultado['latencias']['totalMs']} ms"
        )
        if resultado["delegacion"]["sobredelegacion"]:
            print(f"       sobredelegacion: {resultado['delegacion']['sobredelegacion']}")
        if resultado["delegacion"]["subdelegacion"]:
            print(f"       subdelegacion  : {resultado['delegacion']['subdelegacion']}")

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
    print(f"  Latencia total promedio        : {metricas['latencia_total_promedio_ms']} ms")
    print(f"  Latencia clasificacion promedio: {metricas['latencia_clasificacion_promedio_ms']} ms")
    print(f"  Confianzas observadas          : {metricas['valores_de_confianza_observados']}")
    print()
    print("  Por tipo:")
    for tipo, datos in metricas["por_tipo"].items():
        print(f"    {tipo:20} {datos['aciertos']}/{datos['total']}")
    print()
    print(f"  Resultados completos: {RESULTADOS_PATH}")


if __name__ == "__main__":
    main()