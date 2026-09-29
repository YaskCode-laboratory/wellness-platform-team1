# Documentación — Plataforma Inteligente Wellness 2.0

Índice de la documentación técnica del proyecto. **Equipo 1** — Sistemas
Inteligentes, Maestría en TIC, Universidad del Zulia.

Caso de estudio: **RunCoach AI**, una PWA de entrenamiento de running que
evoluciona a lo largo de tres sprints desde un agente de recomendación hasta un
sistema multiagente coordinado.

---

## Por dónde empezar

| Si quieres… | Lee |
|---|---|
| Entender el sistema completo | `architecture/system-overview.md` |
| Ponerlo a correr en local | `deployment/local-setup.md` |
| Ver cómo se coordinan los agentes | `orchestration/orchestration-pattern.md` |
| Saber qué tan bien funciona | `evaluation/multiagent-evaluation.md` |
| Leer el cierre de un sprint | `reports/sprint-{1,2,3}-report.md` |

---

## Arquitectura

| Documento | Qué cubre | Sprint |
|---|---|---|
| `architecture/system-overview.md` | Vista general de la plataforma | 1 |
| `architecture/rag-architecture.md` | Pipeline RAG, modo dual legacy/RAG, endpoint comparativo | 1 |
| `architecture/agent-architecture.md` | Agente conversacional: memoria, herramientas, ciclo ReAct | 2 |
| `architecture/multiagent-architecture.md` | Roster de agentes, fronteras de responsabilidad, decisiones | 3 |
| `architecture/orchestration-flow.md` | Diagramas del flujo multiagente | 3 |
| `architecture/integraciones-datos.md` | Firestore, Vertex AI, ChromaDB, Open-Meteo; matriz de acceso por agente | 3 |

## Orquestación

| Documento | Qué cubre |
|---|---|
| `orchestration/orchestration-pattern.md` | Patrón Supervisor: evaluación de alternativas y justificación |
| `orchestration/orchestrator-agent.md` | El componente: responsabilidades, clasificación, errores, traza |
| `orchestration/delegation-rules.md` | Cuándo delegar, en quién, con qué mensaje y en qué orden |
| `orchestration/communication-flow.md` | Contrato de mensajes entre orquestador y agentes |
| `orchestration/mcp.md` | Evolución hacia Model Context Protocol (análisis, sin implementación) |
| `orchestration/a2a.md` | Evolución hacia Agent-to-Agent (análisis, sin implementación) |

## Agentes

| Documento | Qué cubre |
|---|---|
| `agents/wellness-agent.md` | Wellness Coach: el agente especializado del equipo |
| `agents/nutrition-agent.md` | Nutrition Agent: segundo participante del sistema multiagente |
| `agents/prompts.md` | Diseño de los prompts y su evolución |

## RAG y conocimiento

| Documento | Qué cubre |
|---|---|
| `rag/knowledge-sources.md` | Curación de las fuentes documentales |
| `rag/document-curation.md` | Criterios de inclusión y nivel de evidencia |
| `rag/chunking-strategy.md` | Estrategia de fragmentación híbrida |
| `rag/embeddings-strategy.md` | Modelo, dimensiones y `task_type` |
| `rag/vector-database.md` | ChromaDB: espacio coseno, metadata, idempotencia |
| `rag/retrieval-pipeline.md` | Recuperación y filtrado por categoría |
| `rag/rag-evaluation.md` | Métricas de recuperación |
| `knowledge/ontology.md` | Ontología del dominio |
| `knowledge/taxonomy.md` | Taxonomía: las siete categorías |
| `knowledge/domain-map.md` | Mapa del dominio de conocimiento |

## Evaluación

| Documento | Qué cubre |
|---|---|
| `evaluation/retrieval-metrics.md` | Precision@k, Recall@k, MRR sobre el golden set del Sprint 1 |
| `evaluation/response-quality.md` | Calidad de las respuestas generadas |
| `evaluation/test-cases.md` | Diseño de los conjuntos de prueba |
| `evaluation/agent-evaluation.md` | Evaluación del agente conversacional: cinco rondas, seis hallazgos |
| `evaluation/multiagent-evaluation.md` | Evaluación del flujo multiagente y su observabilidad |
| `evaluation/hallazgo-E-*.md` | Hallazgo E: preguntar en vez de consultar |
| `evaluation/hallazgo-F-*.md` | Hallazgo F: desplazamiento del patrón tras corregirlo |

## Despliegue

| Documento | Qué cubre |
|---|---|
| `deployment/local-setup.md` | Puesta en marcha en local |
| `deployment/environment-variables.md` | Variables de entorno y credenciales |

## Proyecto

| Documento | Qué cubre |
|---|---|
| `project/scope.md` | Alcance del proyecto |
| `project/roadmap.md` | Evolución por sprints |
| `project/team.md` | Integrantes y reparto de responsabilidades |
| `reports/sprint-1-report.md` | Cierre del Sprint 1 — RAG e ingeniería del conocimiento |
| `reports/sprint-2-report.md` | Cierre del Sprint 2 — agentes inteligentes |
| `reports/sprint-3-report.md` | Cierre del Sprint 3 — sistemas multiagente |

---

## Rutas del scaffold sin usar

El repositorio se creó a partir de un scaffold que reserva rutas para
documentación que este equipo **no ha producido**. Se declaran aquí en lugar de
dejarlas como archivos vacíos sin explicación, o de rellenarlas con contenido
que no corresponde a trabajo realizado.

| Ruta | Por qué está vacía |
|---|---|
| `agents/motivation-agent.md` | El Motivation Agent no fue asignado a este equipo. Está en el roadmap de la plataforma, no en los issues de ningún sprint nuestro |
| `agents/analytics-agent.md` | Igual que el anterior. Sería además el consumidor natural de BigQuery, cuya no aplicación se argumenta en `architecture/integraciones-datos.md` §10 |
| `agents/tools.md` | Las cuatro herramientas del Wellness Coach están documentadas en `agents/wellness-agent.md`, junto al ciclo que las invoca. Separarlas de su contexto no aportaría |
| `agents/memory.md` | La memoria conversacional está documentada en `architecture/agent-architecture.md` §3, donde se explica junto a la decisión de no persistir el `ChatSession` del SDK |
| `architecture/cloud-architecture.md` | El sistema corre en local contra servicios gestionados de GCP. No se desplegó en Cloud Run, así que no hay arquitectura de nube que documentar |
| `architecture/data-architecture.md` | El modelo de datos está en `architecture/integraciones-datos.md` §3, con las colecciones de Firestore y quién escribe y lee cada una |
| `architecture/adr/README.md` | Las decisiones arquitectónicas se registran en tablas dentro de cada documento de arquitectura, con su alternativa descartada y el motivo, en lugar de en ADR individuales. Ver `multiagent-architecture.md` §4 |
| `deployment/cloud-deployment.md` | No se realizó despliegue en la nube. La puesta en marcha en local está en `deployment/local-setup.md` |
| `requirements/*.md` | Los requisitos del proyecto los definió la cátedra en los issues de cada sprint, con sus criterios de aceptación. No se solicitó un documento de requisitos como entregable en ningún sprint |
| `reports/final-report.md` | Corresponde al proyecto final integrador, posterior a los tres sprints técnicos |

Si la cátedra espera contenido en alguna de estas rutas, agradecemos que nos lo
indique: la decisión de no llenarlas fue deliberada y es reversible.
