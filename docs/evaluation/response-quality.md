# Calidad de las Respuestas

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

---

## 1. Alcance de esta evaluación

Se evalúa la etapa de **generación**: dado un conjunto de fragmentos recuperados, ¿utiliza el modelo ese conocimiento de forma correcta y trazable?

Se emplean tres aproximaciones:

| Aproximación | Naturaleza | Estado |
|---|---|---|
| Precisión de citación | Cuantitativa, automatizada | Implementada |
| Comparación legacy / RAG | Cualitativa, sobre casos | Ejecutada |
| Faithfulness con LLM evaluador | Cuantitativa, automatizada | **Pendiente** |

La tercera se documenta como carencia reconocida en la sección 6.

---

## 2. Precisión de citación

### Definición

```
precisión_citas = fuentes válidas / (fuentes válidas + fuentes inventadas)
```

Una fuente es **válida** si su `doc_id` figura entre los fragmentos efectivamente entregados al modelo. Es **inventada** si el modelo la cita sin haberla recibido.

### Fundamento

Este modo de falla —cita alucinada— es particularmente problemático porque la respuesta puede ser correcta en contenido y formato mientras la atribución es falsa. En un sistema cuya ventaja declarada es la trazabilidad, una cita inventada anula el beneficio.

### Implementación

```python
def validar_fuentes(fuentes_citadas, chunks):
    disponibles = {c["metadata"]["doc_id"] for c in chunks}
    validas = [f for f in citadas if f in disponibles]
    inventadas = [f for f in citadas if f not in disponibles]
    return validas, inventadas
```

Las fuentes inventadas se eliminan del campo `fuentes` y se registran en la metadata de trazabilidad.

### Observaciones

| Ejecución | Citas emitidas | Válidas | Inventadas | Precisión |
|---|---|---|---|---|
| CP-01 (versión previa a la instrucción 7) | KB-004, KB-005 | 1 | 1 | 0.667 |
| CP-01 (tras instrucción 7) | KB-004, KB-001 | 2 | 0 | 1.000 |
| CP-02 | KB-001 | 1 | 0 | 1.000 |

La instrucción explícita en el prompt —*"cita únicamente los doc_id que aparecen en los fragmentos recuperados"*— redujo la incidencia pero no puede considerarse garantía. La validación programática permanece como salvaguarda.

### Hallazgo secundario: filtración en texto libre

Tras validar el array `fuentes`, se detectó que la cita inventada persistía en el campo `fundamento`:

```
"...mecanismo causal dominante de lesiones por sobreuso. [KB-004], [KB-001], [KB-005]"
```

El array estaba limpio; la prosa no. Se añadió la instrucción 8 al prompt, que prohíbe identificadores en los campos destinados al usuario final.

**Principio derivado:** cada superficie donde el modelo puede citar requiere su propia defensa. Limpiar una no protege las demás.

---

## 3. Comparación legacy frente a RAG

El sistema expone `POST /agent/{userId}/compare`, que ejecuta ambas arquitecturas sobre el mismo estado del corredor y devuelve las dos respuestas.

### Caso CP-01 — Principiante, incremento del 46 %

**Modo legacy:**

```json
{
  "tipo": "descanso",
  "mensaje": "¡Excelente comienzo con esas dos sesiones! 15km en un día es
              una carga considerable... te recomiendo un día de descanso hoy.",
  "alerta": null,
  "prioridad": "alta"
}
```

**Modo RAG:**

```json
{
  "tipo": "descanso",
  "mensaje": "Tu volumen semanal ha aumentado un 46.2%. Como corredor
              principiante, es crucial consolidar tu carga actual...",
  "fundamento": "Un incremento tan rápido de volumen, especialmente en un
                 corredor principiante con base estrecha, es un factor de
                 riesgo. Los tejidos necesitan tiempo para adaptarse...",
  "alerta": "Este incremento es excesivo y te expone a un alto riesgo de
             lesión por sobreuso...",
  "prioridad": "alta",
  "fuentes": ["KB-004", "KB-001"],
  "confianza": "alta"
}
```

**Diferencias observadas:**

| Dimensión | legacy | rag |
|---|---|---|
| Alerta emitida | No (`null`) | Sí, con mecanismo explicado |
| Fundamento | Ausente | Presente, referido al conocimiento recuperado |
| Fuentes | Ninguna | KB-004, KB-001 |
| Calificación de confianza | Ausente | `alta` |
| Auditabilidad | Nula | Completa vía `_rag` |

El modo legacy calificó la situación como *"excelente comienzo"* y no emitió alerta pese a que el incremento del 46 % en un corredor principiante corresponde a un perfil de riesgo documentado.

### Caso CP-02 — Intermedio, incremento del 18.4 %

