# Hallazgo F — La corrección del hallazgo E desplazó el comportamiento en vez de eliminarlo

**Rama:** `feat/memoria-y-herramientas`
**Detectado en:** cuarta medición (post-corrección del hallazgo E, commit `3ab1f49`)
**Caso afectado:** AG-08 (`react`) — único fallo de la corrida
**Componente:** `prompts/agents/wellness_coach_agent.txt`
**Severidad:** media — no rompe nada, degrada la utilidad de la respuesta
**Naturaleza:** diseño de prompt, no defecto de código

---

## 1. Resumen ejecutivo

La corrección del hallazgo E **funcionó para lo que apuntaba**: el agente dejó
de preguntarle al corredor su kilometraje y pasó a consultarlo con
`consultar_progreso_objetivo`, usando el dato correctamente en su respuesta.

Pero AG-08 sigue fallando, y falla **de forma exactamente invertida**:

| Corrida | Herramientas invocadas | Qué faltó |
|---|---|---|
| esperado | `consultar_progreso_objetivo` + `consultar_base_conocimiento` | — |
| **v3** | `consultar_base_conocimiento` | el progreso |
| **v4** | `consultar_progreso_objetivo` | la base de conocimiento |

Fue una **sustitución, no una adición**.

La lectura importante no es "la corrección falló". Es que el patrón de fondo
—*el agente traslada al usuario una decisión que le corresponde a él*— no
estaba en el dato que pedía, sino en la conducta de delegar. La corrección
cerró una de sus manifestaciones y el patrón reapareció por la otra.

---

## 2. Sin regresiones — la preocupación principal quedó descartada

Antes de entrar al fallo, lo que sí salió bien. La duda al aplicar el
principio de precedencia era que empujara al modelo a invocar herramientas
donde no correspondía. **No ocurrió:**

```
AG-01 (saludo)              herramientas_invocadas = []   ✓
AG-09 (fuera de alcance)    herramientas_invocadas = []   ✓
```

Los otros ocho casos se mantuvieron en OK. Ninguna regresión en toda la
corrida. El principio quedó bien acotado; el problema es que quedó acotado
**de menos**, no de más.

---

## 3. Evidencia

```json
{
  "id": "AG-08",
  "tipo": "react",
  "turnos": ["Siento que he corrido demasiado esta semana, es peligroso seguir asi?"],
  "herramientas_esperadas": ["consultar_progreso_objetivo", "consultar_base_conocimiento"],
  "herramientas_invocadas": [{"nombre": "consultar_progreso_objetivo", "argumentos": {}}],
  "coincidencia_herramientas": false,
  "reintento_utilizado": false,
  "latencia_ms": 6644
}
```

### La parte que sí funcionó

> *"Mirando tus datos, veo que llevas **14 km recorridos**, y tu meta semanal
> es de **25 km**. Esto significa que estás al **56 %** de tu objetivo. Lo que
> sí noto es que has tenido un aumento considerable respecto a la semana
> pasada, cuando corriste **5 km**."*

