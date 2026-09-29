# Arquitectura Multiagente — Sprint 3

**Sprint técnico 3: Sistemas Multiagente**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Vista general del sistema multiagente: qué agentes lo componen, qué responde
cada uno y cómo se relaciona con lo construido en los sprints anteriores.

Complementa a `rag-architecture.md` (Sprint 1, pipeline RAG y modo dual) y a
`agent-architecture.md` (Sprint 2, agente conversacional con memoria,
herramientas y ReAct). Ninguno de los dos se reemplaza: el Sprint 3 los
coordina.

> **Dónde está cada cosa.** Este documento cubre el roster y las fronteras. El
> patrón de orquestación y su justificación están en
> `docs/orchestration/orchestration-pattern.md`; los diagramas, en
> `orchestration-flow.md`; la política de delegación, en
> `docs/orchestration/delegation-rules.md`; el contrato de mensajes, en
> `docs/orchestration/communication-flow.md`.

---

## 1. Punto de partida

Al cierre del Sprint 2 la plataforma tenía dos agentes que no se conocían entre
sí, y un componente de acceso a datos que ambos compartían.

| Componente | Origen | Qué hace |
|---|---|---|
| `WellnessAgent` | Sprint 1 | Recomendación de un turno, modos `legacy` y `rag` |
| `WellnessCoachAgent` | Sprint 2 | Conversación con memoria, 4 herramientas, ciclo ReAct |
| `RepositorioCorredor` | Sprint 2 (#10) | Acceso a perfil, sesiones, carga semanal y objetivos |
| Pipeline RAG | Sprint 1 | Recuperación sobre 7 documentos curados, con filtro por categoría |

La entrada al sistema era directa: el cliente sabía a qué endpoint llamar. No
existía ningún componente que decidiera qué agente debe atender una solicitud,
porque hasta entonces la respuesta era obvia.

**El Sprint 3 introduce esa decisión**, y con ella el problema de coordinación
que define un sistema multiagente.

---

## 2. Agentes del sistema

### 2.1 Roster y responsabilidades

| Agente | Responsabilidad | Fuera de su alcance |
|---|---|---|
| **Orchestrator Agent** | Recibir la solicitud, determinar la intención, delegar en el agente competente, consolidar y devolver. Emitir por sí mismo las respuestas de control del flujo | No genera respuestas especializadas de dominio ni consulta la base de conocimiento |
| **Wellness Coach Agent** | Entrenamiento de running: carga, intensidad, lesiones, tapering, recuperación, progreso del corredor | Nutrición, hidratación y pautas alimentarias |
| **Nutrition Agent** | Nutrición del corredor: ingesta, hidratación, pautas antes/durante/después del entrenamiento | Prescripción de entrenamiento y análisis de carga |

La fila del orquestador distingue dos cosas que conviene no confundir. El
orquestador **sí** produce texto dirigido al corredor en tres situaciones, todas
de control del flujo: cuando no reconoce la intención y pide aclaración, cuando
la consulta queda fuera del dominio de la plataforma y redirige, y cuando un
agente falla y hay que declararlo. Son respuestas fijas, no generadas, y su
contenido es sobre la conversación, no sobre running.

Lo que **no** hace es producir contenido especializado: no responde una pregunta
de entrenamiento ni de nutrición, no consulta la base de conocimiento, no accede
a los datos del corredor y no reescribe lo que dicen los agentes. Esa es la
frontera que lo mantiene siendo un coordinador. Si empezara a resolver casos por
su cuenta, el sistema tendría la lógica de dominio repartida entre el
coordinador y los especialistas, que es precisamente lo que el patrón Supervisor
busca evitar. Las cuatro situaciones previstas y su respuesta están en
[`docs/orchestration/orchestrator-agent.md`](../orchestration/orchestrator-agent.md).

El **Wellness Coach** es el agente especializado asignado a este equipo, ya
construido en el Sprint 2. El trabajo de S3-03 no fue crearlo sino **darle
frontera**: convertirlo de *el* agente en *un* agente con límites.

El **Nutrition Agent** se incorpora como segundo participante porque los
criterios de aceptación de S3-04 y S3-06 exigen un escenario verificable de
colaboración entre agentes, y con un único agente especializado la delegación
degenera en un enrutador con un solo destino. Se declara explícitamente como
pieza de soporte del ejercicio multiagente, no como un segundo entregable de
especialización. Detalle en `docs/agents/nutrition-agent.md`.

### 2.2 El WellnessAgent del Sprint 1 queda fuera

Su salida es un JSON estructurado que el frontend renderiza como tarjeta, no una
respuesta conversacional: incorporarlo al flujo de delegación mezclaría dos
contratos de salida distintos sin beneficio.

Sigue accesible por su endpoint propio, incluido `/compare`, que es el que
sostiene la comparación empírica legacy vs. RAG del Sprint 1.

---

## 3. La frontera de responsabilidad es estructural

El criterio de aceptación de S3-03 exige que cada agente *«evite asumir
responsabilidades correspondientes a otros agentes»*. La forma directa de
lograrlo es instruirlo en el prompt. **No es suficiente**, y el Sprint 2 lo
demostró: los hallazgos E y F documentan tres rondas de medición corrigiendo un
comportamiento que el prompt describía correctamente y el modelo aplicaba a su
manera.

La arquitectura aplica la frontera **en el acceso a datos**, donde el modelo no
tiene margen de interpretación. Las siete categorías de la taxonomía del Sprint
1 se reparten entre los dos agentes:

| Agente | Categorías accesibles | Documentos |
|---|---|---|
| Wellness Coach | `carga_entrenamiento`, `zonas_fisiologicas`, `distribucion_intensidad`, `prevencion_lesiones`, `tapering`, `recuperacion` | KB-001…005, KB-007 |
| Nutrition | `nutricion` | KB-006 |

La herramienta de conocimiento de cada agente aplica su conjunto propio, de modo
que **el Coach no puede citar KB-006 aunque el prompt fallara**: esos fragmentos
no llegan a su contexto.

Evidencia, con la misma consulta nutricional bajo los dos filtros:

```
"cuantos carbohidratos debo consumir durante una tirada larga"

dominio del Coach      KB-001  carga_entrenamiento   sim 0.604
                       KB-005  tapering              sim 0.600
                       KB-005  tapering              sim 0.598

dominio de nutrición   KB-006  nutricion             sim 0.725
                       KB-006  nutricion             sim 0.712
                       KB-006  nutricion             sim 0.686
```

El prompt sigue existiendo y sigue importando —gobierna el tono, la derivación y
el reconocimiento de cuándo una pregunta no le corresponde— pero deja de ser la
única línea de defensa.

### 3.1 El reparto es total y disjunto, y se verifica

`tests/unit/test_acceso_datos.py` comprueba contra el front-matter real de la
knowledge base que ninguna categoría pertenece a dos agentes y que **ninguna
queda sin dueño**.

Lo segundo importa más de lo que parece: un documento nuevo con una categoría no
asignada quedaría irrecuperable —ningún agente lo filtra— y nadie se enteraría
hasta que un corredor preguntara por ese tema y recibiera una respuesta sin
fundamento. Es el tipo de laguna silenciosa que ya apareció dos veces en este
proyecto.

---

## 4. Decisiones arquitectónicas registradas

| # | Decisión | Alternativa descartada | Motivo |
|---|---|---|---|
| D-01 | Patrón Supervisor | Swarm, Sequential, Hierarchical | Trazabilidad centralizada y separación de la lógica de coordinación → `orchestration-pattern.md` |
| D-02 | Clasificación de intención por LLM | Reglas sobre palabras clave | Preguntas mixtas y decisión explicable → `orchestrator-agent.md` §3 |
| D-03 | Frontera de dominio por filtro de categoría | Solo instrucción en el prompt | Garantía estructural; los hallazgos E y F mostraron el límite del prompt |
| D-04 | Nutrition Agent como segundo participante | Un solo agente especializado | Sin un segundo agente no hay colaboración que verificar |
| D-05 | `WellnessAgent` fuera del flujo multiagente | Incorporarlo como tercer agente | Su salida es JSON estructurado, no conversacional |
| D-06 | Los agentes no delegan entre sí | Delegación horizontal | Elimina los ciclos por construcción → `delegation-rules.md` §4 |
| D-07 | SDK directo de Vertex AI | LangGraph | Reevaluado en el Sprint 3 y mantenido → `orchestration-pattern.md` §4 |
| D-08 | Reparto de la consulta por el clasificador | Entregar el mensaje completo a cada agente | Evita derivaciones redundantes entre agentes que responden a la vez → `delegation-rules.md` §3 |
| D-09 | Consolidación sin parafrasear | Que el orquestador redacte una respuesta unificada | Reescribir rompería la correspondencia entre afirmación y fuente validada |

---

## 5. Alcance: qué no incluye este sprint

| Elemento | Estado | Motivo |
|---|---|---|
| **MCP / A2A** | Nota arquitectónica, sin implementación | Lo pide así el issue S3-04 → `docs/orchestration/{mcp,a2a}.md` |
| **BigQuery** | No aplica | El volumen actual se resuelve en Firestore → `integraciones-datos.md` §10 |
| **Agentes Motivation y Analytics** | Directorios vacíos | Fuera de la asignación del equipo |
| **Memoria compartida entre agentes** | No | Cada agente conserva la suya; el contexto viaja por solicitud |

---

## 6. Coherencia con la arquitectura existente

La propuesta no reescribe nada de los sprints anteriores:

- `RepositorioCorredor` se consume igual, sin cambios.
- El ciclo ReAct del `WellnessCoachAgent` se conserva completo, incluidos el
  reintento del hallazgo C y la degradación de S2-04.
- El pipeline RAG se reutiliza; el único cambio es admitir una lista de
  categorías en `recuperar()`.
- La memoria conversacional sigue siendo por corredor y propiedad del Coach.
- El endpoint `/compare` del Sprint 1 sigue funcionando sin tocarlo.
- Ninguna integración externa es nueva → `integraciones-datos.md` §1.

Lo que se agrega es una capa por encima, no una sustitución de lo que hay
debajo.

---

## 7. Mapa de la documentación del Sprint 3

| Tema | Documento |
|---|---|
| Patrón de orquestación y su justificación | `docs/orchestration/orchestration-pattern.md` |
| El componente orquestador | `docs/orchestration/orchestrator-agent.md` |
| Política de delegación y reparto | `docs/orchestration/delegation-rules.md` |
| Contrato de mensajes entre agentes | `docs/orchestration/communication-flow.md` |
| Evolución a MCP | `docs/orchestration/mcp.md` |
| Evolución a A2A | `docs/orchestration/a2a.md` |
| Diagramas del flujo | `orchestration-flow.md` |
| Integraciones de datos y servicios | `integraciones-datos.md` |
| El agente de nutrición | `docs/agents/nutrition-agent.md` |
| El agente de entrenamiento | `docs/agents/wellness-agent.md` |
| Evaluación y observabilidad | `docs/evaluation/multiagent-evaluation.md` |
| Informe de cierre | `docs/reports/sprint-3-report.md` |