**Modo RAG (extracto):**

> *"Para corredores no principiantes, como tú, la evidencia sugiere que incrementos cercanos al 20-25% pueden ser tolerados. Realiza un rodaje, manteniendo la intensidad y monitoreando la carga de cada sesión individual para prevenir lesiones."*

`alerta: null` · `prioridad: media`

El sistema legacy, cuyo prompt instruye emitir alerta ante cualquier incremento superior al 10 %, habría marcado esta situación como riesgo.

**Este caso es el más ilustrativo del sprint.** El mismo incremento produce evaluaciones opuestas según el nivel del corredor, y esa modulación no está programada: procede del conocimiento recuperado. Además, el sistema redirige la atención hacia el indicador con mejor respaldo empírico —el pico de carga en sesión individual— en lugar del volumen semanal agregado.

---

## 4. Verificación de anclaje al corpus

Se comprobó que las respuestas incorporan contenido presente en los fragmentos recuperados y ausente del prompt base.

| Afirmación en la respuesta | Origen |
|---|---|
| *"los tejidos necesitan tiempo para adaptarse a la carga"* | KB-004 § Naturaleza del problema |
| *"corredor principiante con base estrecha"* | KB-004 § La paradoja del volumen |
| *"incrementos cercanos al 20-25% pueden ser tolerados"* | KB-001 § Cómo debe interpretarse |
| *"monitoreando la carga de cada sesión individual"* | KB-001 § Qué sí muestra la evidencia |

Ninguna de estas formulaciones figura en la plantilla del prompt. Su presencia confirma que el modelo está empleando el conocimiento recuperado y no exclusivamente su conocimiento paramétrico.

---

## 5. Latencia

| Ejecución | legacy | rag | Δ |
|---|---|---|---|
| CP-01 (datos reales, `/compare`) | 14.963 ms | 13.747 ms | −1.216 ms |

**Esta medición no permite conclusión alguna.** Se trata de una sola muestra, y la latencia de Gemini presenta variabilidad sustancial entre invocaciones. Que el modo RAG resultara más rápido en esta ejecución es probablemente ruido.

Una comparación defendible requeriría N ejecuciones con reporte de mediana y dispersión. Se registra como pendiente.

Consideración teórica: el modo RAG añade una llamada de embedding de la consulta (~200 ms) más búsqueda vectorial local (despreciable), pero entrega al modelo un prompt más acotado y estructurado, lo que puede reducir el tiempo de generación. El efecto neto es indeterminado sin medición adecuada.

---

## 6. Carencia reconocida: faithfulness

La evaluación de **faithfulness** —grado en que cada afirmación de la respuesta está sustentada por los fragmentos recuperados— **no está implementada**.

### Qué requeriría

Un procedimiento con LLM evaluador:

1. Descomponer la respuesta generada en afirmaciones atómicas
2. Para cada afirmación, determinar si el contexto recuperado la sustenta
3. Calcular `faithfulness = afirmaciones sustentadas / afirmaciones totales`

Complementariamente, **answer relevance**: grado de correspondencia entre la respuesta y la situación planteada.

### Por qué no se implementó

Restricción de tiempo. El sprint se entregó con retraso respecto a la fecha prevista y se priorizaron los componentes de recuperación, cuya evaluación cuantitativa está completa.

### Cobertura parcial existente

La precisión de citación cubre una dimensión de la fidelidad —la atribución— pero no verifica que el contenido de cada afirmación esté respaldado. Un modelo podría citar correctamente KB-001 y afirmar algo que ese documento no sostiene.

La verificación manual de la sección 4 aporta evidencia cualitativa de anclaje, pero no es sistemática ni reproducible automáticamente.

### Propuesta

Implementar `scripts/evaluation/evaluate_generation.py` en el Sprint 2, con Gemini como evaluador sobre el conjunto de casos de referencia, reportando faithfulness y answer relevance junto a las métricas de recuperación ya existentes.

---

## 7. Síntesis

**Lo verificado:**

- El sistema RAG produce respuestas con fundamento explícito, fuentes citadas y calificación de confianza, capacidades ausentes en la arquitectura previa
- La modulación por nivel de corredor procede del conocimiento recuperado, no de lógica programada
- Las citas inventadas se detectan y descartan de forma automatizada
- Las respuestas incorporan contenido verificablemente procedente del corpus

**Lo no verificado:**

- Faithfulness cuantitativa sobre un conjunto sistemático
- Answer relevance
- Latencia comparada con potencia estadística
- Consistencia entre ejecuciones sobre un mismo estado

**Valoración honesta:** la evidencia de mejora cualitativa es sólida y está documentada con casos concretos. La evaluación cuantitativa de la etapa de generación es incompleta y constituye la principal carencia metodológica de este sprint.