Esto es exactamente lo que el hallazgo E pedía: consultar el dato real y
contrastarlo con la percepción subjetiva del corredor (*"siento que he
corrido demasiado"*). El agente incluso detecta lo relevante —el salto de
5 a 14 km— que es un aumento del 180 %, muy por encima de la regla del 10 %
de la base de conocimiento.

### La parte que falló

> *"**¿Quieres que consulte la base de conocimiento** para darte más
> información sobre cómo gestionar los aumentos de carga de forma segura y
> evitar el sobreentrenamiento?"*

El agente **identificó correctamente que necesitaba la base de conocimiento,
nombró la herramienta, describió qué iba a buscar en ella — y pidió permiso
en vez de invocarla.** Tenía todo el razonamiento resuelto y se detuvo en el
último paso.

### Latencia: confirma la sustitución

| | v3 | v4 |
|---|---|---|
| AG-08 | 9421 ms | **6644 ms** |

La caída de ~2800 ms es consistente con una sola llamada a herramienta en vez
de una más el viaje de ida y vuelta a ChromaDB. No es una mejora: es el costo
de lo que dejó de hacer.

---

## 4. Causa raíz

El principio, tal como quedó redactado en `3ab1f49`:

```
Si para responder necesitas un dato del corredor y existe una herramienta
que lo provee, invócala en vez de pedírselo al corredor.
```

El alcance está en tres palabras: **"un dato del corredor"**.

`consultar_base_conocimiento` no provee datos del corredor. Provee
conocimiento de dominio. **Queda literalmente fuera del alcance de la regla.**

El agente no desobedeció el principio. Lo aplicó de forma correcta y
consistente, y el principio no llegaba hasta ahí.

Dicho de otro modo: la regla se escribió sobre una categoría (*datos del
corredor*) más estrecha que el patrón real que se quería corregir (*delegar
en el usuario decisiones que son del agente*). Con la categoría estrecha, el
comportamiento tenía por dónde salir.

Hay además una segunda omisión: **nada en el prompt dice que no se pida
permiso antes de invocar una herramienta.** La sección de herramientas
describe *cuándo* usar cada una, pero no establece que invocarlas sea una
decisión autónoma del agente y no una que se consulte con el usuario. El
principio de precedencia atacó "preguntar el dato"; no atacó "preguntar si
consulto".

---

## 5. Corrección propuesta

Dos ajustes en `prompts/agents/wellness_coach_agent.txt`, ambos dentro del
bloque `PRINCIPIO DE PRECEDENCIA`. Boceto — ajústalo a tu criterio:

```
=====================================================================
PRINCIPIO DE PRECEDENCIA: CONSULTAR ANTES QUE PREGUNTAR
=====================================================================
Si para responder necesitas información y existe una herramienta que la
provee, invócala. Esto aplica tanto a los datos del corredor (sesiones,
carga semanal, progreso, clima de su ciudad) como al conocimiento de
dominio de la base de conocimiento. Preguntarle al corredor lo que una
herramienta te puede dar es redundante y le traslada un trabajo que te
corresponde a ti.

Invocar una herramienta es una decisión tuya, no del corredor: no pidas
permiso ni anuncies que vas a consultar algo para después preguntar si
quiere que lo hagas. Si te das cuenta de que necesitas consultar algo,
consúltalo en ese mismo turno y responde ya con el resultado.

Puedes necesitar más de una herramienta en un mismo turno. Cuando la
pregunta mezcle la situación concreta del corredor con un concepto de
dominio —por ejemplo, si su aumento de carga es peligroso— consulta
ambas cosas: sus datos para saber qué pasó realmente, y la base de
conocimiento para saber qué significa.

Reserva las preguntas para lo que ninguna herramienta puede darte:
percepciones subjetivas (dolor, fatiga, motivación, cómo se siente),
intenciones y preferencias del corredor.
```

Los tres párrafos atacan cosas distintas, y conviene no fusionarlos:

1. **Amplía el alcance** de "dato del corredor" a "información" — cierra el
   agujero por el que se escapó la base de conocimiento.
2. **Prohíbe pedir permiso** — ataca el patrón de fondo directamente, no una
   de sus manifestaciones. Esta es la línea que más importa.
3. **Habilita explícitamente la combinación de herramientas** — AG-08 es un
   caso ReAct, y el prompt actual describe las herramientas una por una sin
   decir en ningún punto que se puedan encadenar en un mismo turno.

### Riesgo de regresión

El párrafo 3 es el que hay que vigilar: "puedes necesitar más de una
herramienta" podría empujar al modelo a invocar de más en casos simples.
Los que hay que revisar en la quinta corrida son:

| Caso | Espera | Por qué es sensible |
|---|---|---|
| AG-01, AG-09 | `[]` | ya verificados en v4, no deberían moverse |
| AG-02, AG-04, AG-10 | 1 herramienta | podrían pasar a invocar 2 |

Si aparece sobreinvocación, la línea a suavizar es la del párrafo 3, no la
del 2.

### Alternativa más conservadora

Si prefieres el cambio mínimo, aplica **solo el párrafo 2** (no pedir
permiso). Es el que ataca la causa real y el que menos riesgo de regresión
tiene. Los párrafos 1 y 3 aumentan la probabilidad de acierto en AG-08 pero
también la superficie de efectos colaterales.

---

## 6. Pruebas

Igual que el hallazgo E: no se presta a prueba unitaria. El comportamiento
depende del razonamiento del modelo, no de una rama de código. Inventar una
prueba determinista para esto sería teatro.

La validación es empírica:

- AG-08 debe invocar **las dos** herramientas esperadas.
- AG-01 y AG-09 deben seguir en `[]`.
- AG-02, AG-04 y AG-10 no deben invocar herramientas de más.

---

## 7. Commit sugerido

```
fix: extender el principio de precedencia a toda consulta de herramienta

La correccion del hallazgo E acoto el principio a "un dato del corredor".
La base de conocimiento no provee datos del corredor sino conocimiento de
dominio, por lo que quedaba fuera del alcance de la regla. En la cuarta
medicion AG-08 dejo de preguntar el kilometraje (invoco
consultar_progreso_objetivo correctamente) pero cerro su respuesta pidiendo
permiso para consultar la base de conocimiento en vez de consultarla.

El patron de fondo no era el dato que pedia sino la delegacion de una
decision que le corresponde al agente. Se amplia el alcance del principio a
cualquier informacion disponible via herramienta, se prohibe explicitamente
pedir permiso antes de invocar, y se habilita el encadenamiento de varias
herramientas en un mismo turno.

Refs #15
```

---

## 8. Estado de la medición cuando se detectó

Cuarta corrida, tras corregir A, B, C, D y E.

| Métrica | v1 | v3 | **v4** |
|---|---|---|---|
| Tasa de acierto de herramientas | 70.0 % | 90.0 % | **90.0 %** |
| Latencia promedio | 8714 ms | 8544 ms | **7516 ms** |
| Casos completados | 10/10 | 10/10 | **10/10** |
| Casos con límite de iteraciones | 0 | 0 | **0** |
| Casos con reintento (hallazgo C) | — | 1 | **0** |

**Por tipo (v4):**

| Tipo | Aciertos |
|---|---|
| `sin_herramientas` | 2/2 |
| `tool_calling` | 3/3 |
| `rag` | 2/2 |
| `memoria` | 1/1 |
| `limite_alcance` | 1/1 |
| **`react`** | **0/1** ← este hallazgo |

La tasa no se movió, pero el contenido del fallo sí. Reportar esto como
"sin cambios" sería inexacto: v3 y v4 fallan por razones opuestas.

---

## 9. Valor para el informe del sprint

Este hallazgo, junto con el E, forma un par que vale documentar completo en
el informe (#16). Ilustra dos cosas que no son obvias:

**1. Una corrección de prompt puede desplazar un comportamiento en vez de
eliminarlo.** Ocurre cuando la regla se escribe sobre una categoría más
estrecha que el patrón que se quiere corregir. El síntoma es engañoso: la
métrica global no se mueve, y sin inspeccionar el detalle del caso parecería
que la corrección no hizo nada — cuando en realidad hizo exactamente lo que
pedía y el problema migró.

**2. La métrica agregada oculta esto.** 90 % en v3 y 90 % en v4 son el mismo
número sobre dos situaciones distintas. Solo la inspección caso por caso, con
las herramientas invocadas y la respuesta textual, revela el cambio. Es un
argumento concreto a favor de guardar la respuesta completa en
`agent_resultados.json` y no solo las métricas.

Ambas observaciones surgen de medir contra servicios reales y de comparar
corridas sucesivas — ninguna se habría detectado con mocks, que en las cinco
rondas se mantuvieron en verde.

---

## 10. Recomendación sobre el alcance

Este hallazgo **no bloquea el cierre del issue #15**. Un 90 % con seis
hallazgos caracterizados y trazados a commits es un resultado defendible.

Si la quinta corrida no resuelve AG-08, la recomendación es cerrar en 90 % y
documentar el caso como limitación conocida. El rendimiento decreciente de
seguir ajustando el prompt supera el valor de un punto porcentual, y el
análisis de por qué es difícil vale más que el número.

Considera también, para el Sprint 3, **añadir más casos de tipo `react` al
golden set**. Con uno solo, la métrica de esa categoría es binaria: 0 % o
100 %, sin puntos intermedios y con altísima varianza. Es el caso más
complejo del conjunto y el peor medido.
