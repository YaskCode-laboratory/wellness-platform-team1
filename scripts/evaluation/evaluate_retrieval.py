"""Evaluación de la etapa de recuperación contra el golden set.

Uso:
    python -m scripts.evaluation.evaluate_retrieval
    python -m scripts.evaluation.evaluate_retrieval --k 3
"""

import argparse
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from src.evaluation.metrics import agregar, evaluar_caso
from src.rag.retriever.retriever import recuperar

RAIZ = Path(__file__).resolve().parents[2]
GOLDEN_SET = RAIZ / "data" / "evaluation" / "golden_set.json"
SALIDA = RAIZ / "data" / "evaluation" / "resultados_retrieval.json"


def main(k: int) -> None:
    datos = json.loads(GOLDEN_SET.read_text(encoding="utf-8"))
    casos = datos["casos"]

    print("=" * 78)
    print(f"EVALUACIÓN DE RECUPERACIÓN  ·  k={k}  ·  {len(casos)} casos")
    print("=" * 78)

    resultados = []
    por_categoria = defaultdict(list)

    for caso in casos:
        chunks = recuperar(caso["consulta"], k=k)
        docs_recuperados = [c["metadata"]["doc_id"] for c in chunks]

        metricas = evaluar_caso(docs_recuperados, caso["docs_esperados"], k)
        metricas["id"] = caso["id"]
        metricas["consulta"] = caso["consulta"]
        metricas["docs_esperados"] = caso["docs_esperados"]
        metricas["docs_recuperados"] = docs_recuperados

        resultados.append(metricas)
        por_categoria[caso["categoria"]].append(metricas)

        marca = "✓" if metricas["hit"] else "✗"
        print(
            f"{marca} {caso['id']}  "
            f"P@{k}={metricas['precision_at_k']:.2f}  "
            f"R@{k}={metricas['recall_at_k']:.2f}  "
            f"RR={metricas['reciprocal_rank']:.2f}   "
            f"{caso['consulta'][:52]}"
        )
        if not metricas["hit"]:
            print(f"    esperado: {caso['docs_esperados']}  →  obtenido: {docs_recuperados}")

    global_ = agregar(resultados)

    print("\n" + "=" * 78)
    print("RESULTADOS GLOBALES")
    print("=" * 78)
    print(f"  Casos evaluados     : {global_['n_casos']}")
    print(f"  Precision@{k}        : {global_['precision_at_k']:.4f}")
    print(f"  Recall@{k}           : {global_['recall_at_k']:.4f}")
    print(f"  MRR                 : {global_['mrr']:.4f}")
    print(f"  Hit rate            : {global_['hit_rate']:.4f}")

    print("\n" + "-" * 78)
    print("POR CATEGORÍA")
    print("-" * 78)
    resumen_categoria = {}
    for categoria, items in sorted(por_categoria.items()):
        agg = agregar(items)
        resumen_categoria[categoria] = agg
        print(
            f"  {categoria:26s} n={agg['n_casos']}  "
            f"P@{k}={agg['precision_at_k']:.3f}  "
            f"R@{k}={agg['recall_at_k']:.3f}  "
            f"MRR={agg['mrr']:.3f}"
        )

    SALIDA.write_text(
        json.dumps(
            {
                "fecha": datetime.utcnow().isoformat(),
                "k": k,
                "global": global_,
                "por_categoria": resumen_categoria,
                "casos": resultados,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"\nResultados guardados en data/evaluation/{SALIDA.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5, help="Número de chunks a recuperar")
    main(parser.parse_args().k)