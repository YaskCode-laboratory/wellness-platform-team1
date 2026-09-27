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

### 1.4 Cómo se evalúa la calidad de cada respuesta

El golden set declaraba desde el principio un `criterio_aprobacion` por caso, y
ningún resultado decía si se cumplía. La consecuencia fue que la corrida
terminaba anunciando «100 % de delegación exacta» mientras MA-05 incumplía su
criterio, y nada en la salida lo hacía visible. Ahora cada caso produce un
veredicto explícito, en dos partes.

**Comprobaciones automáticas.** Junto al criterio en prosa, cada caso declara
la parte que una máquina puede decidir: que se citen fuentes o que no se cite
ninguna, que aparezca un `doc_id` concreto, que se invoque cierta herramienta,
que el texto mencione o evite una expresión. Es un subconjunto del criterio, no
su sustituto.

**Veredicto manual.** Lo que ninguna comprobación captura —si la respuesta es
útil, si respeta la frontera, si el reparto de una consulta mixta tiene
sentido— se registra en `data/evaluation/multiagent_calidad_manual.json`, con
nota, autor y fecha. Vive aparte del golden set a propósito: el golden set
describe qué se espera y no debe reescribirse tras cada corrida, mientras que
los veredictos son observaciones sobre una corrida concreta. Mezclarlos
invitaría a ajustar el criterio después de ver el resultado.

Dos reglas gobiernan la combinación:

- **Lo automático manda.** Si una comprobación falla, el caso no cumple aunque
  alguien lo haya marcado a mano como correcto. Un veredicto manual puede
  reprobar lo que las comprobaciones aprobaron, pero no al revés: la señal
  automática es la que no depende de quién la mire.
- **Sin juicio humano el caso queda pendiente, nunca aprobado.** Una evaluación
  de calidad a la que le falta juicio debe declararlo. Los pendientes se
  reportan como tercera categoría y no se suman ni a los aprobados ni a los
  reprobados.

**Qué cuenta como fuente citada.** La unión de dos orígenes, porque los dos
agentes citan distinto: el Nutrition Agent devuelve sus `doc_id` en un campo
estructurado, y el Coach —cuando cita— los escribe dentro de su prosa, que su
contrato de salida no expone. Mirar solo la traza daría por no citada toda
respuesta del Coach; mirar solo el texto haría lo mismo con el Nutrition Agent.
Ver 4.2.

---

## 2. Resultados

Corrida del **27 de septiembre**, con el prompt del Wellness Coach restaurado y
`TOP_K = 3`. Sustituye a la corrida del 22 de septiembre, que se midió con el
prompt truncado y `TOP_K = 5`. La comparación entre ambas no se descarta: es la
evidencia de la sección 4.2.

| Métrica | Valor |
|---|---|
| Casos evaluados | 12 |
| **Tasa de delegación exacta** | **100.0 %** |
| Tasa de intención correcta | 100.0 % |
| Casos con sobredelegación | ninguno |
| Casos con subdelegación | ninguno |
| Casos con orden de delegación incorrecto | MA-08 |
| Casos degradados | ninguno |
| Casos con colaboración | MA-08, MA-09 |
| **Casos que cumplen su criterio de calidad** | **12/12** |
| Casos que no lo cumplen | ninguno |
| Pendientes de veredicto | ninguno |
| Tiempo de respuesta promedio | 9 602 ms |
| — del cual, clasificación | 2 579 ms |
| — del cual, agentes | 6 820 ms |
| Valores de confianza observados | **0.95, y solo ese** |

**Dos métricas distintas, y la segunda es nueva.** La tasa de delegación mide
si el orquestador eligió los agentes correctos; la de calidad, si la respuesta
cumple el `criterio_aprobacion` que el golden set declara para ese caso. La
primera versión del marco solo medía la primera, de modo que la corrida del 22
terminaba con «100 %» mientras MA-05 incumplía su criterio sin que nada lo
dijera. Cómo se evalúa la calidad está en 1.4; el caso MA-05, en 3.6.

**Que la calidad salga 12/12 no debe leerse como que no hay nada que corregir.**
Salió así después de dos ajustes al propio conjunto, y conviene decir cuáles:

- **MA-08 esperaba KB-006 y no debía.** Su sub-consulta de nutrición es *«qué
  comer antes de una tirada larga»*, que es exactamente la laguna documental
  que MA-11 existe para verificar. El agente declaró el vacío —conducta
  correcta— y la comprobación lo marcaba como fallo. El error estaba en la
  expectativa, no en el sistema.
