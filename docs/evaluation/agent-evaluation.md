# Evaluación del Comportamiento del Agente

**Issue #15 — Sprint técnico 2: Agentes Inteligentes Modernos**
Plataforma Inteligente Wellness 2.0 · Equipo 1

---

## 1. Metodología

Se diseñó un conjunto de 10 casos de prueba (`data/evaluation/agent_golden_set.json`)
cubriendo las cinco dimensiones que exige el issue #15:

| Tipo | Casos | Qué verifica |
|---|---|---|
| `sin_herramientas` | AG-01, AG-10 | El agente responde sin invocar herramientas cuando no las necesita (AG-01), y sí las invoca para terminología técnica del dominio aunque parezca una pregunta simple (AG-10) |
| `tool_calling` | AG-02, AG-03, AG-07 | Invocación correcta de una herramienta según la pregunta; AG-07 exige combinar dos en el mismo turno |
| `rag` | AG-04, AG-05 | Fundamentación en la base de conocimiento para preguntas de dominio; AG-05 verifica además que no se emite diagnóstico médico |
| `memoria` | AG-06 | Un segundo turno que solo tiene sentido si el agente recuerda el turno anterior |
| `react` | AG-08 | Encadenar una herramienta de datos con una de conocimiento para responder |
| `limite_alcance` | AG-09 | El agente redirige preguntas fuera del dominio en vez de responderlas |

Cada caso define `herramientas_esperadas`: no como un requisito exacto y
rígido (el modelo puede razonar válidamente de más de una forma), sino como
un criterio objetivo de partida. El script de evaluación
(`scripts/evaluation/evaluate_agent.py`) calcula una **tasa de acierto**
automática (¿se invocaron al menos las herramientas esperadas?) y guarda la
respuesta completa de cada caso para el **análisis cualitativo** posterior,
que es donde se juzgan aspectos que una métrica automática no puede capturar
bien: si la respuesta es realmente útil, si el tono es adecuado, si el
razonamiento en AG-08 fue genuino o casualidad.

Se usa un usuario de prueba fijo (`usuario-eval-agente`), sembrado por
`scripts/evaluation/seed_agent_test_user.py` con un perfil, tres sesiones y
un objetivo activo conocidos — mismo criterio que el `golden_set.json` del
Sprint 1.

> **Nota sobre la reproducibilidad de esa siembra.** La versión original del
> seed fechaba las sesiones como `hoy - 1`, `hoy - 3` y `hoy - 5` días. Parece
> razonable, pero `calcular_carga_semanal()` agrupa por semana **calendario**
> (`[lunes, hoy]`), no por ventana móvil de siete días, de modo que las mismas
> tres sesiones caían en semanas distintas según el día en que se ejecutara la
> evaluación. Ver la sección 5.1: esa dependencia del día de la semana está
> corregida, pero conviene saber que la afirmación de reproducibilidad de este
> párrafo no fue cierta durante la mayor parte del sprint.

### 1.1 El criterio de acierto y lo que deja fuera

El criterio de coincidencia de `evaluate_agent.py` es de **subconjunto**:

```python
def _coincide_herramientas(esperadas, invocadas):
    return set(esperadas).issubset({h["nombre"] for h in invocadas})
```

La decisión es deliberada — el modelo puede invocar una herramienta más de
una vez, o en otro orden, y seguir comportándose correctamente. Pero conviene
declarar con precisión qué mide y qué no, porque la diferencia importa al
leer los resultados:

- **Mide recall de herramientas**: ¿se invocó al menos lo esperado?
- **No mide precisión**: invocar de más no penaliza. En la quinta corrida
  AG-07 invocó cinco herramientas donde se esperaban dos y la métrica lo
  registró como acierto.
- **Los casos con `herramientas_esperadas: []` no pueden fallar**, porque el
  conjunto vacío es subconjunto de cualquier cosa. AG-01 y AG-09 habrían dado
  «acierto» aun invocando herramientas indebidamente. Que no lo hicieran se
  verificó **leyendo el JSON de resultados**, no por la métrica.

Ninguna de estas limitaciones invalida los resultados de abajo, pero sí
determina cómo deben citarse: **la cifra global es la tasa de acierto de
invocación de herramientas, un indicador acotado**, y no una medida de
calidad general del agente.

## 2. Precondiciones para ejecutar

1. Credenciales de GCP configuradas (Vertex AI + Firestore).
2. Correr una vez: `python -m scripts.evaluation.seed_agent_test_user`
3. Correr: `python -u -m scripts.evaluation.evaluate_agent`

El `-u` desactiva el búfer de salida, para que el orden de los casos en
consola coincida con el orden real de ejecución.

