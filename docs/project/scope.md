# Alcance del Proyecto

**Plataforma Inteligente Wellness 2.0 — Equipo 1**
Sistemas Inteligentes · Maestría en TIC · Universidad del Zulia

---

## 1. Descripción

Plataforma de gestión de entrenamiento con recomendaciones generadas por inteligencia artificial fundamentadas en conocimiento especializado.

El usuario registra sus sesiones de entrenamiento y define objetivos de volumen. El sistema analiza su carga, recupera conocimiento pertinente de una base curada y genera recomendaciones personalizadas con fuentes verificables.

---

## 2. Dominio de aplicación

El dominio modelado es el **entrenamiento de resistencia aplicado a la carrera a pie**, acotado a la toma de decisiones sobre carga, intensidad y recuperación de un corredor individual.

### Dentro del alcance

- Cuantificación y progresión de la carga de entrenamiento
- Clasificación fisiológica de la intensidad
- Distribución de intensidad a lo largo del macrociclo
- Prevención de lesiones por sobreuso asociadas a errores de carga
- Puesta a punto previa a competición
- Soporte nutricional y de recuperación

### Fuera del alcance

- Diagnóstico clínico de lesiones
- Prescripción de tratamiento de lesiones establecidas
- Biomecánica instrumentada y análisis de la técnica de carrera
- Prescripción nutricional individualizada
- Poblaciones con condiciones médicas particulares

### Límite explícito del sistema

El sistema ofrece **orientación basada en conocimiento documentado**, no asesoramiento médico ni nutricional individualizado. Ante indicios de lesión establecida, deficiencia energética u otras condiciones que requieran valoración profesional, la respuesta apropiada es sugerir consulta con un especialista.

Este límite está codificado en la knowledge base y se refleja en las recomendaciones generadas.

---

## 3. Alcance por sprint

### Sprint 1 — Ingeniería del Conocimiento y RAG ✅

Transformar el agente heredado en un sistema basado en conocimiento.

- Modelo de conocimiento: ontología, taxonomía, mapa de dominio
- Base de conocimiento curada con fuentes verificables
- Pipeline RAG: ingesta, indexación, recuperación, generación
- Evaluación de recuperación con conjunto de referencia

### Sprint 2 — Agentes Inteligentes Modernos

Dotar al agente de capacidad de razonamiento y uso de herramientas.

- Refactorización del Wellness Agent
- Memoria conversacional
- Tool calling e integración de herramientas externas
- Patrón ReAct
- Evaluación del comportamiento del agente

### Sprint 3 — Sistemas Multiagente

Construir una plataforma multiagente coordinada.

- Orchestrator Agent
- Agentes especializados: nutrición, analítica, motivación
- Comunicación y delegación entre agentes
- Evaluación del flujo multiagente

---

## 4. Usuarios

| Perfil | Necesidad |
|---|---|
| Corredor principiante | Progresión segura, prevención de lesiones, construcción de base |
| Corredor intermedio | Optimización de la distribución de intensidad, progresión sostenida |
| Corredor avanzado | Periodización, puesta a punto, gestión de carga elevada |

El sistema modula sus recomendaciones según el nivel declarado, dado que los umbrales de progresión tolerables no son universales.

---

## 5. Restricciones

### Técnicas

- Infraestructura Google Cloud Platform, proyecto `runcoach-ai-496921`
- Modelos de Vertex AI: Gemini 2.5 Flash y `text-embedding-004`
- Persistencia en Cloud Firestore
- Base vectorial embebida, sin servicio dedicado

### De datos

El modelo de datos heredado define los objetivos como **metas de volumen periódico** (`kmMeta`, `tipo`), sin fecha de competición. Esta restricción impide derivar la fase de entrenamiento y aplicar el conocimiento sobre tapering, según se documenta en `docs/knowledge/ontology.md`.

### Académicas

Tres sprints con entregables definidos por la cátedra, más proyecto final integrador.

---

## 6. Supuestos

- El usuario registra sus sesiones con distancia y fecha
- El usuario declara su nivel al crear el perfil
- El corpus de conocimiento se mantiene manualmente
- El volumen de datos por usuario permite resolución en memoria de filtros y ordenaciones

---

## 7. Criterios de aceptación del Sprint 1

| Criterio | Estado |
|---|---|
| Modelo de conocimiento formalizado y documentado | ✅ |
| Base de conocimiento con fuentes verificables | ✅ |
| Pipeline RAG operativo end-to-end | ✅ |
| Recuperación evaluada con métricas estándar | ✅ |
| Recomendaciones con fuentes citadas y trazables | ✅ |
| Evaluación cuantitativa de calidad de respuesta | ⚠️ Parcial |
