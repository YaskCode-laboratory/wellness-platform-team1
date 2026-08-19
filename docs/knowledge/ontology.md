# Ontología Ligera del Dominio Wellness

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Archivo fuente: [`src/knowledge/ontology/wellness_ontology.yaml`](../../src/knowledge/ontology/wellness_ontology.yaml)

---

## 1. Propósito

Una ontología ligera define **qué existe en el dominio y cómo se relaciona**, sin la carga formal de una ontología completa en OWL. En este proyecto cumple tres funciones concretas:

1. **Guiar la curación documental.** Los documentos de la knowledge base se organizan alrededor de las entidades y relaciones declaradas aquí, evitando cobertura arbitraria.
2. **Enriquecer los chunks con metadata estructurada.** Cada fragmento indexado declara a qué entidades del modelo se refiere.
3. **Habilitar filtrado semántico.** El retriever puede acotar la búsqueda por categoría o nivel de evidencia antes de calcular similitud.

Se eligió el formato YAML en lugar de OWL/RDF por una razón práctica: el modelo debe ser legible y editable por el equipo, y consumible directamente por código Python sin capa de razonamiento adicional. El alcance del sprint no requiere inferencia sobre la ontología, sino representación explícita del dominio.

---

## 2. Entidades

Se declaran nueve entidades. La distinción relevante es entre entidades **observadas** (registradas por el usuario), **derivadas** (calculadas por el sistema) y **generadas** (producidas por el agente).

| Entidad | Naturaleza | Rol en el dominio |
|---|---|---|
| `Corredor` | Observada | Sujeto central. Todas las recomendaciones se personalizan respecto a él |
| `Sesion` | Observada | Unidad atómica de entrenamiento registrada |
| `Objetivo` | Observada | Meta declarada por el corredor |
| `CargaEntrenamiento` | Derivada | Cuantificación del estrés acumulado. Entidad clave para evaluación de riesgo |
| `ZonaIntensidad` | Derivada | Rango fisiológico delimitado por umbrales de lactato |
| `FaseEntrenamiento` | Derivada | Periodo del macrociclo con objetivo fisiológico propio |
| `Lesion` | Observada / Predicha | Condición que interrumpe el entrenamiento |
| `Recomendacion` | Generada | Salida del sistema inteligente |
| `FuenteConocimiento` | Referencial | Documento curado que fundamenta una recomendación |

### 2.1 Entidades destacadas

**`CargaEntrenamiento`** es la entidad de mayor densidad conceptual. Declara cinco atributos que representan formas alternativas de cuantificar el mismo fenómeno:

- `carga_aguda` — volumen de los últimos 7 días
- `carga_cronica` — media móvil de 28 días
- `acwr` — ratio agudo:crónico
- `variacion_semanal_pct` — incremento respecto a la semana previa
- `pico_sesion_pct` — incremento de la sesión individual más larga

La coexistencia de los cinco es deliberada y documentada: no son redundantes sino que tienen **niveles de respaldo empírico distintos**. El atributo `variacion_semanal_pct` corresponde a la clásica regla del 10%, cuyo soporte científico es notablemente más débil que el de `acwr` y `pico_sesion_pct`. Modelar los tres permite al sistema razonar con el indicador apropiado en lugar de con el más difundido.

**`FuenteConocimiento`** no existía en el modelo previo al Sprint 1. Su incorporación es lo que hace posible la trazabilidad: toda recomendación puede auditarse hasta el documento que la sustenta.

---

## 3. Relaciones

Se declaran once relaciones. Las de mayor peso conceptual:

| Relación | Cardinalidad | Observación |
|---|---|---|
| `Corredor` **ejecuta** `Sesion` | 1:N | Relación base de registro |
| `Sesion` **se_desarrolla_en** `ZonaIntensidad` | N:1 | Determina la adaptación fisiológica producida |
| `Sesion` **acumula** `CargaEntrenamiento` | N:1 | Agregación temporal |
| `CargaEntrenamiento` **incrementa_riesgo_de** `Lesion` | 1:N | **Relación causal central del dominio** |
| `Lesion` **predispone_a** `Lesion` | N:N | Lesión previa es el factor de riesgo con mejor evidencia |
| `Corredor` **modula** `CargaEntrenamiento` | 1:1 | El nivel modifica los umbrales tolerables |
| `Recomendacion` **fundamentada_en** `FuenteConocimiento` | N:N | **Materializa el aporte de RAG** |

### 3.1 Las dos relaciones críticas

**`CargaEntrenamiento → incrementa_riesgo_de → Lesion`** es la relación que justifica la existencia del sistema. Si la carga no se relacionara causalmente con el riesgo de lesión, un agente de recomendación de entrenamiento carecería de propósito preventivo.

