# Arquitectura de Agentes — Sprint 2

**Sprint técnico 2 — Agentes Inteligentes Modernos**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Este documento registra las decisiones arquitectónicas del Sprint 2. Complementa,
sin reemplazar, a `docs/architecture/rag-architecture.md` del Sprint 1: aquel
documenta el pipeline RAG y el modo dual legacy/RAG tal como quedaron al cierre
de ese sprint; este documenta cómo evoluciona esa arquitectura para incorporar
memoria conversacional, herramientas y razonamiento.

Se completa de forma incremental a medida que avanza el sprint. Cada sección
corresponde a uno o más issues del backlog (#10–#16).

---

## 1. Refactorización del Wellness Agent (#10)

### 1.1 Diagnóstico

Al cierre del Sprint 1, `WellnessAgent` (`src/agents/wellness/agent.py`) concentraba
tres responsabilidades distintas en una sola clase:

| Responsabilidad | Métodos afectados |
|---|---|
| Acceso a datos del corredor | `get_user_profile`, `_sesiones_de_usuario`, `get_last_sessions`, `get_weekly_load`, `get_goals`, `_cargar_estado` |
| Generación de recomendación | `_analizar_legacy`, `_analizar_rag`, `build_prompt` |
| Orquestación y persistencia | `analyze`, `comparar` |

Esta mezcla era razonable mientras existía un único agente. Con la incorporación
planeada del Wellness Coach Agent 2.0 (#11), que necesita exactamente el mismo
estado del corredor (sesiones, carga semanal, objetivos, nivel, y el nuevo campo
`ciudad`), mantener el acceso a datos dentro de `WellnessAgent` habría obligado
al agente nuevo a importar al agente legacy solo para reutilizar sus consultas,
o a duplicar cuatro consultas a Firestore con lógica de negocio no trivial
(cálculo de semana ISO, filtrado de objetivos activos).

### 1.2 Decisión: extracción a `RepositorioCorredor`

Se extrajo el acceso a datos a un componente independiente: