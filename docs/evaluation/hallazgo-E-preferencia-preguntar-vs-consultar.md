# Hallazgo E — El agente pregunta al corredor datos que ya puede consultar

**Rama:** `feat/memoria-y-herramientas`
**Detectado en:** tercera medición de evaluación (post-correcciones A, B, C, D)
**Caso afectado:** AG-08 (`react`) — único fallo de la corrida
**Componente:** `prompts/agents/wellness_coach_agent.txt`
**Severidad:** media — no rompe nada, degrada la utilidad de la respuesta
**Naturaleza:** diseño de prompt, no defecto de código

---

## 1. Contexto: la hipótesis anterior era incorrecta

En el análisis de la primera medición (70 %) se atribuyó el fallo de AG-08 a
la contaminación de memoria del hallazgo A. La hipótesis era que el dolor de
rodilla arrastrado desde AG-06 desviaba la atención del agente.

**Esa hipótesis queda refutada.** En la tercera corrida la memoria está limpia
—verificado textualmente— y AG-08 falla exactamente igual.

La causa es otra.

---

## 2. El caso

```json
{
  "id": "AG-08",
  "tipo": "react",
  "turnos": ["Siento que he corrido demasiado esta semana, es peligroso seguir asi?"],
  "herramientas_esperadas": ["consultar_progreso_objetivo", "consultar_base_conocimiento"],
  "herramientas_invocadas": ["consultar_base_conocimiento"],
  "coincidencia_herramientas": false,
  "reintento_utilizado": false,
  "reintento_fallido": false,
  "latencia_ms": 9421
}
```

Invocó la base de conocimiento pero **no** consultó el progreso del objetivo.

### Cómo cierra la respuesta

> *"Para poder darte una orientación más precisa, me gustaría saber: **¿a qué
> te refieres con «demasiado»? ¿Fue un incremento significativo en tu
> kilometraje semanal habitual**, o hiciste alguna carrera más larga de lo
> normal, o entrenamientos más intensos? ¿Estás sintiendo alguna molestia o
> dolor en particular?"*

**El agente le pregunta al corredor exactamente el dato que
`consultar_progreso_objetivo` le habría dado.**

La herramienta devuelve carga semanal actual, carga de la semana anterior y
progreso respecto a la meta. Es literalmente la respuesta a *"¿fue un
incremento significativo en tu kilometraje semanal habitual?"*.

---

## 3. Causa raíz

Revisando `prompts/agents/wellness_coach_agent.txt`, la instrucción para esa
herramienta dice:

```
2. consultar_progreso_objetivo
   Úsala cuando el corredor pregunte cómo va respecto a su meta, o
   cuando necesites saber su carga semanal actual para dar un consejo
   ajustado a su volumen real.
```

La guía es razonable, pero el prompt describe **cuándo usar cada herramienta
de forma aislada**. En ningún punto establece un principio general sobre qué
hacer cuando el agente detecta que le falta un dato del corredor.

Frente a la ambigüedad de *"siento que he corrido demasiado"*, el modelo
razonó:

1. Es una pregunta de dominio → consulta la base de conocimiento ✓
2. Necesito saber cuánto corrió realmente → **le pregunto al corredor** ✗

El paso 2 debería haber sido *"consulto su progreso"*. Nada en el prompt le
dice que prefiera averiguar sobre preguntar.

La regla más cercana es la última de la sección de límites:

```
- No inventes datos del corredor que no hayas obtenido de una
  herramienta o de los datos básicos ya provistos arriba.
```

Esa regla previene la **fabricación**, no la **pregunta innecesaria**. El
agente la cumplió: no inventó nada. Simplemente eligió el camino menos útil.

---

## 4. Matiz importante: preguntar no siempre está mal

Antes de corregir, conviene delimitar el problema, porque una sobrecorrección
sería peor que el defecto.

**Preguntar es correcto cuando:**

- El dato depende de una percepción subjetiva del corredor (dolor, fatiga,
  motivación) que ninguna herramienta puede aportar
- La pregunta es genuinamente ambigua y hay varias interpretaciones
  igualmente válidas
- Se trata de una preferencia o intención del usuario, no de un hecho
  registrado

**Preguntar es incorrecto cuando:**

- El dato está disponible a través de una herramienta
- El agente pide al usuario que le informe algo que la plataforma ya sabe

En AG-08 se cumplen ambas condiciones del segundo grupo: el kilometraje
semanal está en Firestore y hay una herramienta dedicada a exponerlo.

Nótese que la respuesta del agente mezcla los dos tipos de pregunta:

| Pregunta que hizo | Tipo | ¿Correcta? |
|---|---|---|
| *"¿Fue un incremento significativo en tu kilometraje semanal habitual?"* | Dato registrado | ✗ debió consultarlo |
| *"¿Hiciste alguna carrera más larga de lo normal?"* | Dato registrado | ✗ está en el historial |
| *"¿Estás sintiendo alguna molestia o dolor?"* | Percepción subjetiva | ✓ correcta |

La tercera pregunta es exactamente lo que un buen entrenador haría. Las dos
primeras son datos que la plataforma tiene.

---

## 5. Corrección propuesta

Añadir un principio explícito de precedencia en
`prompts/agents/wellness_coach_agent.txt`, en la sección de herramientas,
antes o después del listado.

Boceto de la idea, ajústalo a tu criterio:

```
PRINCIPIO DE PRECEDENCIA: consultar antes que preguntar

Si para responder necesitas un dato del corredor y existe una herramienta
que lo provee, invócala en vez de pedírselo al corredor. La plataforma ya
registra sus sesiones, su carga semanal y su progreso: preguntárselo es
redundante y traslada al usuario un trabajo que te corresponde.

Reserva las preguntas para lo que ninguna herramienta puede darte:
percepciones subjetivas (dolor, fatiga, motivación), intenciones y
preferencias. Esas sí conviene preguntarlas.
```

### Consideraciones

**1. Verifica que no rompa AG-01 ni AG-09.** Son los casos que esperan cero
herramientas (*"Hola, buenos días"* y la pregunta sobre películas). Un
principio de precedencia mal calibrado podría empujar al modelo a invocar
herramientas donde no corresponde. Ambos están en 100 % ahora; hay que
mantenerlos.

**2. El caso AG-08 es de tipo `react`,** el único de esa categoría. Su tasa
actual es 0/1. Si esta corrección funciona, el tipo `react` pasaría a 1/1 y
la tasa global a 100 %.

**3. Considera si el golden set debería tener más de un caso `react`.** Un
solo caso en una categoría hace que su métrica sea binaria y ruidosa — 0 % o
100 % sin puntos intermedios. Es una observación sobre el diseño del conjunto
de evaluación, no urgente para este sprint.

---

## 6. Pruebas

Este hallazgo es difícil de cubrir con pruebas unitarias: el comportamiento
depende del razonamiento del modelo, no de una rama de código.

Lo que sí se puede hacer:

- **Verificación empírica**: volver a correr la evaluación tras el cambio de
  prompt y comprobar que AG-08 invoca las dos herramientas esperadas.
- **Prueba de regresión sobre AG-01 y AG-09**: confirmar que siguen sin
  invocar herramientas.

No inventes una prueba unitaria artificial para esto. La honestidad
metodológica vale más: es un ajuste de prompt cuya validación es empírica y
no determinista.

---

## 7. Commit sugerido

```
fix: instruir al agente a consultar herramientas antes de preguntar al usuario

En AG-08 el agente pidio al corredor su kilometraje semanal en vez de
invocar consultar_progreso_objetivo, que expone exactamente ese dato. El
prompt describia cuando usar cada herramienta de forma aislada, pero no
establecia un principio de precedencia entre consultar y preguntar.

Se agrega ese principio, delimitando que las preguntas quedan reservadas
para percepciones subjetivas e intenciones, que ninguna herramienta puede
aportar.

La hipotesis inicial atribuia este fallo a la contaminacion de memoria del
hallazgo A. La tercera medicion, con memoria limpia verificada, lo refuto:
el fallo persiste y su causa es de diseno de prompt.

Refs #14
```

---

## 8. Estado de la medición cuando se detectó

Tercera corrida, tras corregir los hallazgos A, B, C y D.

| Métrica | v1 | v3 |
|---|---|---|
| Tasa de acierto de herramientas | 70.0 % | **90.0 %** |
| Latencia promedio | 8714 ms | 8544 ms |
| Casos completados | 10/10 | 10/10 |
| Casos con límite de iteraciones | 0 | 0 |

**Por tipo (v3):**

| Tipo | Aciertos |
|---|---|
| `sin_herramientas` | 2/2 |
| `tool_calling` | 3/3 |
| `rag` | 2/2 |
| `memoria` | 1/1 |
| `limite_alcance` | 1/1 |
| **`react`** | **0/1** ← este hallazgo |

**Cambios respecto a v1:**

| Caso | v1 | v3 | |
|---|---|---|---|
| AG-03 | REVISAR | OK | corregido por hallazgo B |
| AG-05 | REVISAR | OK | corregido por hallazgo C |
| AG-08 | REVISAR | REVISAR | **este documento** |

Los otros siete casos se mantuvieron en OK. Sin regresiones.

### Nota sobre el hallazgo C

El mecanismo de reintento se ejercitó **una vez** en la corrida, en AG-06, y
funcionó (`reintento_utilizado: true`, `reintento_fallido: false`).

AG-05, que en v1 era la manifestación principal del problema, pasó con
`reintento_utilizado: false` — el modelo invocó la herramienta directamente
sin caer en el fallo. Conviene ser preciso al reportarlo: **el mecanismo está
verificado por AG-06, no por AG-05.** AG-05 pasó porque el problema no se
reprodujo en esa ejecución, lo cual es información distinta.

---

## 9. Recomendación sobre el alcance

Este hallazgo **no bloquea el cierre del issue #15**. La medición de 90 % con
los cuatro hallazgos anteriores corregidos y este documentado es un resultado
cerrable y defendible.

Dos caminos válidos:

**A. Corregir e intentar una cuarta medición.** Si funciona, la tasa sube a
100 %. Riesgo: rendimiento decreciente y posible regresión en AG-01/AG-09.

**B. Documentarlo como limitación conocida** en el informe del sprint (#16) y
dejar la corrección para el Sprint 3.

La opción B tiene un argumento a favor que vale la pena considerar: **un 90 %
con un fallo bien caracterizado es académicamente más interesante que un
100 %**. Este caso ilustra una distinción real y no trivial —cuándo un agente
debe averiguar y cuándo debe preguntar— que difícilmente se hubiera detectado
sin medición empírica sobre un servicio real.

Sea cual sea la decisión, el análisis de este documento debería entrar en
`docs/evaluation/agent-evaluation.md` y en el informe del sprint.
