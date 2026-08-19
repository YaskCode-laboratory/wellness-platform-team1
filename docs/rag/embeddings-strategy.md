# Estrategia de Embeddings

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Implementación: [`src/rag/embeddings/embedder.py`](../../src/rag/embeddings/embedder.py)

---

## 1. Fundamento

Un **embedding** es la proyección de un texto en un vector de números reales que representa su significado. En el modelo empleado, cada texto se convierte en 768 dimensiones.

Lo relevante no son los valores individuales sino la propiedad geométrica que emerge del entrenamiento del modelo: **textos con significado próximo producen vectores próximos en el espacio**.

Esta propiedad es lo que separa la búsqueda semántica de la búsqueda léxica. La consulta *"¿Cuánto debo bajar los kilómetros las semanas previas a mi maratón?"* no comparte ningún término con la afirmación *"El tapering implica reducir el volumen entre 41 % y 60 % antes de competir"*, y sin embargo sus vectores quedan próximos. Un buscador por palabras clave no establecería esa correspondencia.

---

## 2. Modelo seleccionado

| Parámetro | Valor |
|---|---|
| Modelo | `text-embedding-004` |
| Proveedor | Vertex AI (Google Cloud) |
| Dimensiones | 768 |
| Autenticación | Application Default Credentials |
| Proyecto GCP | `runcoach-ai-496921` |
| Región | `us-central1` |

### Justificación

**Continuidad de infraestructura.** La plataforma ya operaba sobre Vertex AI con Gemini 2.5 Flash y credenciales ADC configuradas. Incorporar el modelo de embeddings del mismo proveedor evita gestionar un segundo conjunto de credenciales y mantiene los datos dentro del mismo perímetro.

**Rendimiento multilingüe.** El corpus está redactado en español. `text-embedding-004` ofrece soporte multilingüe adecuado, a diferencia de modelos entrenados predominantemente en inglés.

**Sin coste de infraestructura propia.** Alternativas de código abierto —`sentence-transformers`, `multilingual-e5`— habrían requerido alojar el modelo. El servicio gestionado elimina esa carga operativa.

### Alternativas evaluadas

| Opción | Motivo de descarte |
|---|---|
| `sentence-transformers` local | Requiere infraestructura de inferencia propia; sin ventaja de calidad demostrada para este corpus |
| OpenAI `text-embedding-3-*` | Introduce un segundo proveedor y otro conjunto de credenciales |
| Embeddings por defecto de ChromaDB | Modelo pequeño orientado a inglés; calidad insuficiente para corpus técnico en español |

---

## 3. Diferenciación por `task_type`

Es la decisión técnica de mayor impacto sobre la calidad de la recuperación, y frecuentemente omitida en implementaciones de RAG.

Los modelos de embedding de Vertex AI aceptan un parámetro que declara el **rol del texto**:

| Valor | Uso |
|---|---|
| `RETRIEVAL_DOCUMENT` | Textos que se almacenan en el índice |
| `RETRIEVAL_QUERY` | Consultas que se buscan contra el índice |

### Por qué la distinción importa

Una pregunta y su respuesta **no se parecen textualmente**. La pregunta *"¿Cuánto debo reducir el volumen antes de una maratón?"* y la respuesta *"El tapering óptimo implica una reducción del 41 % al 60 % del volumen"* tienen estructura sintáctica y vocabulario distintos.

Al declarar el rol de cada texto, el modelo los proyecta a un espacio donde pregunta y respuesta quedan próximas pese a esa disimilitud superficial.

Emplear el mismo `task_type` para ambos es un **error silencioso**: el sistema no falla, simplemente recupera peor. Es especialmente insidioso porque no produce ninguna señal de error.

### Implementación

```python
def embed_texts(textos, task_type="RETRIEVAL_DOCUMENT"):
    entradas = [TextEmbeddingInput(text=t, task_type=task_type) for t in lote]
    ...

def embed_query(consulta):
    return embed_texts([consulta], task_type="RETRIEVAL_QUERY")[0]
```

El retriever invoca siempre `embed_query`; el script de ingesta invoca siempre `embed_texts` con el valor por defecto.

---

## 4. Batching por presupuesto de tokens

### El problema encontrado

La implementación inicial agrupaba en lotes de 100 textos, asumiendo que el límite de la API era el número de elementos. La ejecución sobre los 82 chunks produjo:

```
400 Unable to submit request because the input token count is 20101
but the model supports up to 20000
```

El límite real es de **tokens totales por petición**, no de cantidad de textos. Los 82 chunks sumaron 20.101 tokens, excediendo el límite por 101.

### Lección general

Los límites de API suelen ser **multidimensionales**: cantidad de elementos, tokens totales, tamaño en bytes, peticiones por minuto. Agrupar únicamente por cantidad es frágil. La agrupación debe atender a la dimensión que efectivamente restringe.

### Solución implementada

