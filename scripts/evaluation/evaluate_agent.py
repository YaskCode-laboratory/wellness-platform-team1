"""Evalua el comportamiento del Wellness Coach Agent 2.0 contra el golden
set (issue #15). Requiere credenciales de GCP (Vertex AI + Firestore) y que
el usuario de prueba ya este sembrado (ver seed_agent_test_user.py).

Uso:
    python -m scripts.evaluation.evaluate_agent

Produce:
    data/evaluation/agent_resultados.json  -- resultados crudos por caso
    Resumen impreso en consola con la tasa de acierto de herramientas
"""

import json
import time
from pathlib import Path

from src.agents.wellness_coach.agent import WellnessCoachAgent

GOLDEN_SET_PATH = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "agent_golden_set.json"
RESULTADOS_PATH = Path(__file__).resolve().parents[2] / "data" / "evaluation" / "agent_resultados.json"


def calcular_metricas(resultados: list[dict]) -> dict:
    """Calcula metricas agregadas a partir de los resultados por caso.

    Separada del resto del script para poder probarla sin ejecutar el
    agente real: recibe una lista de resultados ya calculados y solo hace
    aritmetica sobre ellos.
    """
    total = len(resultados)
    if total == 0:
        return {"total_casos": 0}

    casos_con_herramienta_correcta = sum(1 for r in resultados if r["coincidencia_herramientas"])
    casos_con_limite_alcanzado = sum(1 for r in resultados if r["limite_alcanzado"])
    casos_con_reintento_utilizado = sum(1 for r in resultados if r.get("reintento_utilizado", False))
    casos_con_reintento_fallido = sum(1 for r in resultados if r.get("reintento_fallido", False))
    latencia_promedio_ms = round(sum(r["latencia_ms"] for r in resultados) / total)

    por_tipo: dict[str, dict] = {}
    for r in resultados:
        tipo = r["tipo"]
        por_tipo.setdefault(tipo, {"total": 0, "aciertos": 0})
        por_tipo[tipo]["total"] += 1
        if r["coincidencia_herramientas"]:
            por_tipo[tipo]["aciertos"] += 1

    return {
        "total_casos": total,
        "tasa_acierto_herramientas": round(casos_con_herramienta_correcta / total, 3),
        "casos_con_limite_alcanzado": casos_con_limite_alcanzado,
        "casos_con_reintento_utilizado": casos_con_reintento_utilizado,
        "casos_con_reintento_fallido": casos_con_reintento_fallido,
        "latencia_promedio_ms": latencia_promedio_ms,
        "por_tipo": por_tipo,
    }


def _coincide_herramientas(esperadas: list[str], invocadas: list[dict]) -> bool:
    """True si todas las herramientas esperadas fueron invocadas (subconjunto),
    sin exigir que el orden o la cantidad exacta coincida -- Gemini puede
    invocar una herramienta mas de una vez o en distinto orden y seguir
    siendo un comportamiento correcto."""
    nombres_invocados = {h["nombre"] for h in invocadas}
    return set(esperadas).issubset(nombres_invocados)


def evaluar_caso(agente: WellnessCoachAgent, user_id: str, caso: dict) -> dict:
    herramientas_invocadas_total = []
    respuesta_final = ""
    limite_alcanzado = False
    reintento_utilizado = False
    reintento_fallido = False

    inicio = time.perf_counter()
    for mensaje in caso["turnos"]:
        resultado = agente.conversar(user_id, mensaje)
        herramientas_invocadas_total.extend(resultado["herramientasInvocadas"])
        respuesta_final = resultado["respuesta"]
        limite_alcanzado = limite_alcanzado or resultado["limiteAlcanzado"]
        # .get() con default: compatibilidad con conversar() de versiones
        # previas a la correccion del hallazgo C, que no devolvian estas claves.
        reintento_utilizado = reintento_utilizado or resultado.get("reintentoUtilizado", False)
        reintento_fallido = reintento_fallido or resultado.get("reintentoFallido", False)
    latencia_ms = round((time.perf_counter() - inicio) * 1000)

    return {
        "id": caso["id"],
        "tipo": caso["tipo"],
        "turnos": caso["turnos"],
        "herramientas_esperadas": caso["herramientas_esperadas"],
        "herramientas_invocadas": herramientas_invocadas_total,
        "coincidencia_herramientas": _coincide_herramientas(
            caso["herramientas_esperadas"], herramientas_invocadas_total
        ),
        "respuesta_final": respuesta_final,
        "limite_alcanzado": limite_alcanzado,
        "reintento_utilizado": reintento_utilizado,
        "reintento_fallido": reintento_fallido,
        "latencia_ms": latencia_ms,
    }


def main():
    golden_set = json.loads(GOLDEN_SET_PATH.read_text(encoding="utf-8"))
    user_id = golden_set["usuario_prueba"]
    agente = WellnessCoachAgent()

    resultados = []
    for i, caso in enumerate(golden_set["casos"], 1):
        # CORRECCION (hallazgo A, verificacion real #15): se reinicia la
        # memoria conversacional al INICIO de cada caso, no solo una vez al
        # sembrar el usuario. Sin esto, un caso multi-turno como AG-06
        # (que introduce dolor de rodilla) contaminaba todos los casos
        # posteriores en la misma corrida -- la evaluacion dejaba de ser
        # reproducible, porque el resultado dependia del orden de ejecucion.
        # Dentro de un mismo caso multi-turno (AG-06 en si) la memoria SI
        # se acumula entre sus propios turnos, porque eso es exactamente lo
        # que ese caso mide -- solo se limpia ENTRE casos, nunca dentro de
        # uno.
        agente.memoria.limpiar_historial(user_id)

        print(f"[{i}/{len(golden_set['casos'])}] Evaluando {caso['id']} ({caso['tipo']})...")
        resultado = evaluar_caso(agente, user_id, caso)
        resultados.append(resultado)
        marca = "OK" if resultado["coincidencia_herramientas"] else "REVISAR"
        print(f"    -> {marca} | herramientas: {[h['nombre'] for h in resultado['herramientas_invocadas']]}")

    metricas = calcular_metricas(resultados)

    RESULTADOS_PATH.write_text(
        json.dumps({"resultados": resultados, "metricas": metricas}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\n" + "=" * 60)
    print("RESUMEN")
    print("=" * 60)
    print(f"Casos evaluados: {metricas['total_casos']}")
    print(f"Tasa de acierto de herramientas: {metricas['tasa_acierto_herramientas']:.1%}")
    print(f"Casos con limite de iteraciones alcanzado: {metricas['casos_con_limite_alcanzado']}")
    print(f"Latencia promedio: {metricas['latencia_promedio_ms']} ms")
    print(f"\nResultados completos guardados en: {RESULTADOS_PATH}")


if __name__ == "__main__":
    main()