**`Recomendacion → fundamentada_en → FuenteConocimiento`** es la arista que **no existía antes de este sprint**. En la arquitectura previa las recomendaciones se generaban sin vínculo a conocimiento curado: el modelo respondía desde su conocimiento paramétrico, sin posibilidad de auditar el fundamento. Introducir esta relación es, en términos del modelo conceptual, la transformación completa que produjo el Sprint 1.

**`Corredor → modula → CargaEntrenamiento`** merece mención porque codifica una decisión que contradice la práctica común: los umbrales de progresión no son universales. Un corredor competitivo tolera incrementos sustancialmente mayores que un principiante, y el modelo lo representa explícitamente en lugar de aplicar un valor único.

---

## 4. Axiomas

La ontología declara cinco axiomas de inferencia. Constituyen **conocimiento simbólico explícito**, complementario al conocimiento distribuido que reside en los embeddings.

| ID | Enunciado | Tipo | Evidencia |
|---|---|---|---|
| `AX-01` | Si ACWR > 1.5 el riesgo se considera elevado y la recomendación prioriza recuperación | Regla de riesgo | Moderada |
| `AX-02` | Ante historial de lesión previa, todo umbral de incremento se reduce respecto al valor de referencia | Regla de riesgo | **Alta** |
| `AX-03` | Un incremento de volumen sub-LT1 no equivale en estrés a un incremento equivalente sobre LT2 | Regla de equivalencia | **Alta** |
| `AX-04` | Si quedan ≤ 3 semanas para la meta, la fase es tapering: volumen −41% a −60%, intensidad constante | Regla de periodización | **Alta** |
| `AX-05` | El umbral de incremento tolerable es función del nivel; no existe valor único poblacional | Regla de personalización | Moderada |

### 4.1 Por qué conviven axiomas y RAG

Una pregunta legítima es por qué mantener reglas simbólicas si el sistema ya recupera conocimiento documental. La respuesta es que resuelven problemas distintos:

- Los **axiomas** son deterministas, auditables y no dependen de la calidad de la recuperación. `AX-04` puede evaluarse con aritmética de fechas y no admite ambigüedad.
- El **conocimiento recuperado** aporta matiz, contexto y fundamento, pero está sujeto a la calidad de la consulta y del corpus.

El sistema resultante es **híbrido por diseño**: articula representación simbólica y representación distribuida en lugar de sustituir una por la otra. Esta convivencia es un objetivo explícito del Tema 1 del programa —Representación del Conocimiento— y no un compromiso de implementación.

---

## 5. Limitación identificada: brecha entre ontología e implementación

Durante la integración se detectó una discrepancia que se documenta por transparencia metodológica.

La ontología modela `Objetivo` con los atributos `distancia_meta` y `fecha_meta`, correspondientes a un objetivo de competición ("media maratón el 15 de octubre"). El modelo de datos implementado en la plataforma define los objetivos de forma distinta:

```
goals: { kmMeta: 30, tipo: "semanal", activo: true, userId: ... }
```

Es decir, **metas de volumen periódico, no objetivos de competición con fecha**.

### Consecuencias

1. `FaseEntrenamiento` no puede derivarse: sin fecha meta no hay distancia temporal contra la cual calcular la fase.
2. El axioma `AX-04` (tapering) no es evaluable con el esquema actual.
3. El documento KB-005 sobre tapering permanece en la knowledge base pero su conocimiento no es aplicable a los datos reales de la plataforma.

### Alternativas de resolución

| Opción | Implicación |
|---|---|
| **Extender el modelo de objetivos** de la aplicación para admitir objetivos de competición con fecha | Habilita fase, tapering y `AX-04`. Requiere cambios en frontend, backend y esquema de datos |
| **Acotar la ontología** al modelo de datos vigente | Coherencia inmediata, pero renuncia a un dominio de conocimiento con evidencia alta |

Se propone la primera opción como elemento de backlog para el Sprint 2, dado que el conocimiento de periodización tiene respaldo empírico sólido y su ausencia limita el valor del sistema.

---

## 6. Trazabilidad al código

| Elemento de la ontología | Implementación |
|---|---|
| Entidades y atributos | `src/knowledge/ontology/wellness_ontology.yaml` |
| Propagación como metadata | `src/knowledge/chunking/chunker.py` → `_construir_metadata()` |
| Filtrado por entidad | `src/rag/retriever/retriever.py` → parámetros `categoria`, `nivel_evidencia` |
| `Recomendacion.fuentes` | `src/rag/pipeline/rag_pipeline.py` → `validar_fuentes()` |
| Trazabilidad de `FuenteConocimiento` | Campo `_rag.chunks_recuperados` de la respuesta |