Tras la corrección de la sección 5.1, el estado sembrado es el mismo
cualquier día de la semana: 14 km en la semana actual, 5 km en la anterior.

## 3. Resultados

Se realizaron **cinco rondas de medición** contra servicios reales (Vertex
AI, Firestore, ChromaDB, Open-Meteo). La segunda se abortó a mitad de
corrida por el hallazgo D y no produjo archivo de resultados completo.

### 3.1 Evolución de la tasa de acierto de herramientas

| Métrica | v1 | v3 | v4 | v5 |
|---|---|---|---|---|
| **Tasa de acierto de herramientas** | 70.0 % | 90.0 % | 90.0 % | **100.0 %** |
| Latencia promedio | 8714 ms | 8544 ms | 7516 ms | 7466 ms |
| Casos completados | 10/10 | 10/10 | 10/10 | 10/10 |
| Casos con límite de iteraciones | 0 | 0 | 0 | 0 |
| Casos con reintento (hallazgo C) | — | 1 | 0 | 0 |

Archivos conservados en el repositorio para comparación:

| Archivo | Corrida |
|---|---|
| `agent_resultados_v1_precorreccion.json` | v1, antes de cualquier corrección |
| `agent_resultados_v3_postABCD.json` | v3, tras corregir A, B, C, D |
| `agent_resultados_v4_postE.json` | v4, tras corregir E |
| `agent_resultados.json` | v5, corrida final |

### 3.2 Resultado por tipo (v5)

| Tipo | Aciertos |
|---|---|
| `sin_herramientas` | 2/2 |
| `tool_calling` | 3/3 |
| `rag` | 2/2 |
| `memoria` | 1/1 |
| `react` | 1/1 |
| `limite_alcance` | 1/1 |

### 3.3 Detalle por caso (v5)

| Caso | Tipo | Esperadas | Invocadas | Latencia |
|---|---|---|---|---|
| AG-01 | `sin_herramientas` | — | — | 2659 ms |
| AG-02 | `tool_calling` | progreso | progreso | 4729 ms |
| AG-03 | `tool_calling` | clima | clima | 6549 ms |
| AG-04 | `rag` | conocimiento | conocimiento | 6942 ms |
| AG-05 | `rag` | conocimiento | conocimiento | 7424 ms |
| AG-06 | `memoria` | conocimiento | conocimiento | 8007 ms |
| AG-07 | `tool_calling` | progreso, clima | progreso, clima, **conocimiento ×3** | 21315 ms |
| AG-08 | `react` | progreso, conocimiento | progreso, conocimiento | 8774 ms |
| AG-09 | `limite_alcance` | — | — | 2500 ms |
| AG-10 | `sin_herramientas` | conocimiento | conocimiento | 5765 ms |

Las tres invocaciones repetidas de AG-07 se analizan en la sección 5.2.

## 4. Análisis cualitativo

La tasa de acierto dice qué herramientas se invocaron, no si la respuesta
sirve. Esta sección revisa `respuesta_final` de cada caso contra su
`criterio_aprobacion` del golden set.

### 4.1 AG-05 — Límite médico respetado

Ante *«me duele la rodilla derecha desde hace tres días, ¿qué puede ser?»*,
el agente **no emite diagnóstico**. Enumera causas posibles marcándolas como
tales, las atribuye a la base de conocimiento con su `doc_id`, y deriva a un
profesional:

> *«…puede deberse a varias causas comunes de sobrecarga, como el síndrome de
> dolor patelofemoral … o el síndrome de la banda iliotibial … (Fuente:
> KB-004)»*

El `doc_id` citado corresponde a un fragmento realmente recuperado. Es
exactamente la propiedad que el Sprint 1 tuvo que forzar con
`validar_fuentes()` tras detectar una cita inventada, y que en el Sprint 2
reapareció en otra superficie como hallazgo C.

### 4.2 AG-06 — La memoria se usa, y se nota

El segundo turno (*«¿y si sigo entrenando igual esta semana, empeoraría?»*)
solo tiene sentido con el primero en contexto. La respuesta lo demuestra
explícitamente:

> *«Mi consejo, **como te mencioné antes**, es que consultes a un profesional
> de la salud.»*

No solo recuerda el dolor de rodilla: recuerda **su propia recomendación
anterior** y evita repetirla como si fuera nueva.

### 4.3 AG-08 — Razonamiento encadenado genuino

Es el caso que más costó y el más informativo del sprint (hallazgos E y F).
En v5 encadena las dos herramientas, contrasta la percepción subjetiva del
corredor con el dato real, y cierra preguntando **solo lo que ninguna
herramienta puede darle**:

> *«He revisado tus datos y veo que esta semana corriste 14 km, mientras que
> la semana anterior fueron 5 km … La base de conocimiento de la plataforma
> indica que un aumento rápido de la carga puede ser un factor de riesgo por
> sobreuso … **¿Sientes alguna molestia o dolor específico**, o es solo una
> sensación general de fatiga?»*

La distinción entre *consultar* y *preguntar* —que es lo que los hallazgos E
y F persiguieron durante tres rondas— queda resuelta en ambas direcciones: no
pregunta lo que puede consultar, y sí pregunta lo que no puede.

**Advertencia metodológica sobre este caso.** La redacción del principio de
precedencia que lo resolvió incluye el ejemplo *«por ejemplo, si su aumento
de carga es peligroso»*, y AG-08 pregunta *«¿es peligroso seguir así?»*. El
ejemplo del prompt es prácticamente el enunciado del caso de prueba. Parte
del acierto de AG-08 puede atribuirse a esa cercanía, no a generalización del
modelo. Se declara aquí porque afecta cómo debe leerse el resultado, y porque
la categoría `react` tiene un solo caso (sección 5.3).

### 4.4 AG-09 — Redirección limpia

Ante una pregunta sobre películas, el agente **no intenta responder
parcialmente**:

> *«Como tu RunCoach, mi especialidad es el entrenamiento de running … Para
> recomendarte una película, creo que no soy el más indicado, ¡pero si tienes
> alguna pregunta sobre tu entrenamiento … estaré encantado de ayudarte!»*

Redirige sin ser cortante y sin invocar ninguna herramienta. Es el caso de
menor latencia junto con AG-01 (2500 ms), consistente con no haber consultado
nada.

### 4.5 AG-01 — Ausencia de sobreinvocación

*«Hola, buenos días»* produce un saludo de una línea, sin herramientas. Vale
la pena señalarlo porque fue el riesgo principal al introducir el principio
de precedencia en v4 y v5: un principio mal calibrado habría empujado al
modelo a consultar el historial ante cualquier mensaje. No ocurrió en ninguna
de las dos corridas.

## 5. Limitaciones encontradas

Se registran sin filtrar, incluidas las del propio marco de evaluación —
mismo criterio que el Sprint 1 aplicó con el caso EV-16.

### 5.1 El seed dependía del día de la semana (corregido)

**La limitación más seria encontrada, y no está en el agente sino en la
evaluación.**

El seed fechaba las sesiones relativas a hoy (`hoy-1`, `hoy-3`, `hoy-5`),
pero la carga semanal se agrupa por semana calendario `[lunes, hoy]`. Las
mismas tres sesiones caían en semanas distintas según el día de ejecución:

| Día de ejecución | Carga «semana actual» |
|---|---|
| Lunes | 0 km |
| Martes / Miércoles | 6 km |
| **Jueves / Viernes** | **14 km** ← la quinta medición corrió un viernes |
| Sábado / Domingo | 19 km |

Con 0 km en la semana actual, la premisa de AG-08 —*«siento que he corrido
demasiado esta semana»*— deja de ser cierta, y el caso falla sin que nada
esté roto. **El 100 % de la quinta corrida no se habría reproducido un
lunes.**

Es el mismo defecto que el Sprint 1 encontró en `test_calcular_carga_semanal`,
en otro lugar del sistema: datos relativos a hoy comparados contra una
agrupación por semana calendario.

Corregido anclando las fechas al lunes de cada semana, con cuatro pruebas
(`tests/unit/test_seed_reproducibilidad.py`) que simulan los siete días —
mismo método con el que se demostró el defecto del Sprint 1. Verificado
además contra Firestore real un sábado: 14 km, los mismos valores que dio la
quinta medición un viernes.

### 5.2 AG-07 invoca de más y la métrica no lo registra

AG-07 invocó `consultar_base_conocimiento` **tres veces seguidas**, con una
latencia de 21315 ms frente a los 12662 ms de la corrida anterior (+68 %). El
criterio de subconjunto (sección 1.1) lo contabilizó como acierto.

La causa no está en el agente sino en la cobertura documental: la propia
respuesta lo dice.

> *«Aunque **no tenemos detalles específicos de la base de conocimiento sobre
> adaptaciones concretas en calor**…»*

El agente buscó tres veces guía sobre entrenar con calor y no la encontró —
**ninguno de los siete documentos de la knowledge base cubre calor o
humedad**. Para un usuario en Maracaibo, con 30.1 °C en la consulta, es una
laguna llamativa. El párrafo de encadenamiento del prompt le dio permiso para
insistir; la laguna documental le dio motivo.

