# Métricas de Recuperación

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Implementación: [`src/evaluation/metrics.py`](../../src/evaluation/metrics.py) · [`scripts/evaluation/evaluate_retrieval.py`](../../scripts/evaluation/evaluate_retrieval.py)

---

## 1. Por qué evaluar la recuperación por separado

Un sistema RAG tiene dos etapas que fallan por causas distintas:

| Etapa | Pregunta que responde | Métricas |
|---|---|---|
| **Recuperación** | ¿Se obtuvieron los documentos correctos? | Precision@k, Recall@k, MRR, Hit rate |
| **Generación** | ¿Se utilizó correctamente lo recuperado? | Faithfulness, precisión de citación |

La separación es diagnóstica: si la recuperación falla, la generación no puede compensarlo — el modelo no puede fundamentar una respuesta en conocimiento que nunca recibió. Evaluar por separado identifica **dónde** reside el problema.

---

## 2. Diseño del conjunto de referencia

El *golden set* (`data/evaluation/golden_set.json`) contiene **18 casos**, cada uno con una consulta y los documentos que deberían recuperarse.

| Categoría | Casos |
|---|---|
| `carga_entrenamiento` | 4 |
| `zonas_fisiologicas` | 3 |
| `prevencion_lesiones` | 3 |
| `distribucion_intensidad` | 2 |
| `tapering` | 2 |
| `nutricion` | 2 |
| `recuperacion` | 2 |

### Criterio de relevancia: nivel documento

La relevancia se define a nivel de **documento** (`doc_id`), no de fragmento.

**Justificación.** Exigir la recuperación de un fragmento específico sería excesivamente estricto: si el sistema devuelve un fragmento distinto del mismo documento que también responde a la consulta, eso constituye un acierto funcional, no un fallo. Los documentos del corpus son temáticamente cohesivos por diseño —un documento por categoría taxonómica—, lo que hace del documento la unidad de relevancia apropiada.

Es una decisión metodológica explícita, no una simplificación por conveniencia.

### Redacción de las consultas

Las consultas se redactaron deliberadamente en **registro de usuario**, no reproduciendo la terminología del corpus:

- *"Me duele la rodilla cada vez que salgo a correr, qué debo hacer"* en lugar de *"síndrome de dolor patelofemoral"*
- *"Cuánto debo reducir los kilómetros las semanas previas a una maratón"* en lugar de *"parámetros óptimos de tapering"*

El objetivo es evaluar la capacidad real de salvar la distancia entre el lenguaje del usuario y el del corpus, no la coincidencia léxica.

---

## 3. Métricas empleadas

### Precision@k

Proporción de los k fragmentos recuperados que pertenecen a documentos relevantes.

> *De lo que se recuperó, ¿cuánto sirve?*

### Recall@k

Proporción de los documentos esperados que aparecen entre los k recuperados.

> *De lo que debía recuperarse, ¿cuánto se recuperó?*

### MRR — Mean Reciprocal Rank

Media del inverso de la posición del primer resultado relevante. Si el primer acierto está en posición 1 vale 1.0; en posición 3, 0.333; si no aparece, 0.

> *¿Aparece lo relevante en las primeras posiciones o queda sepultado?*

### Hit rate

Métrica binaria: 1.0 si al menos un documento esperado aparece en el top-k.

> *¿El sistema falló por completo en este caso?*

---

## 4. Resultados

Ejecución sobre los 18 casos, con dos valores de k:

| Métrica | k = 5 | k = 3 |
|---|---|---|
| Precision@k | 0.7667 | **0.8148** |
| Recall@k | 0.9444 | 0.9444 |
| MRR | 0.9444 | 0.9444 |
| Hit rate | 0.9444 | 0.9444 |
| Casos con acierto | 17 / 18 | 17 / 18 |

### Por categoría (k = 3)

| Categoría | n | P@3 | R@3 | MRR |
|---|---|---|---|---|
| `zonas_fisiologicas` | 3 | 1.000 | 1.000 | 1.000 |
| `distribucion_intensidad` | 2 | 1.000 | 1.000 | 1.000 |
| `prevencion_lesiones` | 3 | 0.889 | 1.000 | 1.000 |
| `tapering` | 2 | 0.833 | 1.000 | 1.000 |
| `carga_entrenamiento` | 4 | 0.750 | 1.000 | 1.000 |
| `recuperacion` | 2 | 0.667 | 1.000 | 1.000 |
| `nutricion` | 2 | 0.500 | 0.500 | 0.500 |

---

## 5. Interpretación

### MRR = 0.9444

De los 17 casos con acierto, **en todos el primer fragmento recuperado pertenecía al documento correcto**. No hay casos en los que lo relevante aparezca en segunda o tercera posición. El único caso que reduce el MRR es el fallo completo (EV-16).

