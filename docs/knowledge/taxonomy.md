# Taxonomía del Dominio Wellness

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Archivo fuente: [`src/knowledge/taxonomy/wellness_taxonomy.yaml`](../../src/knowledge/taxonomy/wellness_taxonomy.yaml)

---

## 1. Propósito y diferencia con la ontología

La ontología declara **qué entidades existen y cómo se relacionan**. La taxonomía declara **qué valores puede tomar cada dimensión clasificatoria**.

Ambas son necesarias y cumplen funciones distintas en el pipeline:

- La ontología dice que una `Sesion` tiene un atributo `tipo`.
- La taxonomía dice que ese `tipo` solo puede ser uno de: `descanso`, `recuperacion`, `rodaje`, `tirada_larga`, `tempo`, `intervalos`, `fartlek`.

Esa enumeración cerrada constituye un **vocabulario controlado**, y es lo que permite que la metadata de los chunks sea consistente y filtrable. Sin vocabulario controlado, un mismo concepto aparecería como "rodaje", "carrera suave" y "trote continuo" en distintos documentos, fragmentando el índice.

---

## 2. Dimensiones taxonómicas

Se declaran ocho dimensiones:

| Dimensión | Valores | Uso principal |
|---|---|---|
| `tipos_sesion` | 7 | Clasificación de sesiones y tipo de recomendación emitida |
| `zonas_intensidad` | 5 (Z1–Z5) | Clasificación fisiológica de la intensidad |
| `niveles_corredor` | 4 | Modulación de umbrales de progresión |
| `fases_entrenamiento` | 4 | Periodización del macrociclo |
| `distancias_objetivo` | 5 | Objetivos de competición |
| `lesiones_sobreuso` | 6 | Clasificación de lesiones frecuentes |
| `categorias_conocimiento` | 7 | **Metadata de chunks — filtrado del retriever** |
| `niveles_evidencia` | 4 | **Metadata de chunks — calificación de confianza** |

Las dos últimas son las que se propagan directamente al índice vectorial y por tanto tienen impacto operativo inmediato sobre la recuperación.

---

## 3. Jerarquía de intensidad

La dimensión más relevante conceptualmente. Las cinco zonas no son divisiones arbitrarias del rango de esfuerzo sino regiones delimitadas por dos umbrales fisiológicos:

```
        Z1 ── Z2 ──┤LT1├── Z3 ── Z4 ──┤LT2├── Z5
     recuperación   base   medio  umbral   VO2máx
```

| Zona | Posición | % FC máx | RPE | Adaptación principal |
|---|---|---|---|---|
| Z1 | Sub-LT1 | 50–60 | 1–2 | Flujo sanguíneo periférico |
| Z2 | Sub-LT1 | 60–75 | 3–4 | Densidad mitocondrial, capilarización |
| Z3 | Entre umbrales | 75–82 | 5–6 | Resistencia aeróbica intermedia |
| Z4 | Entre umbrales | 82–89 | 7–8 | Tolerancia y aclaramiento de lactato |
| Z5 | Sobre LT2 | 89–100 | 9–10 | Consumo máximo de oxígeno |

### Advertencia metodológica sobre los porcentajes

Los rangos de frecuencia cardíaca son **referenciales, no prescriptivos**. La variabilidad interindividual en la FC correspondiente a LT1 y LT2 es sustancial: dos corredores con idéntica FC máxima pueden tener umbrales situados en porcentajes muy diferentes de esa máxima.

La taxonomía documenta esta limitación explícitamente. Un sistema que asigne zonas a partir de FC máxima estimada por fórmulas de edad está introduciendo error apreciable, y debe comunicar esa incertidumbre en lugar de presentar rangos con precisión aparente.

### Nota sobre Z3

La taxonomía anota que Z3 es una zona "históricamente sobreutilizada por corredores recreativos" que "genera fatiga apreciable con estímulo adaptativo subóptimo". Esta anotación no es decorativa: es la base conceptual del modelo de distribución polarizada documentado en KB-003, y permite al sistema identificar un patrón de error accionable.

---

## 4. Niveles de corredor y modulación de umbrales

Esta dimensión codifica la decisión de diseño más consecuente de la taxonomía.

| Nivel | Volumen semanal | Experiencia | Incremento de referencia |
|---|---|---|---|
| Principiante | 0–20 km | 0–6 meses | **10 %** |
| Intermedio | 20–45 km | 6–24 meses | **15 %** |
| Avanzado | 45–80 km | 24–60 meses | **20 %** |
| Competitivo | 80–200 km | 60+ meses | **25 %** |

El campo `incremento_semanal_referencia_pct` **no es constante**. Esto implementa el axioma `AX-05` de la ontología y refleja el hallazgo documentado en KB-001: la evidencia sugiere que corredores bien entrenados toleran incrementos del orden del 20–25 % sin elevación proporcional del riesgo, mientras que el valor clásico del 10 % resulta más apropiado para novatos —no por su respaldo empírico, que es débil, sino porque la ausencia de experiencia previa es en sí misma un factor de riesgo documentado.