```python
MAX_TOKENS_LOTE = 15000      # margen de seguridad sobre el límite de 20.000
MAX_TEXTOS_LOTE = 25
CHARS_POR_TOKEN = 3          # estimación conservadora para español
```

La función `_agrupar_en_lotes` respeta **ambas** restricciones simultáneamente, cerrando el lote en curso cuando cualquiera de las dos se alcanzaría.

La estimación de 3 caracteres por token es deliberadamente conservadora. La proporción real en español ronda 3.5–4 caracteres por token; subestimarla produce lotes menores que el máximo teórico, lo cual es preferible a un fallo por exceso.

### Resultado

Los 82 chunks se procesan en 4 lotes sin error:

```
lote 1/4 → 25/82 textos
lote 2/4 → 50/82 textos
lote 3/4 → 75/82 textos
lote 4/4 → 82/82 textos
```

---

## 5. Verificación empírica del espacio semántico

Se ejecutó una prueba de validación sobre cuatro textos del dominio para confirmar el comportamiento esperado del espacio de embeddings.

| Par comparado | Similitud coseno |
|---|---|
| Afirmación sobre tapering ↔ **pregunta** sobre tapering | **0.7713** |
| Tapering ↔ regla del 10 % | 0.7069 |
| Regla del 10 % ↔ nutrición | 0.6999 |
| Tapering ↔ nutrición | **0.6664** |

El ordenamiento es el correcto: la correspondencia máxima se da entre la afirmación sobre tapering y la pregunta sobre tapering, pese a que la pregunta no contiene el término "tapering" ni "volumen" ni la cifra "41 %". La correspondencia mínima se da entre los dos temas más distantes del dominio.

### Sobre el rango estrecho

Los valores se sitúan entre 0.67 y 0.77 — un rango de apenas 0.11. Existen dos causas:

1. **Homogeneidad del dominio.** Los cuatro textos pertenecen al ámbito del entrenamiento deportivo y comparten vocabulario y contexto, elevando la similitud basal. Comparados contra un texto de dominio ajeno, los valores caerían sustancialmente.

2. **Compresión del coseno en alta dimensionalidad.** Fenómeno geométrico conocido en espacios de muchas dimensiones.

### Consecuencia operativa

**No deben emplearse umbrales absolutos de similitud.** Una regla del tipo *"si similitud > 0.8 entonces es relevante"* sería arbitraria y frágil: ningún par del dominio alcanzaría ese valor.

El criterio correcto es **ordenamiento top-k**: recuperar los k fragmentos más próximos con independencia del valor absoluto de similitud. Es la aproximación implementada en el retriever.

---

## 6. Similitud coseno

La proximidad se mide como el coseno del ángulo entre vectores:

```python
def cosine_similarity(a, b):
    producto = sum(x * y for x, y in zip(a, b))
    norma_a = sum(x * x for x in a) ** 0.5
    norma_b = sum(y * y for y in b) ** 0.5
    return producto / (norma_a * norma_b)
```

Se emplea el ángulo y no la distancia euclídea porque la **magnitud** del vector correlaciona con la longitud del texto, que no es una dimensión semántica relevante. Solo interesa la *dirección* del significado.

| Valor | Interpretación |
|---|---|
| 1.0 | Dirección idéntica |
| ~0.8 | Fuertemente relacionados |
| ~0.5 | Relación moderada |
| ~0.0 | Sin relación |

---

## 7. Coste y rendimiento

| Operación | Volumen | Frecuencia |
|---|---|---|
| Indexación completa del corpus | 82 embeddings, 4 peticiones | Solo al modificar la KB |
| Consulta en runtime | 1 embedding, 1 petición | Por cada análisis |

El diseño concentra el coste en la indexación, que es infrecuente. En runtime cada consulta requiere un único embedding de la consulta sintetizada — el resto es búsqueda vectorial local sobre ChromaDB, sin llamadas de red.

Los vectores se persisten en `data/vector_store/`, de modo que reiniciar el servicio no implica recalcularlos.

---

## 8. Limitaciones

**Dependencia de proveedor.** El corpus está indexado con `text-embedding-004`. Migrar a otro modelo exige reindexar la totalidad del corpus, dado que los espacios vectoriales de modelos distintos no son compatibles.

**Deprecación anunciada.** El SDK `vertexai.language_models` emite advertencia de deprecación con retirada prevista para junio de 2026. La migración a `google-genai` está identificada como trabajo pendiente.

**Sin normalización de consulta.** Las consultas se embeben tal cual se sintetizan, sin corrección ortográfica, expansión de sinónimos ni normalización terminológica. Esta ausencia contribuye al fallo del caso EV-16, donde el registro coloquial del usuario no alcanzó el registro técnico del corpus.

**Estimación de tokens aproximada.** La proporción de 3 caracteres por token es heurística. Emplear la API `CountTokens` proporcionaría exactitud a cambio de una petición adicional por lote.
