# Informe del Sprint 1

## Ingeniería del Conocimiento y Sistemas RAG

**Asignatura:** Sistemas Inteligentes
**Programa:** Maestría en Tecnologías de Información y Comunicación — Universidad del Zulia
**Docente:** Dra. Yaskelly Yedra
**Equipo 1:** José Francisco Urdaneta Sánchez · Julio César Matute
**Fecha:** agosto de 2026

---

## 1. Objetivo del sprint

> *Transformar el agente inicial desarrollado en la asignatura ISBD en un sistema inteligente basado en conocimiento, mediante la aplicación de técnicas de Ingeniería del Conocimiento, Representación del Conocimiento y Retrieval-Augmented Generation.*

---

## 2. Punto de partida

La plataforma heredada de Ingeniería del Software y Bases de Datos disponía de un agente funcional con arquitectura cloud-native: React PWA, microservicios FastAPI sobre Cloud Run, Firestore y Gemini 2.5 Flash vía Vertex AI.

Su limitación era el tratamiento del conocimiento. El único conocimiento de dominio residía en una regla codificada rígidamente dentro de `build_prompt()`: no incrementar el volumen semanal más de un 10 %. Todo lo demás procedía del conocimiento paramétrico del modelo, sin fuentes verificables ni posibilidad de auditar el fundamento de las recomendaciones.

---

## 3. Trabajo realizado

### 3.1 Migración a la estructura del repositorio

Reorganización del proyecto a la estructura definida por la cátedra: `src/agents/`, `src/rag/`, `src/knowledge/`, `prompts/`, `data/`, `docs/`, `scripts/`, `tests/`. Los microservicios previos se consolidaron en una aplicación FastAPI única con separación por capas.

### 3.2 Modelo de conocimiento

| Artefacto | Contenido |
|---|---|
| Ontología ligera | 9 entidades, 11 relaciones, 5 axiomas de inferencia |
| Taxonomía | 8 dimensiones con vocabulario controlado |
| Mapa de dominio | Delimitación, jerarquías y diagramas conceptuales |

La ontología incorpora la entidad `FuenteConocimiento` y la relación `Recomendacion → fundamentada_en → FuenteConocimiento`, inexistentes en el modelo previo. Esa arista es, en términos conceptuales, la transformación completa que produjo el sprint.

Los cinco axiomas constituyen conocimiento simbólico explícito que convive con el conocimiento distribuido de los embeddings. El sistema resultante es **híbrido por diseño**: articula ambas formas de representación en lugar de sustituir una por otra.

### 3.3 Base de conocimiento

Siete documentos curados, uno por categoría taxonómica, con front-matter declarando categoría, nivel de evidencia y referencias bibliográficas verificables.

| ID | Documento | Evidencia | Chunks |
|---|---|---|---|
| KB-001 | Carga de entrenamiento y progresión | Moderada | 13 |
| KB-002 | Zonas de intensidad y umbrales fisiológicos | Alta | 12 |
| KB-003 | Distribución de intensidad y polarizado | Alta | 12 |
| KB-004 | Prevención de lesiones por sobreuso | Moderada | 14 |
| KB-005 | Tapering y puesta a punto | Alta | 10 |
| KB-006 | Nutrición para el corredor | Alta | 10 |
| KB-007 | Recuperación y sueño | Moderada | 11 |

**Total: 82 chunks.**

### 3.4 Pipeline RAG

| Etapa | Implementación |
|---|---|
| Chunking | Híbrido estructural: corte por encabezados, subdivisión condicional a 800 caracteres, solapamiento de 120, prefijo contextual |
| Embeddings | `text-embedding-004` (768 dim), diferenciación `RETRIEVAL_DOCUMENT` / `RETRIEVAL_QUERY`, batching por presupuesto de tokens |
| Indexación | ChromaDB persistente, espacio coseno, idempotente por `doc_id` |
| Recuperación | Top-3 con filtrado opcional por categoría y nivel de evidencia |
| Generación | Gemini 2.5 Flash, temperatura 0.2, salida JSON, prompt con 8 instrucciones de anclaje |
| Validación | Verificación programática de citas contra el conjunto recuperado |

### 3.5 Modo dual y comparativa

Implementación adicional no requerida por el sprint: el agente admite `mode="legacy"` y `mode="rag"`, con endpoint `POST /agent/{userId}/compare` que ejecuta ambas arquitecturas sobre el mismo estado y devuelve las dos respuestas con trazabilidad y latencias.

### 3.6 Evaluación

Conjunto de referencia de 18 casos redactados en registro de usuario, cubriendo las siete categorías. Métricas implementadas: Precision@k, Recall@k, MRR y Hit rate.

---

## 4. Resultados

### Recuperación

