# Flujo de Orquestación — Diagramas

**Sprint 3 — Sistemas Multiagente** · Plataforma Inteligente Wellness 2.0 · Equipo 1

Vista gráfica del sistema multiagente. Cada diagrama enlaza al documento donde
se justifica lo que representa.

---

## 1. Arquitectura del sistema multiagente

Las llamadas a Vertex AI se omiten como aristas individuales para no saturar el
diagrama: **el orquestador y los dos agentes especializados invocan a Gemini**,
y el pipeline RAG lo usa además para generar embeddings de consulta.

```mermaid
graph TD
    Cliente["Cliente PWA / API"]

    subgraph Orquestacion["Capa de orquestación"]
        ORQ["Orchestrator Agent<br/>clasifica intención · delega · consolida"]
    end

    subgraph Especializados["Agentes especializados"]
        COACH["Wellness Coach Agent<br/>entrenamiento de running"]
        NUTRI["Nutrition Agent<br/>nutrición del corredor"]
    end

    subgraph Capacidades["Capacidades compartidas — Sprints 1 y 2"]
        MEM["MemoriaConversacional<br/>historial por corredor"]
        REPO["RepositorioCorredor<br/>perfil · sesiones · carga · objetivos"]
        RAG["Pipeline RAG<br/>recuperación con filtro por categoría"]
    end

    subgraph Infra["Infraestructura"]
        FS[("Firestore")]
        CHROMA[("ChromaDB<br/>7 documentos curados")]
        METEO["Open-Meteo"]
    end

    Cliente --> ORQ
    ORQ -->|delega| COACH
    ORQ -->|delega| NUTRI
    COACH -.->|resultado| ORQ
    NUTRI -.->|resultado| ORQ

    COACH --> MEM
    COACH --> REPO
    COACH --> RAG
    COACH --> METEO
    NUTRI --> REPO
    NUTRI --> RAG

    MEM --> FS
    REPO --> FS
    RAG --> CHROMA
```

El `WellnessAgent` del Sprint 1 queda fuera del flujo multiagente —su salida es
JSON estructurado, no conversacional— y conserva su endpoint propio:

```mermaid
graph LR
    Cliente["Cliente PWA / API"]
    LEGACY["WellnessAgent<br/>recomendación de un turno<br/>modos legacy · rag · compare"]
    REPO["RepositorioCorredor"]
    RAG["Pipeline RAG"]

    Cliente -->|endpoint propio| LEGACY
    LEGACY --> REPO
    LEGACY --> RAG
```

> Justificación del roster y de las fronteras:
> `multiagent-architecture.md`

---

## 2. Delegación simple

```mermaid
sequenceDiagram
    actor Corredor
    participant ORQ as Orchestrator
    participant COACH as Wellness Coach
    participant CAP as Capacidades<br/>(Repositorio · RAG · Memoria)

    Corredor->>ORQ: "¿Puedo entrenar fuerte hoy?"
    activate ORQ
    Note over ORQ: Clasifica intención<br/>→ entrenamiento<br/>→ confianza alta
    ORQ->>ORQ: Registra traza:<br/>agente elegido + motivo

    ORQ->>COACH: SolicitudAgente<br/>(user_id, mensaje, contexto)
    activate COACH
    COACH->>CAP: consultar progreso, clima,<br/>base de conocimiento
    CAP-->>COACH: observaciones
    Note over COACH: Ciclo ReAct del Sprint 2
    COACH-->>ORQ: RespuestaAgente<br/>(texto, herramientas, fuentes)
    deactivate COACH

    ORQ-->>Corredor: respuesta + traza
    deactivate ORQ
```

---

## 3. Colaboración entre agentes

El caso MA-08 de la evaluación, con el reparto real que produjo el clasificador.

```mermaid
sequenceDiagram
    actor Corredor
    participant ORQ as Orchestrator
    participant NUTRI as Nutrition Agent
    participant COACH as Wellness Coach

    Corredor->>ORQ: "¿Qué como antes de una tirada larga<br/>y cómo ajusto el entrenamiento esta semana?"
    activate ORQ
    Note over ORQ: Intención mixta<br/>Reparte la consulta

    ORQ->>NUTRI: "¿Qué debo comer antes<br/>de una tirada larga?"
    activate NUTRI
    NUTRI-->>ORQ: RespuestaAgente (KB-006)
    deactivate NUTRI

    Note over ORQ: contexto = respuesta de nutrición

    ORQ->>COACH: "¿Cómo debo ajustar mi entrenamiento<br/>esta semana, considerando que tengo<br/>una tirada larga?"
    activate COACH
    COACH-->>ORQ: RespuestaAgente (progreso + KB)
    deactivate COACH

    Note over ORQ: Consolida sin reescribir,<br/>atribuyendo cada parte
    ORQ-->>Corredor: respuesta consolidada + traza de 2 pasos
    deactivate ORQ
```

Obsérvese que la sub-consulta de entrenamiento **conserva que hay una tirada
larga prevista**, aunque ese detalle apareciera en la frase nutricional del
mensaje original. Sin esa regla, repartir empeoraría la respuesta en vez de
mejorarla.

> Las tres reglas del reparto: `docs/orchestration/delegation-rules.md`,
> sección 3.

---

## 4. Árbol de decisión de delegación

```mermaid
flowchart TD
    A[Solicitud del corredor] --> B[Clasificación de intención<br/>LLM con salida estructurada]
    B --> C{¿Confianza ≥ 0.5?}

    C -->|no| H[Pedir aclaración<br/>sin delegar]
    C -->|sí| D{¿Intención?}

    D -->|entrenamiento| E1[Delegar en Wellness Coach]
    D -->|nutrición| E2[Delegar en Nutrition]
    D -->|mixta| F[Repartir la consulta<br/>y delegar en secuencia]
    D -->|fuera de dominio| G[Redirigir sin delegar]
    D -->|no reconocida| H
    D -->|dominio sin agente| I[Declararlo sin delegar]

    E1 --> J[Recibir resultado]
    E2 --> J
    F --> K[Consolidar con atribución]
    K --> J

    J --> L{¿El agente<br/>respondió?}
    L -->|sí| M[Devolver respuesta + traza]
    L -->|error| N[Respuesta degradada<br/>declarando qué no se pudo consultar]

    G --> M
    H --> M
    I --> M
    N --> M
```

> Los cinco motivos de no delegación y el orden de las comprobaciones:
> `docs/orchestration/delegation-rules.md`, sección 2.

---

## 5. Documentos relacionados

| Tema | Documento |
|---|---|
| Arquitectura y roster de agentes | `multiagent-architecture.md` |
| Justificación del patrón Supervisor | `docs/orchestration/orchestration-pattern.md` |
| El componente orquestador | `docs/orchestration/orchestrator-agent.md` |
| Política de delegación | `docs/orchestration/delegation-rules.md` |
| Contrato de mensajes | `docs/orchestration/communication-flow.md` |
| Integraciones de datos | `integraciones-datos.md` |
