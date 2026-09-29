# Patrón de Orquestación

**Sprint 3 — Sistemas Multiagente** · Plataforma Inteligente Wellness 2.0 · Equipo 1

Decisión del patrón de coordinación entre agentes, con la evaluación de las
alternativas y la evidencia que respalda la elección.

---

## 1. Los cuatro patrones evaluados

| Patrón | Qué supone | Ajuste |
|---|---|---|
| **Sequential** | Un pipeline fijo por el que pasan todas las solicitudes | **No.** La ruta depende de la intención: una pregunta de entrenamiento no debe atravesar el agente de nutrición |
| **Hierarchical** | Supervisores anidados que coordinan subgrupos de agentes | **No.** Con dos agentes especializados no hay subgrupos que anidar; añade una capa sin contenido |
| **Swarm** | Los agentes se pasan el control entre sí, sin punto central | **No.** Ver 1.1 |
| **Supervisor** | Un coordinador central recibe, decide, delega y devuelve | **Adoptado.** Ver 2 |

### 1.1 Por qué Swarm queda descartado

Es la alternativa que más merece argumento, porque en abstracto es atractiva:
los agentes se coordinan entre sí sin un cuello de botella.

El problema es que **sin un punto central de decisión, reconstruir el recorrido
de una solicitud exige correlacionar registros emitidos por agentes
distintos**. El criterio de aceptación de S3-06 pide *«trazabilidad suficiente
para comprender el recorrido de una solicitud»*, de modo que Swarm juega en
contra de un objetivo explícito del propio sprint.

A eso se suma que la delegación horizontal introduce el problema de los ciclos
—un agente que delega en otro que delega de vuelta— que con Supervisor no
existe por construcción.

---

## 2. Supervisor: justificación

Tres razones, en orden de peso.

### 2.1 Un solo punto de decisión produce un solo punto de traza

Cada solicitud atraviesa el orquestador al entrar y al salir. La traza completa
—intención detectada, agente elegido, motivo de la elección, qué se le pidió a
cada uno, resultado y latencias— se construye en un único lugar.

Responder *«¿qué pasó con esta solicitud?»* es leer un documento, no
correlacionar varios.

### 2.2 La lógica de coordinación queda separada de la de los agentes

Criterio de aceptación explícito de S3-02. Los agentes especializados **no
necesitan saber que existen otros agentes**: reciben una solicitud y devuelven
una respuesta. Quién los llamó y qué se hace con el resultado no es asunto suyo.

Eso se sostiene en la práctica con los adaptadores del registro, que traducen
entre el contrato del orquestador y la forma interna de cada agente. Ver
`delegation-rules.md`.

### 2.3 Es la elevación natural de lo que el sistema ya hacía

El ciclo ReAct del Sprint 2 ya es un supervisor en pequeño: un bucle central que
decide qué herramienta invocar, la despacha y procesa su observación. El Sprint
3 eleva ese mismo patrón un nivel — de herramientas a agentes.

La continuidad conceptual no es casual y facilita razonar sobre el sistema
completo: quien entiende el ciclo de herramientas entiende el de agentes.

---

## 3. Contrapartidas asumidas

El patrón no es gratis y sus costos están medidos, no estimados.

### 3.1 Punto único de fallo

El orquestador es obligatorio en toda solicitud. Se mitiga con el manejo de
errores documentado en `orchestrator-agent.md`: el clasificador nunca lanza
excepción, los fallos de agente se contienen en el punto de despacho, y el
registro de trazas es auxiliar.

### 3.2 Una llamada al modelo por solicitud, antes de poder decidir nada

Medido sobre los doce casos de S3-06:

| | Valor |
|---|---|
| Latencia total promedio | 9 294 ms |
| Clasificación promedio | 2 923 ms |
| **Sobrecosto de coordinación** | **≈ 31 %** |
| Saludo sin delegación (MA-01) | 4 050 ms |

El último dato es el que mejor expone el costo: **responder «hola» cuesta cuatro
segundos y una llamada al modelo completa**, porque el clasificador se ejecuta
antes de poder decidir que no hay nada que delegar.

S3-01 anunció que este costo se mediría y se reportaría como precio del patrón.
Las dos vías de mejora consideradas y no aplicadas están en
`docs/evaluation/multiagent-evaluation.md`, sección 4.3.

---

## 4. Sobre frameworks de orquestación

El informe del Sprint 2 dejó anotado que el Sprint 3 sería el momento de
reconsiderar LangGraph, descartado entonces por un conflicto de dependencias con
`firebase-admin` sobre `google-cloud-storage`.

Reevaluado con el alcance real del sprint —dos agentes especializados y un
Supervisor sin estado compartido entre pasos— **la conclusión se mantiene**: el
grafo que LangGraph construiría tiene tres nodos y dos aristas. Se implementa en
menos código del que costaría la integración, y el conflicto de dependencias
sigue vigente.

La decisión se revisaría con un roster mayor, ramificación condicional compleja,
o necesidad de estado persistente entre pasos del grafo. Se registra aquí para
que la reevaluación futura parta de un criterio y no de una preferencia.

---

## 5. Documentos relacionados

| Tema | Documento |
|---|---|
| Arquitectura general y roster de agentes | `docs/architecture/multiagent-architecture.md` |
| Diagramas del flujo | `docs/architecture/orchestration-flow.md` |
| El componente orquestador | `orchestrator-agent.md` |
| Política de delegación | `delegation-rules.md` |
| Contrato de mensajes | `communication-flow.md` |
| Resultados de la evaluación | `docs/evaluation/multiagent-evaluation.md` |