| Métrica | k = 5 | k = 3 |
|---|---|---|
| Precision@k | 0.767 | **0.815** |
| Recall@k | 0.944 | 0.944 |
| MRR | 0.944 | 0.944 |
| Hit rate | 17/18 | 17/18 |

### Generación

| Indicador | Valor |
|---|---|
| Precisión de citación | 1.000 tras corrección del prompt |
| Citas alucinadas detectadas | 1 caso, descartado automáticamente |
| Faithfulness cuantitativa | No implementada |

---

## 5. Hallazgos

### 5.1 La regla del 10 % carece de respaldo empírico sólido

La revisión de fuentes reveló que la regla codificada en el sistema previo:

- No procede de un estudio fundacional; se popularizó en literatura de divulgación de los años 80
- En un estudio con **486 corredores novatos** no produjo diferencias en prevalencia de lesión (21 %) frente a un programa estándar
- No mostró diferencia significativa frente a incrementos del 24 %
- Trata todo volumen como equivalente, ignorando la zona de intensidad

La evidencia contemporánea señala como mejores predictores el **ratio de carga aguda:crónica** y el **control de picos en sesión individual**.

Este hallazgo motivó la introducción del nivel de evidencia `practica_consolidada` en la taxonomía, categoría para conocimiento ampliamente adoptado pero débilmente sustentado.

### 5.2 La comparación empírica confirma la mejora

Corredor intermedio con incremento del 18.4 %:

| | legacy | rag |
|---|---|---|
| Evaluación | Alerta por superar el 10 % | Dentro de lo tolerable para nivel intermedio |
| Referencia | Regla fija | *"incrementos cercanos al 20-25 % pueden ser tolerados"* |
| Redirección | — | *"monitoreando la carga de cada sesión individual"* |
| Fuentes | Ninguna | KB-001 |

La modulación por nivel no está programada: procede del conocimiento recuperado.

En el caso de un corredor principiante con incremento del 46 %, el modo legacy respondió *"excelente comienzo"* sin emitir alerta, mientras el modo RAG identificó los factores de riesgo documentados y explicó el mecanismo causal.

### 5.3 k = 3 supera a k = 5

Recall, MRR y hit rate idénticos con precisión superior. Los fragmentos cuarto y quinto no aportaban documentos relevantes adicionales. Decisión de configuración derivada de medición.

### 5.4 Las citas alucinadas requieren defensa en código

El modelo citó KB-005 sin haberlo recibido. La instrucción de prompt redujo la incidencia; la validación programática la eliminó.

Corolario: limpiar el array de fuentes no protegió el texto libre del campo `fundamento`. Cada superficie de citación requiere su propia defensa.

### 5.5 La consulta condiciona la recuperación tanto como el índice

Una versión previa de la síntesis de consulta incorporaba *"tapering"* de forma incondicional, provocando que 3 de 5 fragmentos procedieran del documento equivocado. El retriever funcionaba correctamente; la consulta estaba mal construida.

### 5.6 La brecha de registro lingüístico es el modo de falla dominante

El único caso fallido (EV-16) enfrenta el registro coloquial del usuario —*"como muy poco"*— al registro técnico del corpus —*"disponibilidad energética"*. Se conservó documentado en lugar de corregirse: ajustar el corpus a las consultas de evaluación sería metodológicamente cuestionable.

### 5.7 Brecha entre ontología e implementación

La ontología modela `Objetivo` con distancia y fecha meta. El modelo de datos de la plataforma define objetivos como metas de volumen periódico (`kmMeta`, `tipo`), sin fecha de competición.

Consecuencia: `FaseEntrenamiento` no es derivable, el axioma `AX-04` no es evaluable y el conocimiento de KB-005 sobre tapering no es aplicable a los datos reales.

Se propone extender el modelo de objetivos de la aplicación como elemento de backlog.

---

## 6. Cumplimiento del entregable

| Componente exigido | Estado | Ubicación |
|---|---|---|
| Mapa de conocimiento del dominio | ✅ | `docs/knowledge/domain-map.md` |
| Ontología ligera | ✅ | `src/knowledge/ontology/` · `docs/knowledge/ontology.md` |
| Taxonomía del dominio | ✅ | `src/knowledge/taxonomy/` · `docs/knowledge/taxonomy.md` |
| Curación documental | ✅ | `data/knowledge_base/` · `docs/rag/document-curation.md` |
| Estrategia de chunking | ✅ | `docs/rag/chunking-strategy.md` |
| Estrategia de embeddings | ✅ | `docs/rag/embeddings-strategy.md` |
| Base vectorial | ✅ | `docs/rag/vector-database.md` |
| Ingesta documental | ✅ | `scripts/ingestion/index_knowledge_base.py` |
| Indexación | ✅ | `src/rag/vector_store/store.py` |
| Recuperación | ✅ | `src/rag/retriever/retriever.py` |
| Generación de respuestas | ✅ | `src/rag/generation/` · `src/rag/pipeline/` |
| Métricas de recuperación | ✅ | `docs/evaluation/retrieval-metrics.md` |
| Casos de prueba | ✅ | `docs/evaluation/test-cases.md` |
| Evaluación de calidad de respuestas | ⚠️ Parcial | `docs/evaluation/response-quality.md` |