El nivel `principiante` incluye además una anotación de riesgo que el pipeline utiliza para enriquecer la consulta de recuperación (ver `construir_consulta()` en `src/rag/pipeline/rag_pipeline.py`).

---

## 5. Categorías de conocimiento

Vocabulario controlado que clasifica los documentos de la knowledge base. Cada valor corresponde a exactamente un documento curado:

| Categoría | Documento | Chunks |
|---|---|---|
| `carga_entrenamiento` | KB-001 | 13 |
| `zonas_fisiologicas` | KB-002 | 12 |
| `distribucion_intensidad` | KB-003 | 12 |
| `prevencion_lesiones` | KB-004 | 14 |
| `tapering` | KB-005 | 10 |
| `nutricion` | KB-006 | 10 |
| `recuperacion` | KB-007 | 11 |

Esta categoría viaja como metadata de cada chunk y habilita **búsqueda híbrida**: el retriever puede acotar el espacio de búsqueda por categoría antes de calcular similitud semántica.

```python
recuperar("cuánto debo consumir al entrenar", k=3, categoria="nutricion")
```

La utilidad inmediata es acotar consultas ambiguas. La utilidad prospectiva es mayor: en el Sprint 3, cada agente especializado consultará únicamente su dominio de conocimiento mediante este mismo filtro.

---

## 6. Niveles de evidencia

Dimensión que califica la solidez del respaldo científico de cada documento.

| Nivel | Definición |
|---|---|
| `alto` | Metaanálisis o revisiones sistemáticas con hallazgos consistentes |
| `moderado` | Estudios primarios de calidad razonable, con heterogeneidad o limitaciones |
| `limitado` | Hallazgos preliminares, conflictivos o de muestra reducida |
| `practica_consolidada` | Ampliamente adoptado en la práctica pero con soporte débil o parcialmente refutado |

### La categoría `practica_consolidada`

Esta categoría se introdujo específicamente durante la curación documental, al constatar que la regla del 10 % —codificada de forma rígida en el sistema previo al sprint— no encaja en ninguna de las tres categorías convencionales. No es evidencia alta, moderada ni limitada: es una práctica ampliamente difundida cuyo respaldo empírico ha sido cuestionado.

Disponer de esta categoría permite que la knowledge base documente el conocimiento **tal como es**, incluyendo su grado de solidez, en lugar de presentar toda afirmación con autoridad uniforme. El nivel de evidencia se propaga al contexto del prompt, de modo que el agente puede calificar la confianza de sus recomendaciones —campo `confianza` de la respuesta.

---

## 7. Propagación al índice vectorial

Cada chunk indexado incorpora los siguientes campos derivados de la taxonomía:

```json
{
  "doc_id": "KB-001",
  "titulo": "Carga de entrenamiento y progresión del volumen",
  "categoria": "carga_entrenamiento",
  "nivel_evidencia": "moderado",
  "entidades_ontologia": "CargaEntrenamiento; Sesion; Corredor; Lesion",
  "conceptos_taxonomia": "niveles_corredor; tipos_sesion",
  "seccion": "La regla del 10%: origen, adopción y evidencia",
  "archivo": "carga-entrenamiento-progresion.md",
  "chunk_index": 4
}
```

### Restricción técnica

ChromaDB admite en metadata únicamente valores de tipo `str`, `int`, `float` y `bool`. Los campos que en el front-matter son listas —`referencias`, `entidades_ontologia`, `conceptos_taxonomia`— se aplanan a cadena con separador `"; "` durante el chunking.

Esta decisión tiene un costo conocido: `referencias` ocupa aproximadamente 700 caracteres y se replica en cada chunk del documento. A la escala actual (82 chunks) el impacto es despreciable. En un corpus de mayor tamaño correspondería normalizar, manteniendo únicamente `doc_id` en el chunk y resolviendo las referencias contra un registro documental externo. Se documenta como decisión consciente, no como omisión.

---

## 8. Trazabilidad al código

| Elemento de la taxonomía | Implementación |
|---|---|
| Definición completa | `src/knowledge/taxonomy/wellness_taxonomy.yaml` |
| Declaración por documento | Front-matter YAML de cada archivo en `data/knowledge_base/` |
| Aplanado a metadata | `src/knowledge/chunking/chunker.py` → `CAMPOS_METADATA`, `CAMPOS_LISTA` |
| Filtrado por categoría | `src/rag/retriever/retriever.py` → `recuperar(categoria=...)` |
| Nivel de evidencia en el prompt | `src/rag/pipeline/rag_pipeline.py` → `construir_contexto()` |
| Modulación por nivel de corredor | `src/rag/pipeline/rag_pipeline.py` → `construir_consulta()` |