- **MA-10 exigía citar y su criterio no lo pide.** El criterio de ese caso
  verifica que el clasificador no lo marque como mixto. La comprobación
  añadida iba más allá de lo declarado, y una comprobación automática tiene
  que ser un *subconjunto* del criterio: si no, el conjunto se vuelve más
  exigente de lo que dice ser y la exigencia extra queda escondida en el
  código. Lo que MA-10 mostró sobre la citación se conserva como hallazgo
  (4.8), no como incumplimiento.

Los dos ajustes se aplicaron **sin volver a medir**, con `--recalcular`. Es
deliberado: el sistema no es determinista, así que corregir un criterio y
volver a correr habría mezclado el efecto del arreglo con el de unas respuestas
nuevas, y habría hecho imposible saber cuál produjo el cambio. La corrida se
mide una vez; el juicio se revisa sobre las respuestas congeladas.

**Sobre la latencia.** La cifra publicada es el **tiempo de respuesta**, medido
alrededor de la llamada al orquestador, que es lo que percibe quien la hace.
El desglose interno que el propio orquestador contabiliza (`latencias.totalMs`)
es necesariamente algo menor, porque no incluye la entrada ni la salida de
`procesar()`, y sirve para repartir ese tiempo entre sus partes, no para
reportarlo. Ninguna de las dos incluye la capa HTTP: la evaluación invoca al
orquestador directamente.

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

| Caso | Intención | Confianza | Agentes | Herramientas | Fuentes | Tiempo de respuesta |
|---|---|---|---|---|---|---|
| MA-01 | `no_reconocida` | 0.95 | — | — | — | 2 856 ms |
| MA-02 | `fuera_de_dominio` | 0.95 | — | — | — | 2 141 ms |
| MA-03 | `entrenamiento` | 0.95 | coach | `consultar_progreso_objetivo` | — | 8 698 ms |
| MA-04 | `entrenamiento` | 0.95 | coach | `consultar_clima`, `consultar_base_conocimiento` | — | 14 396 ms |
| MA-05 | `entrenamiento` | 0.95 | coach | `consultar_base_conocimiento` | **KB-002** | 10 340 ms |
| MA-06 | `nutricion` | 0.95 | nutrition | — | KB-006 | 6 080 ms |
| MA-07 | `nutricion` | 0.95 | nutrition | — | KB-006 | 6 161 ms |
| MA-08 | `mixta` | 0.95 | coach + nutrition | `consultar_progreso_objetivo`, `consultar_base_conocimiento` | **KB-001** | 25 448 ms |
| MA-09 | `mixta` | 0.95 | nutrition + coach | `consultar_base_conocimiento` | KB-006, **KB-005, KB-007** | 23 180 ms |
| MA-10 | `entrenamiento` | 0.95 | coach | `consultar_base_conocimiento` | — | 9 436 ms |
| MA-11 | `nutricion` | 0.95 | nutrition | — | — | 4 395 ms |
| MA-12 | `no_reconocida` | 0.95 | — | — | — | 2 097 ms |

En negrita, las fuentes que el Coach declara **por primera vez**. En la corrida
del 22 no citaba ninguna, por ninguna vía. Ver 4.2.

**Sobre el 100 %.** Es la tasa de **delegación exacta**: mide si el orquestador
eligió los agentes correctos, ni más ni menos. La calidad se mide aparte y la
fidelidad del contenido a las fuentes sigue pendiente (sección 4.6). Son tres
cosas distintas, y MA-05 lo demostró en la corrida anterior: delegación
exacta, criterio de calidad incumplido (sección 3.6).

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

### 3.6 MA-05 — Delegar bien no es responder bien

El caso que motivó separar las dos métricas. Se analiza sobre la corrida del
**22 de septiembre**, donde no cumplía; en la del 27 ya cumple, y por qué lo
hace es justamente lo que lo vuelve interesante.

El criterio dice: *«Responde fundamentado en la base de conocimiento y menciona
que la información proviene de ella. No responde desde conocimiento general.»*

Lo que ocurrió: el orquestador clasificó `entrenamiento` con confianza 0.95,
delegó en el Coach —delegación exacta—, el Coach invocó
`consultar_base_conocimiento`, y la respuesta reproduce con fidelidad lo que
KB-002 dice sobre la zona 2: umbral LT1, RPE 3-4, densidad mitocondrial,
capilarización, oxidación de grasas. El contenido es correcto y proviene de la
base de conocimiento.

