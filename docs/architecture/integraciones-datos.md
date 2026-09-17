# Integraciones de Datos y Servicios

**Issue S3-05 (#21) — Sprint técnico 3: Sistemas Multiagente**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Este documento inventaria las fuentes de datos y servicios que consume el
sistema multiagente, qué agente accede a cada una y por qué, cómo se manejan
las credenciales y qué ocurre cuando algo falla.

---

## 1. Inventario de integraciones

| Integración | Tipo | Qué aporta | Introducida en |
|---|---|---|---|
| **Firestore** | Base de datos gestionada (GCP) | Perfil, sesiones, objetivos, memoria conversacional, recomendaciones, trazas de delegación | Sprint 1 |
| **Vertex AI — Gemini 2.5 Flash** | Servicio de modelo (GCP) | Generación de respuestas y clasificación de intención | Sprint 1 |
| **Vertex AI — text-embedding-004** | Servicio de modelo (GCP) | Embeddings para indexación y recuperación | Sprint 1 |
| **ChromaDB** | Vector store local, persistente | Recuperación sobre la knowledge base curada | Sprint 1 |
| **Open-Meteo** | API externa, sin autenticación | Condiciones climáticas de la ciudad del corredor | Sprint 2 |

**Ninguna integración es nueva en el Sprint 3.** El criterio de aceptación pide
*«reutilizar las integraciones existentes cuando sea posible»* e *«integrar APIs
externas únicamente cuando sean necesarias»*: el sistema multiagente se apoya
íntegramente en lo construido en los Sprints 1 y 2, y lo único que se añade es
una colección de Firestore para las trazas de delegación.

---

## 2. Matriz de acceso por agente

Qué puede consultar cada agente, y qué no:

| | perfil | sesiones | objetivos | memoria | KB entrenamiento | KB nutrición | clima |
|---|---|---|---|---|---|---|---|
| **Orchestrator** | — | — | — | — | — | — | — |
| **Wellness Coach** | sí | sí | sí | sí | sí | **no** | sí |
| **Nutrition** | sí | **no** | **no** | no | **no** | sí | no |

Tres decisiones que esta matriz materializa:

**El orquestador no accede a ningún dato del corredor.** Clasifica y delega. Si
empezara a consultar por su cuenta dejaría de ser un coordinador para
convertirse en un agente más, y la frontera entre ambas responsabilidades se
volvería difusa. Su único contacto con Firestore es el registro de
delegaciones, y lo recibe inyectado.

**El Nutrition Agent consulta el perfil pero no el historial.** Necesita el peso
porque las pautas nutricionales se expresan en gramos por kilogramo; no
necesita las sesiones, que son del dominio del Coach.

**Los dominios documentales son disjuntos.** Las siete categorías de la
taxonomía del Sprint 1 se reparten entre los dos agentes sin solaparse.

### 2.1 Cómo se verifica

La matriz no es una afirmación de este documento: es un invariante con pruebas.
`tests/unit/test_acceso_datos.py` comprueba que el Nutrition Agent no invoca las
consultas de historial, que su recuperación se restringe a su categoría, y que
el módulo del orquestador no importa siquiera el repositorio ni el retriever.

Esa última comprobación es estática a propósito: un acceso a datos empieza
siempre por una importación, así que verificar los nombres que el módulo conoce
detecta el problema en el momento en que alguien agrega el `import`, sin
depender de que exista un caso de prueba que ejercite ese camino.

Dos pruebas más cubren el reparto documental contra el front-matter real de la
knowledge base:

- **Toda categoría tiene dueño.** Si alguien cura un documento con una
  categoría nueva y olvida asignarla, ese documento queda irrecuperable —
  ningún agente lo filtra — y nadie se entera hasta que un corredor pregunte
  por ese tema y reciba una respuesta sin fundamento.
- **Ningún agente declara una categoría inexistente.** Filtrar por una
  categoría que no existe no da error: da cero resultados. Un agente quedaría
  mudo sin que nada lo indicara.

---

## 3. Firestore

### 3.1 Colecciones

| Colección | Documento | Escribe | Lee |
|---|---|---|---|
| `users` | perfil del corredor | auth / seed | Coach, Nutrition, WellnessAgent |
| `sessions` | una por entrenamiento | app / seed | Coach, WellnessAgent |
| `goals` | objetivos activos | app / seed | Coach, WellnessAgent |
| `conversations` | una por corredor, con sus turnos | Coach | Coach |
| `recommendations` | recomendaciones generadas | WellnessAgent | API |
| `delegaciones` | una traza por solicitud | Orchestrator | evaluación, demo |

### 3.2 Acceso centralizado

Todas las consultas relacionadas con el estado del corredor pasan por
`RepositorioCorredor` (`src/data/repositorio_corredor.py`), extraído en el
issue S2-01 precisamente para que dos agentes no terminaran con copias
divergentes de las mismas cuatro consultas.

### 3.3 Dos decisiones heredadas que siguen vigentes

**Sin índices compuestos.** Se evita combinar `where` con `order_by`, o varios
`where` sobre campos distintos: Firestore exige índices compuestos para esos
casos, y crearlos es configuración manual en la consola que no queda versionada
en el repositorio. Se filtra por `userId` y se resuelve el resto en memoria. Con
decenas de documentos por usuario el costo es despreciable y elimina una
dependencia de configuración externa.

**Cliente perezoso.** `src/database/firestore_client.py` retrasa la conexión
hasta el primer uso real. Es lo que permite que las 121 pruebas de la suite
corran sin credenciales — y, en consecuencia, que el pipeline de CI no necesite
ningún secret de GCP.

### 3.4 La colección `delegaciones`

Lo único que el Sprint 3 añade a Firestore. Un documento por solicitud,
identificado por `traza_id`, con todos sus pasos. Un flujo con dos agentes es un
documento con dos pasos, no dos documentos: la unidad de análisis es la
solicitud, no la invocación.

Detalle en `docs/architecture/protocolo-comunicacion-agentes.md`, sección 9.

---

## 4. Vertex AI

Dos modelos, ambos en `us-central1`:

| Modelo | Uso | Consumidores |
|---|---|---|
| `gemini-2.5-flash` | Generación y clasificación | Orchestrator, Coach, Nutrition, WellnessAgent |
| `text-embedding-004` | Embeddings de 768 dimensiones | Indexación y recuperación |

**El clasificador usa `temperature=0`.** Una decisión de enrutamiento no debe
cambiar entre ejecuciones idénticas: el Sprint 2 cerró con una lección sobre
resultados que variaban entre corridas que se creían iguales.

**Cambiar `EMBEDDING_MODEL` invalida el índice.** Los vectores de ChromaDB se
generaron con ese modelo y no son comparables con los de otro. Está advertido
en `.env.example` porque es el tipo de cambio que parece inocuo y degrada la
recuperación en silencio.

> **Deuda registrada.** El SDK `vertexai.generative_models` está deprecado, con
> retiro anunciado para junio de 2026. La migración a `google-genai` sigue
> pendiente desde el Sprint 2.

---

## 5. ChromaDB

Vector store local y persistente en `data/vector_store/`, con espacio coseno
explícito (`hnsw:space: cosine`; el valor por defecto es L2).

El acceso de cada agente se restringe por filtro de categoría, que es donde vive
la frontera de dominio establecida en S3-03:

```python
# Wellness Coach — seis categorías
recuperar(consulta, k=3, categorias=CATEGORIAS_COACH)

# Nutrition Agent — una
recuperar(consulta, k=3, categoria="nutricion")
```

El script de verificación (sección 8) comprueba en cada ejecución que el Coach
no recupera KB-006 y que la consulta de nutrición no devuelve otras categorías.
No es una comprobación de conectividad: es la frontera verificándose a sí misma.

---

## 6. Open-Meteo

Única API externa del sistema. Sin autenticación, sin clave, sin cuota
declarada. Dos llamadas encadenadas: geocodificación de la ciudad y consulta del
clima actual.

Se integró en el Sprint 2 porque el Coach necesita saber si hace calor extremo
antes de recomendar un entrenamiento fuerte — en Maracaibo, donde vive el
usuario de prueba, no es un detalle menor. Es la única API externa que el
sistema consume, consistente con el criterio de integrarlas solo cuando son
necesarias.

**Es también la integración que más nos enseñó.** Un error 500 real durante una
medición del Sprint 2 tumbó la evaluación completa, mientras las 50 pruebas
unitarias con mocks seguían en verde. De ahí salió el hallazgo D y, en cascada,
la generalización del manejo de errores en S2-04.

---

## 7. Manejo de errores

El principio es el mismo en las tres capas y se estableció en la corrección
S2-04: **proteger el punto por donde pasan todas las invocaciones, no cada
llamada individual.** Así, cualquier herramienta o agente que se añada después
hereda la protección sin implementarla.

| Capa | Dónde se protege | Comportamiento ante fallo |
|---|---|---|
| Herramientas | `_despachar_con_degradacion()` | Observación `{"disponible": False, ...}`; el ciclo ReAct continúa |
| Agentes | `OrchestratorAgent._delegar()` | Respuesta degradada; en colaboración, el otro agente responde igual |
| Clasificación | `clasificar()` | Degrada a `no_reconocida`; se pide aclaración, nunca se delega a ciegas |
| Registro de trazas | `RegistroDelegaciones.registrar()` | Se pierde la traza; la conversación continúa |

En los cuatro casos, la excepción real va al log con traza completa
(`logger.exception`) y al usuario le llega un mensaje genérico: exponer detalles
de infraestructura en la superficie conversacional no le sirve al corredor y
filtra información del sistema.

**Lo que no está protegido a nivel de integración**: `RepositorioCorredor` no
captura fallos de Firestore. Es deliberado — se protege un nivel más arriba, en
el despacho de herramientas y de agentes, donde la degradación tiene sentido
para el usuario. Capturar ahí produciría un perfil vacío que el agente
interpretaría como «corredor sin datos», que es peor que un fallo declarado.

---

## 8. Verificación reproducible

```bash
python -m scripts.evaluation.seed_agent_test_user
python -m scripts.verificacion.verificar_integraciones
```

Comprueba las diez integraciones sin invocar a ningún agente, y devuelve código
de salida distinto de cero si alguna falla, para poder encadenarlo en un script
de despliegue.

Existe porque las 121 pruebas de la suite usan mocks y no tocan ningún servicio.
Esa decisión es deliberada —es lo que permite que el CI corra sin credenciales—
pero deja un punto ciego que los dos sprints anteriores demostraron que es real.
El script no sustituye a la suite: la suite verifica la lógica, esto verifica
que el mundo exterior está donde lo dejamos.

Resultado de la última ejecución:

```
[OK] Configuracion por variables de entorno       12 ms  proyecto=runcoach-ai-496921
[OK] Firestore - perfil del corredor            1693 ms  nivel=intermedio ciudad=Maracaibo peso=68
[OK] Firestore - sesiones y objetivos            752 ms  carga 14.0 km (previa 5.0 km), 1 objetivo(s)
[OK] Firestore - memoria conversacional          149 ms  0 turno(s)
[OK] Firestore - registro de delegaciones        495 ms  2 traza(s) accesibles
[OK] Vertex AI - embeddings                     3584 ms  vector de 768 dimensiones
[OK] Vertex AI - generacion                     2249 ms  intencion=entrenamiento confianza=0.95
[OK] ChromaDB - dominio del Coach                417 ms  3 fragmento(s): ['KB-001']
[OK] ChromaDB - dominio de nutricion             326 ms  3 fragmento(s), todos de nutricion
[OK] Open-Meteo - clima                         1598 ms  29.0 C en Maracaibo

Integraciones comprobadas: 10   Correctas: 10   Fallidas: 0
```

---

## 9. Credenciales y configuración

**No hay credenciales en el repositorio.** Verificado sobre los archivos
versionados: `.env` está en `.gitignore`, no existe ningún JSON de cuenta de
servicio, y una búsqueda de patrones de clave (`AIza…`, `-----BEGIN`,
`private_key`, `client_secret`) sobre el árbol versionado no devuelve nada.

| Dónde | Cómo |
|---|---|
| Backend | Variables de entorno centralizadas en `src/utils/config.py`, cargadas desde `.env` |
| Frontend | `import.meta.env.VITE_*`, inyectadas en build |
| Desarrollo local | Application Default Credentials (`gcloud auth application-default login`) |
| CI | Sin secrets: las pruebas usan mocks y no tocan ningún servicio |
| Producción | Identidad de la plataforma (Cloud Run), sin fichero de credenciales |

`src/utils/config.py` centraliza las cuatro variables que el sistema lee.
Existía dispersión en cuatro archivos antes del Sprint 2; centralizarla asegura
que el valor activo sea siempre el del entorno y nunca un literal enterrado en
código de negocio.

Los valores por defecto del código (`runcoach-ai-496921`, `us-central1`) son
identificadores de proyecto y región, no secretos: permiten que el repositorio
funcione recién clonado sin exponer nada.

---

## 10. BigQuery: por qué no aplica

El issue menciona BigQuery en sus actividades y lo condiciona con *«cuando
corresponda»*. **No corresponde en el estado actual del sistema**, y conviene
justificarlo en vez de integrarlo por cumplir.

### 10.1 Qué resuelve BigQuery

Es un almacén analítico columnar, diseñado para agregaciones sobre volúmenes
grandes: escaneos de millones de filas, series temporales largas, consultas
analíticas que en una base operacional serían caras o imposibles.

### 10.2 Qué volumen tiene este sistema

| Entidad | Volumen por corredor |
|---|---|
| Perfil | 1 documento |
| Sesiones | decenas al año |
| Objetivos | unos pocos activos |
| Turnos de conversación | máximo 50 persistidos |

Las consultas que hacen los agentes son *«las N sesiones más recientes»*,
*«la carga de esta semana y la anterior»* y *«los objetivos activos»*. Todas
recuperan decenas de documentos de un solo corredor y se resuelven en Firestore
en cientos de milisegundos, como muestra la verificación de la sección 8.

**Introducir BigQuery hoy añadiría una dependencia, un proceso de sincronización
desde Firestore y una segunda fuente de verdad, a cambio de ninguna consulta que
hoy no se pueda hacer.** Y una segunda fuente de verdad sin necesidad es una
fuente de inconsistencias.

### 10.3 Cuándo sí correspondería

El caso de uso natural es el **Analytics Agent** que contempla el roadmap de la
plataforma, y que no está asignado a este equipo. Ese agente respondería
preguntas que Firestore no resuelve bien:

- Evolución de la carga a lo largo de meses o años, con agregaciones por
  período.
- Comparación de un corredor contra cohortes de nivel o edad similares.
- Detección de patrones sobre el histórico completo de la plataforma.

Ninguna de esas es una consulta del Wellness Coach ni del Nutrition Agent.

### 10.4 Cómo entraría, si entrara

La arquitectura ya deja el camino claro: `RepositorioCorredor` es el único punto
de acceso a los datos del corredor, así que un `RepositorioAnalitico` sobre
BigQuery sería un componente hermano, no una modificación del existente. Los
agentes actuales no se enterarían.

---

## 11. Dependencias externas identificadas

| Dependencia | Criticidad | Si falla |
|---|---|---|
| Vertex AI (Gemini) | **Crítica** | El sistema no puede responder. El clasificador degrada y se pide aclaración |
| Firestore | **Crítica** | Sin perfil ni datos. Las herramientas degradan; el agente responde declarando lo que no pudo consultar |
| ChromaDB | Alta | Sin fundamentación documental. Los agentes declaran el vacío en vez de rellenarlo |
| Open-Meteo | Baja | El Coach responde sin clima, declarándolo. Ya ocurrió en producción (hallazgo D) |

El orden no es teórico: refleja lo que se observó midiendo. La única
integración que ha fallado de verdad hasta ahora es la de criticidad más baja, y
el sistema la absorbió correctamente una vez corregido el hallazgo D.
