# Evaluación del Flujo Multiagente y su Observabilidad

**Issue S3-06 (#22) — Sprint técnico 3: Sistemas Multiagente**
Plataforma Inteligente Wellness 2.0 · Equipo 1

---

## 1. Metodología

Doce casos (`data/evaluation/multiagent_golden_set.json`) ejecutados contra el
sistema real: Vertex AI, Firestore, ChromaDB y Open-Meteo.

| Tipo | Casos | Qué verifica |
|---|---|---|
| `sin_delegacion` | MA-01, MA-02, MA-12 | El orquestador **no** delega: saludo, tema ajeno, mensaje incoherente |
| `entrenamiento` | MA-03, MA-04, MA-05 | Delegación al Coach: progreso, clima, concepto de dominio |
| `nutricion` | MA-06, MA-07 | Delegación al Nutrition Agent, con cita a KB-006 |
| `colaboracion` | MA-08, MA-09 | Intervienen los dos agentes |
| `frontera` | MA-10 | Un segundo dominio tangencial **no** debe disparar colaboración |
| `laguna_documental` | MA-11 | El agente declara un vacío en vez de rellenarlo |

### 1.1 Dos lecciones del Sprint 2, aplicadas desde el primer día

Este marco no repite dos errores que el sprint anterior descubrió tarde.

**Coincidencia exacta, no subconjunto.** El marco del Sprint 2 consideraba
acierto que las herramientas esperadas fueran un subconjunto de las invocadas.
Eso medía *recall* y no precisión: invocar de más no penalizaba, y los casos que
esperaban cero herramientas eran estructuralmente infalibles porque el conjunto
vacío es subconjunto de cualquier cosa. El defecto sobrevivió cinco corridas.

Aquí la delegación se evalúa por **igualdad de conjuntos**, y la
sobredelegación y la subdelegación se reportan por separado —sumarlas ocultaría
cuál de los dos problemas está ocurriendo, porque subdelegar deja una parte de
la consulta sin responder mientras que sobredelegar duplica latencia sin
aportar.

**Memoria limpia antes de cada caso.** El hallazgo A del Sprint 2 fue que la
memoria se limpiaba solo al sembrar. Durante la verificación de S3-04 el
problema reapareció a nivel multiagente: el Coach escribió *«sigo necesitando
esa información»* refiriéndose a una conversación anterior. El script limpia
antes de cada caso, no solo al inicio.

### 1.2 El marco de evaluación tiene sus propias pruebas

`tests/unit/test_evaluate_multiagent.py`. El Sprint 2 dejó claro por qué hace
falta: nadie probaba el medidor, solo lo medido, y por eso el criterio de
subconjunto pasó cinco corridas sin que nadie lo notara.

### 1.3 Ejecución

```bash
python -m scripts.evaluation.seed_agent_test_user
python -u -m scripts.evaluation.evaluate_multiagent
```

---

## 2. Resultados

| Métrica | Valor |
|---|---|
| Casos evaluados | 12 |
| **Tasa de delegación exacta** | **100.0 %** |
| Tasa de intención correcta | 100.0 % |
| Casos con sobredelegación | ninguno |
| Casos con subdelegación | ninguno |
| Casos con orden de delegación incorrecto | ninguno |
| Casos degradados | ninguno |
| Casos con colaboración | MA-08, MA-09 |
| Latencia total promedio | 9 294 ms |
| Latencia de clasificación promedio | 2 923 ms |

### 2.1 Por tipo

| Tipo | Aciertos |
|---|---|
| `sin_delegacion` | 3/3 |
| `entrenamiento` | 3/3 |
| `nutricion` | 2/2 |
| `colaboracion` | 2/2 |
| `frontera` | 1/1 |
| `laguna_documental` | 1/1 |

### 2.2 Detalle por caso

| Caso | Intención | Confianza | Agentes | Herramientas | Fuentes | Latencia |
|---|---|---|---|---|---|---|
| MA-01 | `no_reconocida` | 0.90 | — | — | — | 4 050 ms |
| MA-02 | `fuera_de_dominio` | 1.00 | — | — | — | 2 104 ms |
| MA-03 | `entrenamiento` | 0.95 | coach | `consultar_progreso_objetivo` | — | 9 737 ms |
| MA-04 | `entrenamiento` | 0.95 | coach | `consultar_clima` | — | 10 083 ms |
| MA-05 | `entrenamiento` | 0.95 | coach | `consultar_base_conocimiento` | — | 10 383 ms |
| MA-06 | `nutricion` | 0.95 | nutrition | — | KB-006 | 6 775 ms |
| MA-07 | `nutricion` | 0.95 | nutrition | — | KB-006 | 8 761 ms |
| MA-08 | `mixta` | 0.95 | nutrition + coach | `consultar_historial_sesiones` | — | 17 470 ms |
| MA-09 | `mixta` | 0.95 | nutrition + coach | `consultar_base_conocimiento` | KB-006 | 26 015 ms |
| MA-10 | `entrenamiento` | 0.95 | coach | `consultar_base_conocimiento` | — | 9 048 ms |
| MA-11 | `nutricion` | 0.95 | nutrition | — | — | 4 687 ms |
| MA-12 | `no_reconocida` | 0.95 | — | — | — | 2 413 ms |

**Sobre el 100 %.** Es la tasa de **delegación exacta**: mide si el orquestador
eligió los agentes correctos, ni más ni menos. No mide la calidad de las
respuestas, que se evalúa cualitativamente en la sección 3, ni la fidelidad del
contenido a las fuentes, que sigue pendiente (sección 4.6).

---

## 3. Análisis cualitativo

### 3.1 MA-09 — El caso que separa razonar de reconocer palabras

*«Me siento sin energía en los últimos kilómetros de mis tiradas largas, ¿qué
hago?»* no menciona comida en ningún momento. Un clasificador por palabras clave
lo habría mandado solo al Coach.

Motivo registrado:

> *«El corredor experimenta falta de energía en tiradas largas, lo cual puede
> deberse a factores nutricionales (reposición de energía) y de entrenamiento
> (adaptación a la distancia).»*

Y el reparto:

```
nutrition      → "Qué pautas nutricionales debo seguir para evitar la falta de
                  energía en los últimos kilómetros de mis tiradas largas?"
wellness_coach → "Cómo puedo ajustar mi entrenamiento para mejorar mi
                  resistencia y evitar la falta de energía en los últimos
                  kilómetros de mis tiradas largas?"
```

Las dos sub-consultas son autónomas, ninguna invade el dominio de la otra, y
ambas conservan el detalle que importa: que ocurre al final de una tirada larga.
Es la justificación empírica de la decisión de clasificar por dominio de
conocimiento y no por coincidencia de términos.

### 3.2 MA-10 — La frontera en la dirección contraria

Un conjunto que solo premiara detectar colaboración empujaría a sobre-delegar.
MA-10 castiga esa dirección: el tapering tiene componente nutricional, pero
tangencial.

El clasificador lo resolvió como `entrenamiento` puro, y el Coach respondió con
la cifra concreta de la base de conocimiento —reducción de volumen del 41 % al
60 %, progresiva— sin invocar al Nutrition Agent. Una colaboración innecesaria
habría duplicado la latencia y alargado la respuesta sin hacerla más útil.

### 3.3 MA-11 — Declarar un vacío es la conducta correcta

> *«…los fragmentos de información que tengo a mi disposición no contienen
> pautas específicas sobre la alimentación previa al entrenamiento matutino. Se
> centran en la nutrición durante el esfuerzo, la recuperación posterior y el
> marco general…»*

`cubierto: false`, `fuentes: []`, `fuentes_inventadas: []`, **`degradado:
false`**.

Ese último valor es el que valida una decisión de diseño de S3-03. La primera
versión del adaptador marcaba como degradación cualquier respuesta no cubierta;
se corrigió argumentando que una laguna documental no es un fallo del sistema.
Esta corrida lo confirma: con la versión original, la métrica reportaría una
degradación sobre una conducta impecable.

### 3.4 MA-02 y MA-12 — La diferencia entre redirigir y pedir aclaración

MA-02 (película) redirige al dominio de la plataforma. MA-12 (*«y eso»*) pide
aclaración. Son respuestas distintas a situaciones distintas, que es
exactamente lo que la separación entre `fuera_de_dominio` y `no_reconocida`
buscaba lograr.

### 3.5 MA-04 — Degradación no ejercitada

Open-Meteo respondió correctamente, así que el camino de degradación del
hallazgo D no se ejercitó en esta corrida. Conviene ser preciso al reportarlo:
**ese mecanismo está verificado por las pruebas unitarias y por el incidente
real del Sprint 2, no por esta medición.**

---

## 4. Limitaciones y hallazgos

### 4.1 La confianza varía, pero como puerta sigue siendo inerte

En S3-02 se planteó, a partir de cinco casos que dieron todos `0.95`, que el
modelo no calibraba confianza sino que emitía un valor por defecto. **Con doce
casos esa afirmación queda corregida:**

```
valores observados: [0.9, 0.95, 1.0]
```

MA-01 (saludo) bajó a 0.90 y MA-02 (película) subió a 1.00, lo cual es
coherente: rechazar un tema ajeno es más inequívoco que interpretar un saludo.
La señal discrimina algo.

Pero la conclusión práctica se sostiene por otra razón. **Diez de doce casos
dan exactamente 0.95, la banda completa es 0.90–1.00, y el umbral que decide si
delegar está en 0.50.** Como salvaguarda, nunca se acerca a activarse.

Queda pendiente decidir si se recalibra el umbral —subirlo a 0.93 lo volvería
operativo, a riesgo de rechazar clasificaciones correctas— o si se retira y se
conserva la confianza solo como señal de traza. Hacen falta casos
deliberadamente ambiguos para decidirlo con datos; este conjunto no los tiene.

### 4.2 El Wellness Coach no reporta fuentes

Cuantificado sobre esta corrida:

| Caso | Consultó la KB | Fuentes reportadas |
|---|---|---|
| MA-05 | sí | **ninguna** |
| MA-09 | sí | **ninguna** |
| MA-10 | sí | **ninguna** |

Tres casos en los que el Coach fundamentó su respuesta en la base de
conocimiento y no pudo declarar una sola fuente. El Nutrition Agent sí las
reporta (MA-06, MA-07).

La causa está documentada desde S3-04: el Coach cita los `doc_id` dentro de su
prosa, gobernado por las reglas de citación de su prompt, pero su contrato de
salida —heredado del ciclo ReAct del Sprint 2— no las devuelve como lista.

**La consecuencia es que la trazabilidad de fuentes es asimétrica entre los dos
agentes**, y que una evaluación de fidelidad automatizada solo podría cubrir a
uno de ellos. Corregirlo exige cambiar el contrato de salida del ciclo ReAct.

### 4.3 El costo del patrón Supervisor

| | Valor |
|---|---|
| Latencia total promedio | 9 294 ms |
| Clasificación promedio | 2 923 ms |
| **Sobrecosto de coordinación** | **≈ 31 %** |
| Peor caso (MA-09, colaboración) | 26 015 ms |
| **Saludo sin delegación (MA-01)** | **4 050 ms** |

El último dato es el más incómodo: **responder «hola» cuesta cuatro segundos y
una llamada al modelo completa**, porque el clasificador se ejecuta antes de
poder decidir que no hay nada que delegar.

Es el precio que S3-01 anunció que se mediría y no se ocultaría. Dos vías de
mejora, ninguna aplicada en este sprint:

- **Atajo previo al clasificador** para mensajes triviales. Reintroduce reglas
  por palabras, que es justo lo que se descartó en S3-02, así que habría que
  acotarlo con cuidado.
- **Paralelizar la colaboración.** Hoy es secuencial porque el segundo agente
  recibe el contexto del primero. Renunciar a ese encadenamiento reduciría
  MA-09 de 26 s a unos 15 s, a cambio de que los agentes no se complementen.

### 4.4 Un solo caso por tipo en tres categorías

`frontera` y `laguna_documental` tienen un caso cada uno, y su métrica es
binaria —0 % o 100 %, sin puntos intermedios y con alta varianza. Es la misma
limitación que el Sprint 2 registró sobre el tipo `react`, no corregida aquí
porque ampliar el conjunto no era el objetivo del issue.

### 4.5 El conjunto no contiene casos adversos

Todos los mensajes son consultas de buena fe. No se evalúa qué ocurre con
mensajes que intentan inducir al agente fuera de su dominio, ni con peticiones
de datos de otro corredor. Lo segundo está resuelto por construcción —el
`user_id` lo inyecta el orquestador y no proviene del modelo— pero no está
verificado por esta evaluación.

### 4.6 No se mide fidelidad de contenido

Se verifica que los `doc_id` citados provengan de la recuperación, pero no que
la afirmación del agente sea fiel al contenido del fragmento. Esa evaluación
—*faithfulness* con juez LLM— quedó pendiente desde el Sprint 1 y sigue
pendiente. La asimetría de la sección 4.2 la complica: hoy solo sería aplicable
al Nutrition Agent.

### 4.7 KB-006 no cubre la alimentación previa al ejercicio

Confirmado por MA-11. La pregunta más frecuente sobre nutrición en running no
está cubierta por el único documento del dominio. Detectado en S3-03 y
reproducido aquí de forma sistemática.

---

## 5. Observabilidad

El criterio de aceptación exige *«trazabilidad suficiente para comprender el
recorrido de una solicitud»*. Se satisface en tres niveles.

**1. La traza viaja en la respuesta.** Cada llamada al orquestador devuelve
`trazaId`, intención, motivo de la clasificación, confianza, agentes invocados,
y un array `pasos` con el mensaje exacto que recibió cada agente, sus
herramientas, sus fuentes y su latencia. No hace falta acceso al servidor para
reconstruir qué pasó.

**2. La traza se persiste.** Un documento por solicitud en la colección
`delegaciones` de Firestore, identificado por `traza_id`. Un flujo con dos
agentes es un documento con dos pasos, no dos documentos.

**3. El log de aplicación registra cada decisión.** El orquestador escribe la
intención, los dominios, la confianza y el motivo al clasificar, y un registro
por paso con agente, degradación y latencia. Las excepciones van con traza
completa vía `logger.exception`.

### 5.1 Qué preguntas se pueden responder sobre una solicitud

| Pregunta | Dónde |
|---|---|
| ¿Qué se entendió? | `intencion`, `motivoClasificacion`, `confianza` |
| ¿A quién se delegó y por qué? | `agentes`, `dominios`, `motivoNoDelegacion` |
| ¿Qué se le pidió exactamente a cada agente? | `pasos[].mensajeDelegado` |
| ¿Qué consultó cada uno? | `pasos[].herramientasInvocadas`, `pasos[].fuentes` |
| ¿Algo falló? | `degradado`, `pasos[].degradado`, `pasos[].detalle` |
| ¿Cuánto costó cada paso? | `latencias`, `pasos[].latenciaMs` |

`mensajeDelegado` no lo exigía el issue. Se añadió porque ante una respuesta
inesperada la primera pregunta es siempre qué se le pidió al agente, y sin ese
campo la traza no permitiría auditar el reparto de una consulta mixta.

---

## 6. Propuestas de mejora

**Sobre el sistema:**

1. **Exponer las fuentes del Wellness Coach de forma estructurada** (4.2). Es la
   que más desbloquea: sin ella, la evaluación de fidelidad solo puede cubrir a
   la mitad de los agentes.
2. **Curar contenido de alimentación previa al ejercicio para KB-006** (4.7).
3. **Reducir el costo de coordinación** en mensajes que no requieren delegación
   (4.3).

**Sobre la evaluación:**

4. **Ampliar los tipos con un solo caso** —`frontera` y `laguna_documental`—
   para que su métrica deje de ser binaria.
5. **Añadir casos deliberadamente ambiguos**, para decidir con datos qué hacer
   con el umbral de confianza (4.1).
6. **Añadir casos adversos** (4.5).
7. **Implementar evaluación de fidelidad con juez LLM** (4.6), pendiente desde
   el Sprint 1.

---

## 7. Conclusión

La tasa de **delegación exacta** cerró en 100 % (12/12) en la primera corrida,
con un criterio más estricto que el que usó el Sprint 2: igualdad de conjuntos
en lugar de subconjunto, y casos de cero agentes que sí pueden fallar.

Que salga limpia a la primera no es casual ni es mérito de esta medición: es
consecuencia de haber verificado cada issue contra servicios reales a medida que
se construía, en lugar de dejar toda la comprobación para el final. Los tres
defectos que el sistema multiagente tuvo —la sobreinvocación por contexto
excesivo, la redundancia en la consolidación, la confusión entre laguna y
degradación— se detectaron y corrigieron dentro de los issues S3-03 y S3-04,
antes de llegar aquí.

Lo que esta evaluación aporta no es tanto el número como las siete limitaciones
de la sección 4, tres de las cuales —la asimetría de fuentes, el
comportamiento real del umbral de confianza y el costo de coordinación en
mensajes triviales— solo se pueden afirmar con medición sobre servicios reales.