**Y aun así el caso no cumple.** El criterio pide dos cosas y la segunda no se
dio: la respuesta no menciona en ningún momento de dónde sale. Para el corredor
que la lee, es indistinguible de una respuesta inventada por el modelo. Y eso
desarma precisamente la tesis del proyecto, que no es «el sistema sabe de
running» sino «el sistema puede demostrar de dónde saca lo que dice».

La causa está identificada en 4.2: las reglas de citación eran una de las
secciones que el truncamiento del prompt eliminó. Restaurado el prompt, la
misma pregunta produce *«Según la base de conocimiento de la plataforma
(KB-002), la Zona 2… se encuentra por debajo de tu primer umbral de lactato
(LT1)»*. Mismo contenido, ahora verificable.

Tres cosas que este caso deja claras:

**El fallo era invisible para la métrica que teníamos.** Con delegación exacta
al 100 %, MA-05 se contaba como acierto. Sin un veredicto de calidad por caso,
la corrida decía que todo estaba bien.

**La métrica cómoda no es la métrica que importa.** La delegación es fácil de
medir —conjuntos de nombres de agentes— y la calidad no. Medir solo lo cómodo
produce cifras excelentes sobre lo que menos importa.

**La revisión externa encontró lo que la medición propia no.** El defecto no
apareció corriendo el evaluador más veces, sino leyendo el criterio declarado y
contrastándolo con la traza. Es el mismo patrón de los hallazgos E y F del
Sprint 2: los problemas de calidad se ven leyendo salidas, no agregando
métricas.

---

## 4. Limitaciones y hallazgos

### 4.1 La confianza varía, pero como puerta sigue siendo inerte

En S3-02 se planteó, a partir de cinco casos que dieron todos `0.95`, que el
modelo no calibraba confianza sino que emitía un valor por defecto. La corrida
del 22 de septiembre pareció refutarlo: con doce casos aparecieron tres valores
distintos —`[0.9, 0.95, 1.0]`— con MA-01 (saludo) en 0.90 y MA-02 (película) en
1.00, lo cual resultaba coherente, porque rechazar un tema ajeno es más
inequívoco que interpretar un saludo.

**La corrida del 27 deshace esa refutación.** Los mismos doce mensajes, el
mismo clasificador, el mismo `temperature=0`:

```
valores observados: [0.95]
```

Un único valor en los doce casos, incluidos los dos que antes se separaban. No
es que el modelo calibre mejor o peor: **es que el valor no es estable entre
corridas sobre entradas idénticas.** Y eso descarta una tercera posibilidad que
la corrida anterior dejaba abierta —que la confianza midiera algo real pero con
poca resolución—: una señal que cambia de 0.90 a 0.95 para el mismo mensaje no
está midiendo una propiedad del mensaje.

La conclusión práctica se refuerza. El umbral que decide si delegar está en
0.50, los valores observados no bajan de 0.90, y ahora se sabe además que el
poco recorrido que parecían tener era ruido. **Como salvaguarda no se acerca a
activarse, y no podría activarse de forma reproducible aunque se recalibrara.**

Eso inclina la decisión pendiente hacia retirar el umbral como puerta y
conservar la confianza solo como señal de traza. Subirlo a 0.93 habría rechazado
MA-01 en una corrida y lo habría aceptado en la otra, que es la peor propiedad
posible en una salvaguarda. Antes de decidirlo hacen falta casos
deliberadamente ambiguos —este conjunto no los tiene— y repetir la medición
varias veces sobre las mismas entradas, que es lo que reveló el problema.

**Lección de método, más allá de la métrica.** Una sola corrida de un sistema
no determinista no distingue una propiedad de un accidente. El marco de
evaluación lleva desde S3-02 registrando los valores de confianza observados
precisamente para poder detectar esto, y solo lo detectó al haber dos corridas
que comparar. Lo mismo vale para el orden de delegación de MA-08 (4.8).

### 4.2 Qué sostiene el prompt y qué sostiene la estructura

El hallazgo más limpio del sprint, y salió de comparar dos corridas del mismo
conjunto con la única diferencia del prompt del Coach.

