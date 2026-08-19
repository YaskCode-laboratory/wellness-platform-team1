# Casos de Prueba

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Conjunto de referencia: [`data/evaluation/golden_set.json`](../../data/evaluation/golden_set.json)

---

## 1. Estructura del conjunto

```json
{
  "id": "EV-01",
  "consulta": "¿Es cierto que no debo aumentar más de 10% mi kilometraje semanal?",
  "docs_esperados": ["KB-001"],
  "categoria": "carga_entrenamiento"
}
```

Dieciocho casos que cubren las siete categorías de la taxonomía, con dos a cuatro casos por categoría.

---

## 2. Criterios de construcción

**Registro de usuario.** Las consultas se redactaron como las formularía un corredor, no reproduciendo la terminología del corpus. El objetivo es evaluar la capacidad de salvar la brecha léxica, no la coincidencia de vocabulario.

**Cobertura completa.** Toda categoría de la taxonomía tiene al menos dos casos. No hay dominios de la knowledge base sin evaluar.

**Variedad de formulación.** El conjunto incluye preguntas directas (*"Qué es la zona 2"*), descripciones de síntomas (*"Me duele la rodilla cada vez que salgo a correr"*), consultas de decisión (*"Cuánto debo reducir los kilómetros..."*) y verificaciones de creencias (*"¿Es cierto que no debo aumentar más de 10%...?"*).

**Casos de correspondencia múltiple.** EV-09 espera dos documentos, verificando el comportamiento cuando la respuesta requiere conocimiento de fuentes distintas.

---

## 3. Inventario completo

### Carga de entrenamiento — KB-001

| ID | Consulta | Esperado | Resultado k=3 |
|---|---|---|---|
| EV-01 | ¿Es cierto que no debo aumentar más de 10% mi kilometraje semanal? | KB-001 | ✓ P=1.00 RR=1.00 |
| EV-02 | Qué es el ratio de carga aguda crónica y cómo se calcula | KB-001 | ✓ P=1.00 RR=1.00 |
| EV-03 | Cuánto volumen puedo subir por semana si ya soy un corredor experimentado | KB-001 | ✓ P=0.67 RR=1.00 |
| EV-04 | Diferencia entre carga interna y carga externa de entrenamiento | KB-001 | ✓ P=0.33 RR=1.00 |

**EV-01 es el caso testigo del sprint.** Formula en tono de duda la regla codificada rígidamente en el sistema previo. Recupera los fragmentos sobre origen de la regla y evidencia que la cuestiona, lo que permite al agente responder con matices en lugar de confirmar la heurística.

### Zonas fisiológicas — KB-002

| ID | Consulta | Esperado | Resultado k=3 |
|---|---|---|---|
| EV-05 | Qué es la zona 2 y qué beneficios tiene entrenarla | KB-002 | ✓ P=1.00 RR=1.00 |
| EV-06 | Cuál es la diferencia entre el primer y el segundo umbral de lactato | KB-002 | ✓ P=1.00 RR=1.00 |
| EV-07 | Cómo calculo mis zonas de frecuencia cardíaca para correr | KB-002 | ✓ P=1.00 RR=1.00 |

Categoría con precisión perfecta. El vocabulario de las consultas es próximo al del documento, lo que facilita la correspondencia.

### Distribución de intensidad — KB-003

| ID | Consulta | Esperado | Resultado k=3 |
|---|---|---|---|
| EV-08 | En qué consiste el entrenamiento polarizado ochenta veinte | KB-003 | ✓ P=1.00 RR=1.00 |
| EV-09 | Por qué es contraproducente correr siempre a ritmo medio cómodo | KB-003, KB-002 | ✓ P=1.00 RR=1.00 |

EV-09 verifica correspondencia múltiple. La deriva hacia intensidad media se aborda tanto en KB-003 (distribución) como en KB-002 (caracterización de Z3). El sistema recuperó ambos.

### Prevención de lesiones — KB-004

| ID | Consulta | Esperado | Resultado k=3 |
|---|---|---|---|
| EV-10 | Me duele la rodilla cada vez que salgo a correr, qué debo hacer | KB-004 | ✓ P=1.00 RR=1.00 |
| EV-11 | Cuáles son los principales factores de riesgo de lesión en corredores | KB-004 | ✓ P=1.00 RR=1.00 |
| EV-12 | Cómo evito el dolor en la espinilla al aumentar entrenamientos | KB-004 | ✓ P=0.67 RR=1.00 |

**EV-10 es el caso más demostrativo de recuperación semántica.** La consulta no contiene los términos *lesión*, *sobreuso*, *patelofemoral* ni ningún tecnicismo presente en KB-004. La correspondencia se establece exclusivamente por significado.

**EV-12** emplea *"espinilla"*, término coloquial que el documento denomina *periostitis tibial*. El caso acierta pese a la brecha léxica, lo que indica que el modelo de embeddings salva distancias moderadas de registro.

### Tapering — KB-005

| ID | Consulta | Esperado | Resultado k=3 |
|---|---|---|---|
| EV-13 | Cuánto debo reducir los kilómetros las semanas previas a una maratón | KB-005 | ✓ P=1.00 RR=1.00 |
| EV-14 | Durante la puesta a punto debo correr también más despacio | KB-005 | ✓ P=0.67 RR=1.00 |