**Observación sobre el componente parcial.** La evaluación de calidad de respuestas cubre precisión de citación —cuantitativa y automatizada— y comparación cualitativa legacy/RAG sobre casos documentados. No incluye faithfulness cuantitativa mediante LLM evaluador, cuya implementación se pospuso por restricción de tiempo. Se documenta como carencia reconocida en lugar de presentarse como completa.

---

## 7. Herramientas empleadas

| Categoría | Herramienta | Uso |
|---|---|---|
| Lenguaje | Python 3.11 | Implementación completa |
| Framework web | FastAPI, Uvicorn | API REST |
| Fragmentación | `langchain-text-splitters` | Subdivisión por tamaño |
| Embeddings | Vertex AI `text-embedding-004` | Vectorización |
| Base vectorial | ChromaDB 0.5.23 | Índice y búsqueda |
| Generación | Gemini 2.5 Flash vía Vertex AI | Recomendaciones |
| Persistencia | Cloud Firestore | Datos de usuario |
| Modelado | Mermaid | Diagramas de la documentación |
| Control de versiones | GitHub | Repositorio y flujo de PR |

**Decisión sobre LangChain.** Se empleó únicamente `langchain-text-splitters` en lugar del ecosistema completo. La causa inmediata fue un conflicto irresoluble de dependencias entre `firebase-admin` y `langchain-google-vertexai` sobre `google-cloud-storage`. La causa de fondo es que el paquete descartado envolvía un SDK ya operativo en el proyecto; eliminarlo redujo dependencias y aumentó la transparencia de las llamadas.

**Decisión sobre ChromaDB frente a FAISS.** Persistencia nativa, filtrado por metadata integrado e inspeccionabilidad. La ventaja de rendimiento de FAISS es irrelevante a escala de 82 fragmentos.

---

## 8. Limitaciones reconocidas

| Limitación | Naturaleza |
|---|---|
| Faithfulness no implementada | Evaluación incompleta de la etapa de generación |
| Conjunto de referencia de 18 casos | Sin potencia estadística para comparaciones finas |
| Anotación por el equipo curador | Riesgo de sesgo de confirmación |
| Latencia con una sola muestra | No permite conclusión sobre coste del RAG |
| Sin pruebas automatizadas | `tests/` permanece vacío |
| Corpus de 7 documentos | Cobertura acotada del dominio |
| Evaluación sobre consultas directas | El agente usa consultas sintetizadas, no medidas |
| `GCP_PROJECT` disperso en 4 módulos | Deuda técnica de configuración |
| SDK Vertex AI deprecado | Retirada anunciada para junio de 2026 |

---

## 9. Trabajo pendiente para el Sprint 2

**Derivado de este sprint**

- Evaluación de faithfulness y answer relevance con LLM evaluador
- Pruebas automatizadas y de regresión sobre el conjunto de referencia
- Expansión de consulta para mitigar la brecha de registro lingüístico
- Extensión del modelo de objetivos para admitir fechas de competición
- Centralización de configuración y migración a `google-genai`

**Del programa de la asignatura**

El Sprint 2 aborda Agentes Inteligentes Modernos: memoria conversacional, tool calling, patrón ReAct. La arquitectura resultante de este sprint lo admite sin reestructuración: `BaseAgent` está definido como clase abstracta y la capa de conocimiento es independiente de la lógica del agente.

---

## 10. Conclusión

El sprint cumplió su objetivo: el agente pasó de operar con una regla codificada rígidamente a fundamentar sus recomendaciones en un corpus curado, con recuperación semántica, citación validada y trazabilidad completa.

La evidencia de mejora está documentada con casos concretos y métricas reproducibles. La recuperación alcanza recall de 0.944 con MRR de 0.944 sobre el conjunto de referencia, y la comparación directa entre arquitecturas muestra diferencias sustantivas en la calidad de las recomendaciones.

Los hallazgos más valiosos del sprint no son los resultados favorables sino los problemas diagnosticados: la debilidad empírica de la regla que el sistema aplicaba, la brecha de registro entre usuario y corpus, la propensión del modelo a inventar citas y la dependencia de la recuperación respecto a la calidad de la consulta. Todos quedan documentados con su análisis y remedios propuestos.

La carencia principal es la evaluación cuantitativa de la etapa de generación, que se declara explícitamente en lugar de presentarse como resuelta.