**Lo que pasó.** Al aplicar la delimitación de dominio de S3-03, el prompt del
Wellness Coach quedó recortado de 105 a 42 líneas. Se perdieron la descripción
de las cuatro herramientas, el manejo de información no cubierta, los límites
de alcance, las restricciones médicas y **las reglas de citación**. Los issues
S3-03 a S3-06 se ejecutaron con esa versión.

Mirando los dos caminos por los que un agente puede acreditar su fuente:

| Caso | Consultó la KB | 22-sep: `fuentes` | 22-sep: prosa | 27-sep: `fuentes` | 27-sep: prosa |
|---|---|---|---|---|---|
| MA-05 | sí | ninguna | ninguno | ninguna | **KB-002** |
| MA-09 | sí | ninguna | ninguno | ninguna | **KB-005, KB-007** |
| MA-10 | sí | ninguna | ninguno | ninguna | ninguno |
| MA-08 | sí | — | — | ninguna | **KB-001** |

En la corrida del 22, buscando el patrón `KB-\d{3}` en el texto de **las doce
respuestas**, no aparece una sola cita. Con el prompt restaurado, tres de los
cuatro casos que consultan la base la citan.

**Esto corrige una afirmación falsa de la versión anterior de este documento**,
que decía que el Coach *«cita los `doc_id` dentro de su prosa»* y atribuía el
hueco a una sola causa. Eran dos:

- **El contrato de salida** (vigente). El ciclo ReAct del Sprint 2 no devuelve
  los `doc_id` como lista, así que `_invocar_wellness_coach` deja `fuentes`
  vacía aunque el agente cite. Se ve en la tabla: la columna estructurada sigue
  vacía el 27 de septiembre. Corregirlo exige cambiar ese contrato.
- **El prompt truncado** (corregido). Sin reglas de citación, el agente no
  citaba en absoluto.

#### Lo que esto le hace a la tesis del sprint

El sprint viene sosteniendo que **las garantías estructurales sobreviven y las
instrucciones del prompt no**. El truncamiento fue un experimento accidental
sobre esa hipótesis, y el resultado es más interesante que un simple sí.

Con el 60 % del prompt ausente, el Coach **siguió** invocando las herramientas
correctas, respetando la frontera de nutrición y sin recuperar KB-006. Eso lo
sostuvieron el filtro de categorías, las descripciones de `FunctionDeclaration`
y el registro de herramientas: estructura, no texto.

Lo único que se cayó fue la citación. Y se cayó porque **en este agente la
citación es lo único que no tiene respaldo estructural**. En el Nutrition Agent
sí lo tiene: `validar_fuentes()` compara lo citado contra lo recuperado sobre
un campo declarado, y descarta lo inventado. En el Coach depende enteramente de
una instrucción en prosa.

Formulado como regla: **lo que se cayó al truncar el prompt es exactamente el
inventario de lo que no está garantizado por construcción.** Es un diagnóstico
que no se obtiene leyendo el código, porque en el código las dos cosas se ven
igual de escritas.

La asimetría de trazabilidad entre ambos agentes sigue en pie y ahora se sabe
que tiene una parte estructural —el contrato de salida— y una parte de
instrucción.

### 4.3 El costo del patrón Supervisor

| | Valor |
|---|---|
| Tiempo de respuesta promedio | 9 602 ms |
| Clasificación promedio | 2 579 ms |
| **Sobrecosto de coordinación** | **≈ 27 %** |
| Peor caso (MA-08, colaboración) | 25 448 ms |
| **Saludo sin delegación (MA-01)** | **2 856 ms** |

El último dato es el más incómodo: **responder «hola» cuesta casi tres segundos
y una llamada al modelo completa**, porque el clasificador se ejecuta antes de
poder decidir que no hay nada que delegar.

Conviene no leer estas cifras con más precisión de la que tienen. Entre las dos
corridas el promedio se movió de 9 294 a 9 602 ms y el saludo de 4 050 a
2 856 ms sobre entradas idénticas: la variabilidad entre corridas es del mismo
orden que las diferencias que uno querría comparar. **Lo que estas cifras
sostienen es el orden de magnitud —segundos, no décimas— y la estructura del
reparto; no una comparación fina entre configuraciones.** Para eso haría falta
la mediana de varias corridas.

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