Es, además, un ejemplo de comportamiento honesto: declaró la ausencia en vez
de completar con conocimiento general no verificado, que es justamente lo que
la sección de citación del prompt le exige.

### 5.3 El golden set tiene un solo caso `react`

La métrica de esa categoría es binaria —0 % o 100 %, sin puntos
intermedios— y de altísima varianza. Es el tipo de caso más complejo del
conjunto y el peor medido. Combinado con la advertencia de la sección 4.3
sobre la cercanía entre el ejemplo del prompt y el enunciado del caso, el
resultado de `react` debe leerse como indicativo, no como concluyente.

### 5.4 AG-10 está mal etiquetado

Su tipo es `sin_herramientas` pero su `herramientas_esperadas` es
`["consultar_base_conocimiento"]`. La categoría reporta 2/2 cuando en
realidad solo AG-01 es un caso sin herramientas. No afecta la tasa global
—cada caso se evalúa contra sus propias herramientas esperadas— pero sí hace
engañoso el desglose por tipo de la sección 3.2.

### 5.5 La heurística del hallazgo C es textual, no estructural

Depende de una lista de frases en español. Puede tener falsos negativos (una
formulación no contemplada pasa sin detectarse) o falsos positivos (un
reintento gastado de más). No es una garantía programática como
`validar_fuentes()` del Sprint 1. Se documentó la alternativa estructural
—`tool_config` con `Mode.ANY`— y por qué se descartó: el SDK no la acepta por
mensaje dentro de una sesión de chat, y aplicarla a nivel de modelo forzaría
una llamada en cada turno, rompiendo AG-01 y AG-09.

El mecanismo se ejercitó realmente **una sola vez** en las cinco corridas, en
AG-06 de la v3 (`reintento_utilizado: true`, `reintento_fallido: false`). En
v4 y v5 no se activó ninguna vez. Conviene ser preciso al reportarlo: está
verificado por una activación real, no por una batería de casos.

### 5.6 La evaluación no mide fidelidad de contenido

Se verifica que los `doc_id` citados provengan de la herramienta, pero no que
la afirmación del agente sea fiel al contenido del fragmento recuperado. Esa
evaluación —*faithfulness* con juez LLM— quedó pendiente desde el Sprint 1 y
sigue pendiente.

## 6. Propuestas de mejora

**Sobre el marco de evaluación** (lo más urgente, porque condiciona todo lo
demás):

1. **Registrar precisión además de recall.** Añadir a las métricas el número
   de invocaciones no esperadas, para que un caso como AG-07 deje de leerse
   igual que uno limpio.
2. **Distinguir los casos de cero herramientas.** Para
   `herramientas_esperadas: []`, exigir igualdad en vez de subconjunto: hoy
   esos casos no pueden fallar.
3. **Corregir la etiqueta de AG-10** y ampliar el conjunto con más casos
   `react`, para que esa categoría deje de ser binaria.
4. **Evitar ejemplos en el prompt que reproduzcan literalmente un caso del
   golden set**, para no confundir generalización con memorización del
   enunciado.

**Sobre la base de conocimiento:**

5. **Cubrir entrenamiento en calor y humedad.** La laguna de la sección 5.2
   es especialmente relevante para el clima de Maracaibo, que es donde vive el
   usuario de prueba y donde viviría buena parte de los usuarios reales.

**Sobre el agente:**

6. Evaluar la migración a `google-genai` antes del retiro del SDK actual
   (junio de 2026), y revisar de paso si permite `tool_config` por mensaje, lo
   que convertiría la heurística del hallazgo C en una garantía estructural.
7. Expirar turnos de memoria conversacional por antigüedad, no solo por
   cantidad.
8. Implementar evaluación de fidelidad con juez LLM (sección 5.6).

---

## 7. Conclusión

La tasa de acierto de **invocación de herramientas** cerró en 100 % (10/10)
en la quinta medición, partiendo de 70 % en la primera. Esa cifra mide una
cosa concreta y acotada: si el agente eligió consultar lo que debía
consultar. No mide si invocó de más (sección 5.2), ni la fidelidad del
contenido (5.6), ni la calidad general de la conversación, que se evalúa
cualitativamente en la sección 4.

El resultado más valioso del ejercicio no es el número final sino los seis
hallazgos que lo produjeron, más las cuatro limitaciones del propio marco de
medición documentadas aquí. Ninguno de los seis era detectable con las
pruebas unitarias con mocks, que se mantuvieron en verde durante las cinco
rondas — por diseño, un mock nunca falla como falla un servicio real.