Es el resultado más sólido del conjunto: cuando el sistema encuentra el documento, lo sitúa en primera posición.

### Sobre la precisión

Un P@k inferior a 1.0 es esperable y no indica deficiencia. Con `docs_esperados: ["KB-001"]` y k=3, la precisión máxima teórica solo se alcanza si los tres fragmentos proceden de KB-001. Que uno provenga de un documento adyacente —por ejemplo KB-004 sobre prevención de lesiones ante una consulta de progresión de carga— constituye frecuentemente contexto útil, no ruido.

Precision es la métrica menos informativa en esta configuración. Recall y hit rate son las determinantes.

### Decisión sobre k

Recall, MRR y hit rate son **idénticos** en k=3 y k=5. La precisión es superior en k=3.

Interpretación: los fragmentos cuarto y quinto no aportaban documentos adicionales relevantes. Únicamente diluían el contexto y consumían ventana del prompt.

**Se adoptó `TOP_K = 3`** con esta base empírica. La decisión queda documentada como derivada de medición, no de criterio arbitrario.

---

## 6. Análisis del caso fallido: EV-16

### El caso

```
Consulta  : "Qué pasa si como muy poco para la cantidad que entreno"
Esperado  : KB-006 (Nutrición)
Recuperado: KB-003, KB-003, KB-005
```

### Diagnóstico

**Brecha de registro lingüístico.** KB-006 aborda exactamente esta situación en su sección sobre disponibilidad energética y deficiencia energética relativa (RED-S). Pero lo hace con terminología técnica: *"disponibilidad energética"*, *"ingesta energética"*, *"masa magra"*.

El usuario dice *"como muy poco"*. Semánticamente equivalente, léxicamente distante — y el modelo de embeddings no salva esa distancia.

Un factor agravante: la segunda mitad de la consulta, *"para la cantidad que entreno"*, presenta alta similitud con el vocabulario de carga y volumen de entrenamiento, lo que atrajo KB-003 y KB-005.

### Valor del hallazgo

Este es el modo de falla característico de los sistemas RAG: **la distancia entre cómo pregunta el usuario y cómo está redactado el corpus**. No es un defecto de implementación sino una propiedad del enfoque, y se documenta como tal.

Se optó por conservar el fallo en lugar de corregirlo antes de la entrega. Un resultado de 18/18 obtenido tras ajustar el corpus a las consultas de evaluación sería metodológicamente cuestionable —equivaldría a entrenar sobre el conjunto de prueba— y menos informativo que un fallo diagnosticado.

### Remedios evaluados

| Remedio | Coste | Efecto esperado |
|---|---|---|
| **Enriquecer KB-006 con fraseo coloquial** — sección de sinónimos o preguntas frecuentes | Bajo | Resuelve este caso; no generaliza |
| **Expansión de consulta** — un LLM reformula la consulta antes de recuperar | Medio: una llamada adicional por consulta | Generaliza a casos no previstos |
| **Búsqueda híbrida** — combinar BM25 léxico con recuperación semántica | Alto: requiere segundo índice y fusión de rankings | Robustez frente a ambos tipos de brecha |

Se propone la expansión de consulta como línea de trabajo para el Sprint 2, por su equilibrio entre coste y generalización.

---

## 7. Reproducibilidad

```bash
python -m scripts.evaluation.evaluate_retrieval           # k = 5
python -m scripts.evaluation.evaluate_retrieval --k 3     # k = 3
```

Resultados completos, incluyendo el detalle por caso, en `data/evaluation/resultados_retrieval.json`.

---

## 8. Limitaciones de la evaluación

**Tamaño del conjunto.** Dieciocho casos permiten detectar problemas gruesos pero no ofrecen potencia estadística para comparaciones finas. Un caso fallido desplaza las métricas globales en 5.6 puntos porcentuales.

**Ausencia de anotación independiente.** El conjunto fue elaborado por el mismo equipo que curó el corpus. Existe riesgo de sesgo de confirmación: las consultas pueden reflejar inconscientemente cómo se redactaron los documentos. Una anotación por evaluadores externos sería metodológicamente superior.

**Relevancia binaria.** Un documento es relevante o no lo es. No se contempla relevancia graduada, que permitiría métricas como nDCG y una evaluación más matizada de casos con múltiples documentos parcialmente pertinentes.

**Consultas directas frente a consultas sintetizadas.** La evaluación emplea consultas en lenguaje natural. El agente en producción utiliza consultas sintetizadas a partir del estado del corredor, cuya estructura es distinta. La calidad de recuperación sobre consultas sintetizadas no está medida cuantitativamente y constituye una brecha de la evaluación actual.
