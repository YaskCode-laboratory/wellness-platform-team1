"""Comprobacion de las integraciones externas del sistema multiagente.

Entregable de S3-05 ("evidencia reproducible de consultas o utilizacion de
datos"). Verifica que cada dependencia externa responde y que devuelve lo que
se espera, sin invocar a ningun agente.

POR QUE SEPARADO DE LAS PRUEBAS UNITARIAS

Las 109 pruebas de la suite usan mocks: no tocan Firestore, ni Vertex AI, ni
ChromaDB, ni Open-Meteo. Esa decision es deliberada -- es lo que permite que el
CI corra sin credenciales de GCP -- pero deja un punto ciego que este sprint y
el anterior demostraron que es real: en el Sprint 2 las 50 pruebas estaban en
verde mientras un error 500 de Open-Meteo tumbaba la evaluacion completa.

Este script cubre ese punto ciego. No sustituye a la suite: comprueba cosas
distintas. La suite verifica la logica; esto verifica que el mundo exterior
esta donde lo dejamos.

USO

    python -m scripts.verificacion.verificar_integraciones

Requiere credenciales de GCP. Devuelve codigo de salida 1 si alguna
integracion falla, para poder encadenarlo en un script de despliegue.
"""

import sys
import time
import traceback

USUARIO_PRUEBA = "usuario-eval-agente"

ANCHO = 72


def _titulo(texto: str) -> None:
    print("\n" + "=" * ANCHO)
    print(texto)
    print("=" * ANCHO)


def _resultado(nombre: str, ok: bool, detalle: str, ms: int) -> dict:
    marca = "OK     " if ok else "FALLO  "
    print(f"  [{marca}] {nombre:38} {ms:>6} ms  {detalle}")
    return {"nombre": nombre, "ok": ok, "detalle": detalle, "latencia_ms": ms}


def _medir(nombre: str, funcion) -> dict:
    """Ejecuta una comprobacion y captura cualquier fallo.

    Se captura Exception de forma amplia a proposito: el objetivo de este
    script es reportar el estado de TODAS las integraciones, no detenerse en la
    primera que falle. Un diagnostico parcial no sirve de mucho cuando lo que
    se quiere saber es que esta caido.
    """
    inicio = time.perf_counter()
    try:
        detalle = funcion()
        ms = round((time.perf_counter() - inicio) * 1000)
        return _resultado(nombre, True, detalle, ms)
    except Exception as e:
        ms = round((time.perf_counter() - inicio) * 1000)
        print(f"         {type(e).__name__}: {e}")
        return _resultado(nombre, False, f"{type(e).__name__}", ms)


# ── Comprobaciones ───────────────────────────────────────────────────────────

def comprobar_configuracion() -> str:
    from src.utils import config

    faltantes = [
        nombre
        for nombre in ("GCP_PROJECT", "GCP_LOCATION", "GEMINI_MODEL", "EMBEDDING_MODEL")
        if not getattr(config, nombre, None)
    ]
    if faltantes:
        raise ValueError(f"configuracion incompleta: {faltantes}")
    return f"proyecto={config.GCP_PROJECT} modelo={config.GEMINI_MODEL}"


def comprobar_firestore_perfil() -> str:
    from src.data.repositorio_corredor import RepositorioCorredor

    perfil = RepositorioCorredor().obtener_perfil(USUARIO_PRUEBA)
    if perfil.uid != USUARIO_PRUEBA:
        raise ValueError("el perfil devuelto no corresponde al usuario de prueba")
    return f"nivel={perfil.nivel} ciudad={perfil.ciudad} peso={perfil.peso}"


def comprobar_firestore_sesiones() -> str:
    from src.data.repositorio_corredor import RepositorioCorredor

    repo = RepositorioCorredor()
    actual, anterior = repo.calcular_carga_semanal(USUARIO_PRUEBA)
    objetivos = repo.obtener_objetivos_activos(USUARIO_PRUEBA)
    return f"carga {actual} km (previa {anterior} km), {len(objetivos)} objetivo(s)"


def comprobar_firestore_memoria() -> str:
    from src.agents.wellness_coach.memory import MemoriaConversacional

    turnos = MemoriaConversacional().obtener_historial(USUARIO_PRUEBA)
    return f"{len(turnos)} turno(s) en la ventana de contexto"