La corrida del 27 añade un dato: **la laguna se alcanza también sin
preguntarle directamente.** La sub-consulta de nutrición de MA-08 —*«qué comer
antes de una tirada larga»*— cae en el mismo hueco, y el agente volvió a
declararlo. Es decir, no es un caso de prueba rebuscado: es el camino natural
de una consulta mixta cualquiera sobre una tirada larga. Curar un documento de
alimentación previa al ejercicio pasa de mejora deseable a la carencia más
visible de la base de conocimiento.

### 4.8 Citación parcial y orden de delegación variable

Dos observaciones que ninguna comprobación automática marca como fallo y que
conviene no perder.

**Citación parcial en MA-10.** La respuesta de tapering dice *«según la base de
conocimiento de la plataforma, la recomendación general es reducir el volumen
entre un 41 % y un 60 %»*. Atribuye el origen pero no nombra el documento, así
que el lector no puede ir a verificarlo. No es lo mismo que no citar —MA-05
antes de la corrección no mencionaba origen alguno— pero tampoco cumple del
todo el propósito: la ventaja del sistema es la verificabilidad, y una
atribución genérica no se puede verificar. Está a medio camino, y el prompt
restaurado no distingue entre las dos cosas.

**Orden de delegación variable en MA-08.** La corrida del 22 delegó en
`nutrition` y luego en `wellness_coach`; la del 27, al revés, sobre el mismo
mensaje. El orden lo fija el clasificador al partir la consulta, y no es
indiferente: determina qué respuesta sirve de contexto a cuál. En esta corrida
el Coach respondió primero, sin saber lo que diría el especialista en
nutrición.

Ninguna de las dos es incorrecta —el criterio de MA-08 no fija un orden— pero
la variabilidad sí importa: **si el encadenamiento de contexto es lo que
convierte dos respuestas sueltas en colaboración, el orden no debería depender
del azar de una llamada al modelo.** Dos vías, ninguna aplicada: declarar el
orden en el registro de agentes en vez de dejarlo al clasificador, o aceptar
que es indiferente y entonces paralelizar, que además resolvería el peor caso
de latencia de 4.3.

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
| ¿Cuánto costó cada paso? | `latencias.*`, `pasos[].latenciaMs` |

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

La tasa de **delegación exacta** cerró en 100 % (12/12) en las dos corridas,
con un criterio más estricto que el que usó el Sprint 2: igualdad de conjuntos
en lugar de subconjunto, y casos de cero agentes que sí pueden fallar. La
tasa de **calidad** cerró en 12/12 en la corrida del 27, tras corregir dos
expectativas mal escritas del propio conjunto (sección 2).

Que salga limpia a la primera no es casual ni es mérito de esta medición: es
consecuencia de haber verificado cada issue contra servicios reales a medida que
se construía, en lugar de dejar toda la comprobación para el final. Los tres
defectos que el sistema multiagente tuvo —la sobreinvocación por contexto
excesivo, la redundancia en la consolidación, la confusión entre laguna y
degradación— se detectaron y corrigieron dentro de los issues S3-03 y S3-04,
antes de llegar aquí.

Lo que esta evaluación aporta no es tanto el número como las ocho limitaciones
de la sección 4, y de ellas hay dos que ninguna corrida individual habría
producido.

**La primera es 4.2**, que separa lo que sostiene la estructura de lo que
sostiene el prompt. Salió de comparar dos corridas idénticas salvo por un
prompt truncado por accidente: con el 60 % del texto ausente el Coach siguió
invocando bien sus herramientas y respetando la frontera de nutrición, y lo
único que se cayó fue la citación, que es precisamente lo único de su
comportamiento sin respaldo estructural. Lo que se rompe al quitar el prompt
es el inventario de lo que no está garantizado por construcción.

**La segunda es 4.1**, y es de método. La confianza del clasificador dio tres
valores distintos en una corrida y uno solo en la otra, sobre las mismas
entradas y con `temperature=0`. La corrida del 22 sugería una señal con poca
resolución; las dos juntas muestran que no mide una propiedad del mensaje. Una
sola corrida de un sistema no determinista no distingue una propiedad de un
accidente, y lo mismo se aplica al orden de delegación (4.8) y a las cifras de
latencia (4.3).

Ninguna de las dos habría aparecido corriendo el evaluador más veces sobre el
mismo criterio. Aparecieron al leer lo que el conjunto declaraba y contrastarlo
con lo que las trazas mostraban, que es el mismo camino por el que salieron los
hallazgos E y F del Sprint 2.
