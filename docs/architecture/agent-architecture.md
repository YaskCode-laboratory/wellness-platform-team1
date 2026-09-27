# Arquitectura de Agentes — Sprint 2

**Sprint técnico 2 — Agentes Inteligentes Modernos**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Este documento registra las decisiones arquitectónicas del Sprint 2. Complementa,
sin reemplazar, a `docs/architecture/rag-architecture.md` del Sprint 1: aquel
documenta el pipeline RAG y el modo dual legacy/RAG tal como quedaron al cierre
de ese sprint; este documenta cómo evoluciona esa arquitectura para incorporar
memoria conversacional, herramientas y razonamiento.

Cada sección corresponde a uno o más issues del backlog (#10–#16).

---

## 0. Visión general

Al cierre del Sprint 1 la plataforma tenía **un** agente: `WellnessAgent`, que
producía una recomendación de un solo turno, sin estado, en dos modos
comparables entre sí (`legacy` y `rag`).

El Sprint 2 no reemplaza ese agente: agrega un **segundo** agente conversacional
al lado, y extrae lo que ambos comparten.

```
                    ┌─────────────────────────┐
                    │   src/api/routes        │
                    └───────────┬─────────────┘
                                │
              ┌─────────────────┴──────────────────┐
              │                                    │
    ┌─────────▼──────────┐            ┌────────────▼─────────────┐
    │   WellnessAgent    │            │   WellnessCoachAgent     │
    │   (Sprint 1, #10)  │            │   (Sprint 2, #11–#14)    │
    │                    │            │                          │
    │  un turno          │            │  conversacional          │
    │  sin estado        │            │  memoria persistida      │
    │  modos legacy/rag  │            │  tool calling + ReAct    │
    └─────────┬──────────┘            └────────────┬─────────────┘
              │                                    │
              │        ┌───────────────────┐       │
              └───────►│ RepositorioCorredor│◄──────┘
                       │      (#10)         │
                       └─────────┬─────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
        ┌─────▼─────┐     ┌──────▼──────┐   ┌───────▼───────┐
        │ Firestore │     │  ChromaDB   │   │  Vertex AI    │
        │  perfil   │     │  knowledge  │   │  Gemini +     │
        │  sesiones │     │  base (S1)  │   │  embeddings   │
        │  memoria  │     └─────────────┘   └───────────────┘
        └───────────┘
```

Los dos agentes conviven a propósito. El endpoint `/compare` del Sprint 1
sigue funcionando, y con él la comparación empírica legacy vs. RAG que era el
valor agregado de aquel sprint. El agente nuevo no lo invalida: opera en otro
modo de interacción.

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

Se extrajo el acceso a datos a un componente independiente,
`src/data/repositorio_corredor.py`, que expone dos objetos de datos y cuatro
consultas:

| Elemento | Qué es |
|---|---|
| `PerfilCorredor` | dataclass: uid, email, nombre, peso, edad, nivel, ciudad |
| `EstadoCorredor` | dataclass: sesiones, carga actual y anterior, objetivos, nivel, ciudad |
| `obtener_perfil()` | perfil declarado del corredor |
| `obtener_ultimas_sesiones()` | las N sesiones más recientes |
| `calcular_carga_semanal()` | kilometraje de la semana actual y la anterior |
| `obtener_objetivos_activos()` | metas con `activo: true` |

`WellnessAgent` quedó reducido a lo que le corresponde: construir prompts,
generar recomendaciones y orquestar/persistir el resultado. El agente nuevo
consume el mismo repositorio sin conocer al agente viejo.

**Valores por defecto en vez de excepciones.** `PerfilCorredor` no falla cuando
falta un campo: lo sustituye por un valor por defecto. La razón es concreta —
los perfiles creados antes de agregar `ciudad` no tienen ese campo en
Firestore, y un esquema sin migraciones obliga a tolerar documentos de
generaciones distintas. La decisión de qué valor usar está aislada en
`desde_documento()`, un solo lugar.

**Consultas sin índices compuestos.** Se evita deliberadamente combinar `where`
con `order_by`, o varios `where` sobre campos distintos: Firestore exige
índices compuestos para esos casos, y crearlos es configuración manual en la
consola que no queda versionada en el repositorio. Se filtra por `userId` y se
resuelve el resto en memoria. Con decenas de documentos por usuario el costo es
despreciable y elimina una dependencia de configuración externa. Es la misma
decisión que el Sprint 1 documentó en su sección 5.4.

### 1.3 Efecto colateral: el cliente perezoso de Firestore

La extracción destapó un problema que estaba latente. `src/database/firestore_client.py`
ejecutaba `db = init_firebase()` **al importar el módulo**, lo que abría una
conexión real a Firestore por el solo hecho de importar cualquier cosa que
dependiera de él — incluidas las pruebas unitarias, que no deberían tocar la red.

Se introdujo `_ClienteFirestorePerezoso`, una envoltura que retrasa la conexión
hasta el primer uso real. `db.collection(...)` sigue funcionando igual para
quien ya lo usaba así.

Un detalle no obvio del diseño: la envoltura **excluye explícitamente los
nombres que empiezan con guion bajo** de disparar la conexión. `unittest.mock`
consulta varios atributos internos (`__func__`, `_is_coroutine_marker`) antes de
reemplazar un objeto por un mock, y esa consulta pasa por `__getattr__` igual
que un uso real. Sin la exclusión, el solo hecho de mockear el objeto en una
prueba abría una conexión a Firestore.

Esta decisión tuvo una consecuencia positiva no buscada que se hizo visible
mucho después: **es lo que permite que el pipeline de CI corra sin credenciales
de GCP** (sección 7).

---

## 2. Diseño del Wellness Coach Agent 2.0 (#11)

### 2.1 Por qué un segundo agente y no una extensión del primero

`WellnessAgent` responde a una pregunta implícita y siempre la misma: *¿qué
debería entrenar este corredor ahora?* No recibe mensajes, no mantiene estado,
y su salida es un JSON estructurado que el frontend renderiza como tarjeta.

El Coach 2.0 responde a preguntas arbitrarias del corredor, en lenguaje
natural, y puede necesitar varios pasos de razonamiento antes de contestar.
Fusionar ambos comportamientos en una clase habría producido un objeto con dos
contratos de entrada y dos de salida.

| | `WellnessAgent` | `WellnessCoachAgent` |
|---|---|---|
| Entrada | `user_id` | `user_id` + mensaje libre |
| Estado | ninguno | memoria persistida |
| Salida | JSON estructurado | texto conversacional |
| Herramientas | no | cuatro, por tool calling |
| Razonamiento | una llamada al modelo | ciclo ReAct multi-paso |

### 2.2 Decisión de stack: SDK directo sobre framework de agentes

Se evaluó LangChain/LangGraph y se descartó para este sprint, por la misma
razón que el Sprint 1 descartó un wrapper de RAG: la dependencia habría
traído un conflicto de resolución con `firebase-admin` sobre
`google-cloud-storage`, y el beneficio —abstracciones de agente que aquí se
implementan en unas 200 líneas— no lo justificaba.

Se usa `vertexai.generative_models` directamente: `GenerativeModel`,
`ChatSession`, `FunctionDeclaration`, `Tool`.

La contrapartida es real y está registrada como deuda técnica: **ese SDK está
deprecado**, con retiro anunciado para junio de 2026. La migración a
`google-genai` se pospuso para mantener el stack estable durante el sprint.

Para el Sprint 3 la evaluación cambia: coordinar varios agentes
(nutrition, motivation, analytics) sí es el caso de uso donde un framework de
orquestación aporta algo que no se resuelve en 200 líneas.

### 2.3 El prompt de sistema como contrato

El comportamiento del agente no vive solo en el código. `prompts/agents/wellness_coach_agent.txt`
define cuatro bloques que son, en la práctica, parte de la arquitectura:

| Bloque | Qué gobierna |
|---|---|
| Principio de precedencia | Cuándo consultar una herramienta y cuándo preguntarle al corredor |
| Herramientas disponibles | Criterio de uso de cada una |
| Reglas de citación | Solo `doc_id` realmente recibidos de la herramienta |
| Límites de alcance | Dominio de running; nada de diagnóstico médico |

Dos de los seis hallazgos de la evaluación (E y F) se corrigieron
exclusivamente aquí, sin tocar una línea de Python. Es una propiedad
incómoda pero real de esta arquitectura: **parte de la lógica de negocio vive
en un archivo de texto y su verificación es empírica, no determinista.** Ver
sección 8.

---

## 3. Memoria conversacional (#12)

### 3.1 El problema: el SDK no es persistible

`ChatSession` de Vertex AI mantiene el historial en memoria del proceso. No es
serializable a Firestore de forma directa, y cada petición HTTP es stateless.

### 3.2 Decisión: historial propio, inyectado como texto

Se implementó `MemoriaConversacional` (`src/agents/wellness_coach/memory.py`),
que persiste los turnos en Firestore y los inyecta **como texto dentro del
prompt de sistema** de cada conversación nueva. El `ChatSession` se crea y
descarta en cada turno; la continuidad la aporta el texto inyectado.

| Constante | Valor | Por qué |
|---|---|---|
| `MAX_TURNOS_PERSISTIDOS` | 50 | El documento no crece sin límite |
| `VENTANA_CONTEXTO` | 10 | El prompt no se infla con historial completo en cada turno |

La distinción entre ambos números es deliberada: **se guarda más de lo que se
muestra**. Persistir 50 turnos permite auditar la conversación completa;
inyectar solo los 10 últimos mantiene el prompt acotado y el costo por turno
estable.

**Un hilo por corredor** (`conversation_id == user_id`). Gestionar
conversaciones paralelas no lo pedía el issue #12 y habría duplicado el modelo
de datos; queda como extensión futura.

### 3.3 Limitación conocida

La memoria expira **por cantidad de turnos, no por antigüedad**. Una
conversación de hace meses sigue disponible como contexto igual que una de hace
minutos, lo cual puede producir continuidad falsa. Registrado como propuesta de
mejora para el Sprint 3.

---

## 4. Herramientas y Tool Calling (#13)

### 4.1 Las cuatro herramientas

| Herramienta | Fuente de datos | Devuelve |
|---|---|---|
| `consultar_historial_sesiones` | Firestore (vía repositorio) | últimas N sesiones |
| `consultar_progreso_objetivo` | Firestore (vía repositorio) | carga semanal vs. meta |
| `consultar_clima` | Open-Meteo (HTTP) | condiciones de la ciudad del corredor |
| `consultar_base_conocimiento` | ChromaDB (pipeline RAG del Sprint 1) | fragmentos con `doc_id` |

La cuarta es la que conecta los dos sprints: el agente conversacional consulta
**la misma knowledge base curada** que alimenta el modo RAG del agente
original. No hay una segunda base ni una segunda estrategia de recuperación.

### 4.2 `_HERRAMIENTAS` como fuente de verdad

El registro (`src/agents/wellness_coach/tools/registro.py`) define las
herramientas como **diccionarios Python simples**, y construye los objetos del
SDK (`FunctionDeclaration`, `Tool`) solo en el momento de hablar con Gemini.

La razón es concreta: esos objetos están respaldados por protobuf y no
garantizan lectura de vuelta de los valores con los que se construyen. Un
diccionario sí se puede inspeccionar libremente, incluido desde las pruebas.

### 4.3 Parámetros que el modelo no controla

`despachar()` recibe `user_id` y `ciudad` desde el contexto de la conversación,
no desde los argumentos que produce el modelo. El modelo **no puede** —ni
necesita— especificar de qué usuario quiere datos: siempre son los del corredor
que está conversando.

Es una decisión de seguridad además de una simplificación: elimina por
construcción la posibilidad de que un mensaje del usuario induzca al modelo a
consultar datos de otro corredor.

### 4.4 Manejo de errores: del síntoma al principio (S2-04)

La primera versión protegía únicamente `consultar_clima`, y por una razón
empírica: Open-Meteo devolvió un 500 real durante una medición y tumbó la
evaluación completa (hallazgo D). Se corrigió el síntoma medido.

La revisión del PR #25 señaló que la corrección era reactiva: las otras tres
herramientas dependen de Firestore y ChromaDB, y un fallo suyo se propagaba
igual.

**Decisión: proteger el punto de despacho, no cada herramienta.**
`despachar()` es el único lugar por donde pasan las cuatro, presentes y
futuras. `_despachar_con_degradacion()` lo envuelve y convierte cualquier
excepción en una observación controlada.

```
  modelo pide herramienta
          │
          ▼
  _despachar_con_degradacion()
          │
    ┌─────┴─────┐
    │           │
  éxito       fallo
    │           │
    │     logger.exception()  ──► traza completa, para diagnóstico
    │           │
    │     {"disponible": False, "mensaje": ...}
    │           │
    └─────┬─────┘
          ▼
  Part.from_function_response  ──► el modelo sigue razonando
```

Tres decisiones dentro de esa función:

1. **Se reutiliza el contrato `{"disponible": False, "mensaje": ...}`** del
   hallazgo D en vez de inventar una forma de error nueva. El modelo ya
   demostró empíricamente que sabe interpretarlo y seguir conversando con las
   fuentes que sí respondieron; darle un segundo formato para la misma
   situación sería pedirle que aprenda dos convenciones donde basta una.
2. **Se captura `Exception` de forma amplia, a propósito.** El objetivo no es
   anticipar qué puede fallar en Firestore, ChromaDB o un servicio HTTP, sino
   garantizar que nada de lo que pase ahí adentro rompa la conversación. Un
   fallo de infraestructura y un `ValueError` por un nombre de herramienta
   alucinado producen la misma degradación de cara al usuario; la distinción
   vive en el log.
3. **El log lleva el traceback, el modelo no.** Exponer detalles internos de
   la infraestructura en la superficie conversacional no le sirve al corredor
   y filtra información del sistema.

La respuesta del agente expone además `herramientasDegradadas`, para que una
degradación deje rastro medible en vez de producir silenciosamente una
respuesta peor.

---

## 5. Ciclo de razonamiento ReAct (#14)

### 5.1 Bucle manual sobre `send_message()`

El patrón Thought → Action → Observation se implementa como un bucle explícito:
mientras el modelo devuelva llamadas a función, se despachan y se le devuelve
el resultado; se detiene cuando produce texto sin más llamadas, o al alcanzar
`MAX_ITERACIONES_HERRAMIENTAS` (5), que evita ciclos infinitos.

```
  mensaje del corredor
          │
          ▼
   ┌─► send_message ──► ¿hay function_calls?
   │         │                   │
   │         │              sí ──┴── no ──► ¿declara uso sin invocar?
   │         │               │                      │
   │         │               ▼                sí ──┴── no ──► respuesta final
   │         │        despachar cada una       │
   │         │               │            empuje + 1 reintento
   │         └───────────────┘                 │
   └─────────────────────────────────────────  ┘
              (máx. 5 iteraciones)
```

### 5.2 El problema de la herramienta declarada pero no invocada (hallazgo C)

El modelo a veces narra la intención de usar una herramienta (*"voy a consultar
la base de conocimiento"*) o directamente atribuye contenido a ella (*"según la
base de conocimiento…"*) sin emitir una llamada a función real. El ciclo
original cerraba el turno ahí, entregando una promesa incumplida o una
atribución falsa — el mismo problema de cita alucinada del Sprint 1, en otra
superficie.

**Alternativa estructural evaluada y descartada.** `tool_config` con
`FunctionCallingConfig.Mode.ANY` fuerza la llamada en vez de detectarla por
texto. Se descartó por dos razones verificadas contra la documentación del SDK:
`ChatSession.send_message()` no acepta `tool_config` por mensaje, y aplicar
`ANY` a nivel de modelo forzaría una llamada en **cada** turno, incluidos los
que legítimamente no requieren ninguna — rompiendo el comportamiento correcto
de un saludo o de una pregunta fuera de dominio.

**Solución adoptada:** heurística textual con un reintento acotado. Si el
modelo declara sin invocar y todavía no ha despachado nada en el turno, se le
empuja una vez con una instrucción explícita. Si insiste, su texto no se
entrega: se sustituye por una respuesta honesta de que la consulta no pudo
completarse.

La heurística solo se aplica **antes** de la primera invocación real: decir
"según la base de conocimiento" después de haberla consultado es una cita
legítima, no una atribución falsa.

Es una solución con limitaciones declaradas —falsos negativos por
formulaciones no contempladas, falsos positivos que gastan un reintento— y no
es una garantía programática como `validar_fuentes()` del Sprint 1. Se
documenta así deliberadamente en vez de presentarla como equivalente.

---

## 6. Evaluación (#15) y su lugar en la arquitectura

El marco de evaluación es parte del sistema, no un accesorio:

| Componente | Rol |
|---|---|
| `data/evaluation/agent_golden_set.json` | 10 casos, seis tipos de comportamiento |
| `scripts/evaluation/seed_agent_test_user.py` | estado conocido y reproducible |
| `scripts/evaluation/evaluate_agent.py` | corrida, métricas, resultados por caso |

Cinco rondas contra servicios reales produjeron seis hallazgos, **ninguno
detectable con las pruebas unitarias con mocks**, que se mantuvieron en verde
durante todo el proceso. Por diseño, un mock nunca falla como falla un servicio
real.

El detalle completo —resultados, análisis cualitativo, limitaciones del propio
marco de medición— está en `docs/evaluation/agent-evaluation.md`.

Una consecuencia arquitectónica que vale registrar: **el marco de evaluación
también es código, y también tuvo defectos.** Cuatro de los seis hallazgos
(A, B, y las limitaciones 5.1 y 5.2 del documento de evaluación) no estaban en
el agente sino en el instrumento que lo medía. Confundirlos habría llevado a
"corregir" un agente que funcionaba bien.

---

## 7. Integración continua

`.github/workflows/tests.yml` ejecuta la suite completa ante cada PR hacia
`main` y ante cada push a `develop`.

**No se configura ningún secret de GCP, y eso no es casualidad.** Las pruebas
usan mocks y no tocan Vertex AI, Firestore ni ChromaDB — lo cual solo es
posible gracias a dos decisiones tomadas mucho antes, por otras razones:

- el cliente perezoso de Firestore (sección 1.3), que evita la conexión al
  importar;
- `vertexai.init()`, que registra configuración sin autenticar.

Si en el futuro este workflow empieza a requerir credenciales, es señal de que
alguna prueba dejó de estar aislada.

Se fija Python 3.11, la versión del entorno de desarrollo del equipo, en lugar
de una más reciente: un CI que prueba una versión distinta a la que se corre
localmente es una fuente de discrepancias gratuita.

---

## 8. Deuda técnica identificada

| Deuda | Origen | Riesgo |
|---|---|---|
| SDK `vertexai.generative_models` deprecado | decisión 2.2 | retiro anunciado para junio de 2026 |
| Lógica de comportamiento en un archivo de texto | decisión 2.3 | verificación empírica, no determinista |
| Heurística textual del hallazgo C | decisión 5.2 | falsos positivos y negativos |
| Memoria sin expiración temporal | decisión 3.3 | continuidad falsa tras meses |
| Knowledge base sin cobertura de calor/humedad | Sprint 1 | relevante para el clima local |
| Métrica de evaluación sin precisión, solo recall | #15 | la sobreinvocación no se penaliza |
| Evaluación de fidelidad con juez LLM | Sprint 1 | sigue pendiente |

---

## 9. Evolución prevista (Sprint 3)

El Sprint 3 introduce sistemas multi-agente. La arquitectura actual ya deja
preparado lo que hace falta:

- **`RepositorioCorredor` es compartido**, no propiedad de un agente. Un tercer
  agente lo consume sin tocar a los dos existentes.
- **El registro de herramientas es una lista de diccionarios.** Agregar una
  herramienta es agregar una entrada y una rama en `despachar()`.
- **La degradación vive en el punto de despacho** (sección 4.4), así que
  cualquier herramienta nueva la hereda sin implementarla.

Lo que sí habrá que decidir de nuevo es la orquestación: coordinar varios
agentes especializados es el caso de uso donde un framework como LangGraph
aporta algo que el SDK directo no resuelve en 200 líneas — a diferencia de este
sprint, donde sí lo resolvía.
