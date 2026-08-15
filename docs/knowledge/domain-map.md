# Mapa de Conocimiento del Dominio Wellness

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

---

## 1. Delimitación del dominio

El dominio modelado es el **entrenamiento de resistencia aplicado a la carrera a pie**, acotado a la toma de decisiones sobre carga, intensidad y recuperación de un corredor individual.

Se incluye dentro del alcance:

- Cuantificación y progresión de la carga de entrenamiento
- Clasificación fisiológica de la intensidad
- Distribución de intensidad a lo largo del macrociclo
- Prevención de lesiones por sobreuso asociadas a errores de carga
- Puesta a punto previa a competición
- Soporte nutricional y de recuperación

Queda fuera del alcance el diagnóstico clínico, la prescripción de tratamiento de lesiones establecidas y la biomecánica instrumentada.

---

## 2. Modelo conceptual

```mermaid
graph TD
    C[Corredor]
    S[Sesión]
    CE[Carga de Entrenamiento]
    Z[Zona de Intensidad]
    O[Objetivo]
    F[Fase de Entrenamiento]
    L[Lesión]
    R[Recomendación]
    FC[Fuente de Conocimiento]

    C -->|ejecuta| S
    S -->|se desarrolla en| Z
    S -->|acumula| CE
    C -->|persigue| O
    O -->|determina| F
    CE -->|incrementa riesgo de| L
    L -->|predispone a| L
    C -->|modula umbrales de| CE
    F -->|condiciona| R
    CE -->|informa| R
    C -->|recibe| R
    R -->|fundamentada en| FC

    style C fill:#e0f2fe,stroke:#0284c7
    style R fill:#fef3c7,stroke:#d97706
    style FC fill:#dcfce7,stroke:#16a34a
    style CE fill:#fee2e2,stroke:#dc2626
    style L fill:#fee2e2,stroke:#dc2626
```

La relación `Recomendación → fundamentada en → Fuente de Conocimiento` es la que materializa el aporte de RAG. En la arquitectura previa esa arista no existía: las recomendaciones se generaban sin trazabilidad a conocimiento curado.

---

## 3. Jerarquía de conceptos

### 3.1 Eje de intensidad

La intensidad se organiza alrededor de dos umbrales fisiológicos de lactato:

| Umbral | Definición | Zonas asociadas |
|--------|-----------|-----------------|
| **LT1** | Primer umbral de lactato. Punto en que la lactatemia comienza a elevarse sobre el nivel basal | Z1, Z2 quedan por debajo |
| **LT2** | Segundo umbral. Velocidad más lenta que produce un incremento súbito y sostenido de lactato | Z5 queda por encima |

```mermaid
graph LR
    Z1[Z1 Recuperación] --> Z2[Z2 Base aeróbica]
    Z2 --> LT1{LT1}
    LT1 --> Z3[Z3 Aeróbico medio]
    Z3 --> Z4[Z4 Umbral]
    Z4 --> LT2{LT2}
    LT2 --> Z5[Z5 VO2 máximo]

    style LT1 fill:#fef3c7,stroke:#d97706
    style LT2 fill:#fee2e2,stroke:#dc2626
```

La asignación de zonas mediante porcentajes de frecuencia cardíaca es una aproximación. La variabilidad interindividual en la FC correspondiente a LT1 y LT2 es sustancial, por lo que los rangos de la taxonomía son referenciales.

### 3.2 Eje temporal

```mermaid
graph LR
    B[Base<br/>12+ semanas] --> CO[Construcción<br/>4-12 semanas]
    CO --> TA[Tapering<br/>0-3 semanas]
    TA --> M((Meta))
    M --> TR[Transición<br/>0-3 semanas]

    style TA fill:#dcfce7,stroke:#16a34a
    style M fill:#0437AB,color:#fff
```

### 3.3 Eje de carga

```mermaid
graph TD
    S[Sesiones registradas] --> CA[Carga aguda<br/>7 días]
    S --> CC[Carga crónica<br/>28 días]
    CA --> ACWR[ACWR<br/>aguda / crónica]
    CC --> ACWR
    S --> PS[Pico de sesión<br/>individual]
    S --> VS[Variación semanal %]

    ACWR --> RI[Evaluación de riesgo]
    PS --> RI
    VS -.evidencia débil.-> RI

    style ACWR fill:#dcfce7,stroke:#16a34a
    style VS fill:#fef2f2,stroke:#fca5a5,stroke-dasharray: 4 3
    style RI fill:#fee2e2,stroke:#dc2626
```

La arista discontinua señala que la variación porcentual semanal — base de la clásica regla del 10% — tiene soporte de evidencia sustancialmente más débil que el ACWR y el control de picos de sesión individual.

---

## 4. Fuentes de conocimiento por categoría

| Categoría | Documento KB | Nivel de evidencia predominante |
|-----------|--------------|--------------------------------|
| Carga de entrenamiento | `carga-entrenamiento-progresion.md` | Moderado / Práctica consolidada |
| Zonas fisiológicas | `zonas-intensidad-umbrales.md` | Alto |
| Distribución de intensidad | `distribucion-intensidad-polarizado.md` | Alto |
| Prevención de lesiones | `prevencion-lesiones-sobreuso.md` | Moderado |
| Tapering | `tapering-puesta-a-punto.md` | Alto |
| Nutrición | `nutricion-corredor.md` | Alto |
| Recuperación | `recuperacion-sueno.md` | Moderado |

---

## 5. Conocimiento simbólico explícito

Además del conocimiento documental recuperable vía RAG, el modelo declara cinco axiomas de inferencia en la ontología (`AX-01` a `AX-05`). Representan reglas de decisión que el agente aplica de forma determinista, complementando la recuperación semántica.

Esta convivencia entre **representación simbólica** (axiomas, taxonomía) y **representación distribuida** (embeddings, recuperación semántica) es deliberada: el sistema no sustituye una por la otra sino que las articula.

---

## 6. Caso testigo: la regla del 10%

El sistema previo a este sprint codificaba de forma rígida la regla del 10% — no incrementar el volumen semanal más de un 10% respecto a la semana anterior. Esta regla es un caso instructivo de **práctica consolidada sin respaldo fuerte**:

- No procede de un estudio fundacional; se popularizó en literatura de divulgación de los años 80
- Un estudio con 486 corredores novatos no encontró diferencia en la incidencia de lesión entre un programa con incrementos graduados al 10% y un programa estándar
- Análisis posteriores no hallaron diferencia entre incrementos del 10% y del 24%
- La regla trata todo volumen como equivalente, ignorando que 10% más de rodaje suave no impone el mismo estrés que 10% más de trabajo de calidad

La knowledge base documenta la regla, su origen, la evidencia que la cuestiona y las alternativas mejor sustentadas (ACWR, control de picos de sesión individual, modulación por nivel del corredor). Este caso se emplea como demostración del contraste entre el flujo *legacy* y el flujo *RAG*.

---

## Referencias

Ver `docs/rag/knowledge-sources.md` para el detalle completo de fuentes consultadas por documento.