EV-14 verifica la recuperación de conocimiento que contradice una intuición extendida: durante el tapering se reduce el volumen pero **se mantiene la intensidad**.

### Nutrición — KB-006

| ID | Consulta | Esperado | Resultado k=3 |
|---|---|---|---|
| EV-15 | Cuántos gramos de carbohidratos tomar por hora en carreras largas | KB-006 | ✓ P=1.00 RR=1.00 |
| EV-16 | Qué pasa si como muy poco para la cantidad que entreno | KB-006 | **✗ P=0.00 RR=0.00** |

**EV-16 es el único fallo del conjunto.** Análisis detallado en `docs/evaluation/retrieval-metrics.md`, sección 6.

### Recuperación — KB-007

| ID | Consulta | Esperado | Resultado k=3 |
|---|---|---|---|
| EV-17 | Cuántas horas necesito dormir si entreno con volumen alto | KB-007 | ✓ P=0.67 RR=1.00 |
| EV-18 | Sirven los baños de agua fría para recuperarse después de correr | KB-007 | ✓ P=0.67 RR=1.00 |

---

## 4. Casos de prueba del pipeline completo

Además de la evaluación de recuperación, se ejecutaron casos sobre el pipeline íntegro para verificar la generación fundamentada.

### CP-01 — Principiante con incremento excesivo

```
Nivel      : principiante
Volumen    : 19 km (semana previa 13 km) → +46.2 %
Meta       : 30 km semanales
Sesiones   : 3 registradas en los últimos 5 días
```

**Fragmentos recuperados:** KB-004 (×4), KB-001 (×1)

**Respuesta generada:**

```json
{
  "tipo": "descanso",
  "mensaje": "Tu volumen semanal ha aumentado un 46.2%... Como corredor
              principiante, es crucial consolidar tu carga actual antes de
              incrementarla.",
  "fundamento": "Un incremento tan rápido de volumen, especialmente en un
                 corredor principiante con base estrecha, es un factor de
                 riesgo...",
  "alerta": "Este incremento es excesivo y te expone a un alto riesgo de
             lesión por sobreuso...",
  "prioridad": "alta",
  "fuentes": ["KB-004", "KB-001"],
  "confianza": "alta"
}
```

**Verificación:** la respuesta recoge el mecanismo causal documentado en KB-004 —*"los tejidos necesitan tiempo para adaptarse a la carga"*— que no figura en el prompt sino que procede del conocimiento recuperado.

### CP-02 — Intermedio con incremento moderado

```
Nivel      : intermedio
Volumen    : 45 km (semana previa 38 km) → +18.4 %
```

**Respuesta generada (extracto):**

> *"Para corredores no principiantes, como tú, la evidencia sugiere que incrementos cercanos al 20-25% pueden ser tolerados. Realiza un rodaje, manteniendo la intensidad y monitoreando la carga de cada sesión individual."*

`alerta: null` · `prioridad: media` · `fuentes: ["KB-001"]`

**Verificación:** el mismo incremento que en un principiante dispararía alerta se evalúa como tolerable en un corredor intermedio. La modulación por nivel opera correctamente y procede del conocimiento recuperado, no de lógica programada.

### CP-03 — Detección de cita alucinada

Ejecución en la que el modelo citó `KB-005` sin haberlo recibido entre los fragmentos.

**Resultado de la validación:**

```
Precisión de citas : 0.667
Fuentes inventadas : ['KB-005']  ← descartadas
```

**Verificación:** el mecanismo de validación programática detectó y eliminó la cita inválida del campo `fuentes`. Documentado en `docs/rag/retrieval-pipeline.md`, sección 7.

---

## 5. Casos límite verificados

| Caso | Comportamiento observado |
|---|---|
| Usuario sin sesiones registradas | Retorno de mensaje informativo sin invocar al modelo |
| Usuario sin perfil en `users` | Nivel *"no declarado"*; el pipeline continúa |
| Semana actual y previa con 0 km | La consulta sintetizada incorpora *"construcción de base desde cero"* |
| Sesiones con fecha muy anterior | Campo `diasAtras` calculado; la consulta incorpora *"retorno tras interrupción"* |
| Objetivo sin `kmMeta` | `formatear_objetivos` recurre a representación JSON genérica |

---

## 6. Cobertura pendiente

**Ausencia de pruebas automatizadas.** Los directorios `tests/rag/`, `tests/unit/` e `tests/integration/` permanecen vacíos. Las verificaciones descritas se ejecutaron de forma manual mediante los puntos de entrada `__main__` de cada módulo.

Pruebas unitarias que corresponderían:

- `chunker.parse_front_matter` — documentos con y sin front-matter, YAML malformado
- `chunker.split_by_headers` — documentos sin encabezados, con un único encabezado
- `metrics.*` — casos con lista vacía, sin aciertos, con aciertos parciales
- `prompt_builder.dias_desde` — fechas futuras, formatos inválidos
- `rag_pipeline.validar_fuentes` — todas válidas, todas inventadas, lista vacía

**Sin pruebas de regresión sobre el conjunto de referencia.** Las métricas se calculan bajo demanda. No existe umbral que falle automáticamente si una modificación degrada la recuperación por debajo de un mínimo aceptable.

Ambas carencias se registran como trabajo pendiente para el Sprint 2.