def comprobar_firestore_delegaciones() -> str:
    from src.database.firestore_client import db
    from src.orchestration.delegation.registro import COLECCION

    docs = list(db.collection(COLECCION).limit(5).stream())
    return f"{len(docs)} traza(s) accesibles (muestra de 5)"


def comprobar_vertex_embeddings() -> str:
    from src.rag.embeddings.embedder import embed_query

    vector = embed_query("prueba de conectividad")
    if not vector:
        raise ValueError("el embedding devuelto esta vacio")
    return f"vector de {len(vector)} dimensiones"


def comprobar_vertex_generacion() -> str:
    from src.orchestration.orchestrator.clasificador import clasificar

    resultado = clasificar("Puedo entrenar fuerte hoy?")
    if resultado.intencion == "no_reconocida":
        raise ValueError("el clasificador degrado: revisar el log")
    return f"intencion={resultado.intencion} confianza={resultado.confianza}"


def comprobar_chromadb_coach() -> str:
    from src.agents.wellness_coach.tools.conocimiento import consultar_base_conocimiento

    salida = consultar_base_conocimiento("progresion de la carga semanal")
    docs = salida.get("doc_ids_disponibles", [])
    if not docs:
        raise ValueError("la base de conocimiento no devolvio fragmentos")
    if "KB-006" in docs:
        raise ValueError("FRONTERA VIOLADA: el Coach recupero KB-006 (nutricion)")
    return f"{len(docs)} fragmento(s): {sorted(set(docs))}"


def comprobar_chromadb_nutricion() -> str:
    from src.rag.retriever.retriever import recuperar

    chunks = recuperar("hidratacion durante la carrera", k=3, categoria="nutricion")
    if not chunks:
        raise ValueError("la categoria nutricion no devolvio fragmentos")
    categorias = {c["metadata"]["categoria"] for c in chunks}
    if categorias != {"nutricion"}:
        raise ValueError(f"FRONTERA VIOLADA: se recuperaron categorias {categorias}")
    return f"{len(chunks)} fragmento(s), todos de nutricion"


def comprobar_open_meteo() -> str:
    from src.agents.wellness_coach.tools.clima import consultar_clima

    salida = consultar_clima("Maracaibo")
    if not salida.get("disponible"):
        # No se lanza excepcion: la degradacion del hallazgo D es el
        # comportamiento correcto ante un servicio caido. Se reporta como
        # fallo de la integracion, no del codigo.
        raise ValueError(f"servicio no disponible: {salida.get('mensaje')}")
    return f"{salida.get('temperaturaC')} C en Maracaibo"


COMPROBACIONES = [
    ("Configuracion por variables de entorno", comprobar_configuracion),
    ("Firestore - perfil del corredor", comprobar_firestore_perfil),
    ("Firestore - sesiones y objetivos", comprobar_firestore_sesiones),
    ("Firestore - memoria conversacional", comprobar_firestore_memoria),
    ("Firestore - registro de delegaciones", comprobar_firestore_delegaciones),
    ("Vertex AI - embeddings", comprobar_vertex_embeddings),
    ("Vertex AI - generacion", comprobar_vertex_generacion),
    ("ChromaDB - dominio del Coach", comprobar_chromadb_coach),
    ("ChromaDB - dominio de nutricion", comprobar_chromadb_nutricion),
    ("Open-Meteo - clima", comprobar_open_meteo),
]


def main() -> int:
    _titulo("VERIFICACION DE INTEGRACIONES — Sistema multiagente Wellness")
    print(f"  Usuario de prueba: {USUARIO_PRUEBA}")
    print(f"  Siembra previa requerida: python -m scripts.evaluation.seed_agent_test_user")
    print()

    resultados = [_medir(nombre, funcion) for nombre, funcion in COMPROBACIONES]

    fallidas = [r for r in resultados if not r["ok"]]
    total_ms = sum(r["latencia_ms"] for r in resultados)

    _titulo("RESUMEN")
    print(f"  Integraciones comprobadas : {len(resultados)}")
    print(f"  Correctas                 : {len(resultados) - len(fallidas)}")
    print(f"  Fallidas                  : {len(fallidas)}")
    print(f"  Tiempo total              : {total_ms} ms")

    if fallidas:
        print()
        for r in fallidas:
            print(f"  FALLO: {r['nombre']} — {r['detalle']}")

    return 1 if fallidas else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        traceback.print_exc()
        sys.exit(1)