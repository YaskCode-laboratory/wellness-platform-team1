# Informe de Cierre — Sprint 3: Sistemas Multiagente

**Plataforma Inteligente Wellness 2.0 · Equipo 1**
Maestría en Tecnologías de Información y Comunicación — Universidad del Zulia
Asignatura: Sistemas Inteligentes · Docente: Dra. Yaskelly Yedra

Julio César Matute (frontend/UI) · José Francisco Urdaneta Sánchez (backend/infraestructura/IA)

---

## 0. Dónde encontrar cada cosa

| Qué | Sección |
|---|---|
| Arquitectura final implementada | §2 · §3 · §4 |
| Agentes participantes y su frontera | §2.1 · §2.3 |
| Resultados de S3-06 | §6.3 |
| Limitaciones | §10 |
| Hallazgos | §8 |
| Instrucciones de reproducción y demostración | §7.6 |
| Estado final del Sprint 3 | §12 |

---

## 1. Resumen ejecutivo

El Sprint 3 convirtió un sistema de **un agente** en un sistema **multiagente**.
Hasta el sprint anterior el Wellness Coach era *el* agente: atendía cualquier
pregunta que llegara y su alcance lo definía únicamente su prompt. El trabajo de
este sprint no fue construirle compañía, sino **darle frontera** y montar encima
la capa que decide quién responde qué.

Se adoptó el patrón **Supervisor**: un orquestador recibe cada solicitud,
clasifica la intención, delega en los agentes competentes y devuelve el
resultado con su traza. Se incorporó un segundo agente especializado —el
**Nutrition Agent**— porque con un único destino la delegación degenera en un
enrutador y no existe colaboración que verificar.

Se completaron los siete issues planteados (#17 a #23) y se agregó un octavo,
S3-08, a solicitud de la cátedra: automatizar el despliegue desde el
repositorio.

La evaluación cerró con **100 % de delegación exacta** sobre doce casos y
**12/12 en cumplimiento del criterio de calidad**, con una suite que pasó de
las **63 pruebas** con que cerró el Sprint 2 a **241**, verificadas
automáticamente en cada Pull Request.

En el lado visible, el sprint cierra con **las tres generaciones del sistema
conviviendo en una sola interfaz**: la recomendación de un turno del Sprint 1,
conmutable entre sus dos modos; el chat multiagente con su panel de traza; y una
comparativa que ejecuta las dos arquitecturas de generación sobre el mismo
estado del corredor y muestra el resultado lado a lado. Conservar el modo
`legacy` en vez de descartarlo por obsoleto —una decisión que se sostuvo sprint
tras sprint— es lo que hace posible esa comparativa, y con ella que el argumento
central del proyecto se pueda **ver** en lugar de leerse (§7).

Pero, igual que en el Sprint 2, el valor del sprint no está en esas cifras.
Está en **seis hallazgos** (§8) que comparten una misma familia y que apuntan
todos a la misma idea: *las garantías estructurales sobreviven; lo que depende
de un texto, de una configuración implícita o de una sola medición, no.* Cuatro
de los seis no aparecieron corriendo más pruebas, sino leyendo lo que el sistema
declaraba y contrastándolo con lo que hacía.

El más limpio fue accidental. Durante cuatro issues el prompt del Wellness Coach
corrió truncado al 40 % sin que nadie lo notara, y comparar esa corrida con la
posterior dejó una conclusión que no se puede planificar: **lo que se cae al
quitar el prompt es exactamente el inventario de lo que no está garantizado por
construcción.**

### 1.1 Lo que cambió en el proceso respecto al Sprint 2

El Sprint 2 consolidó sus siete issues en **un solo Pull Request**. Fue una
decisión consciente bajo presión de tiempo, con una mitigación real —cada commit
pasaba la suite completa y cada pieza se verificaba contra servicios reales
antes de construir la siguiente encima—, pero perdía la trazabilidad granular
por issue. La revisión formal de la cátedra lo señaló y fijó la regla para este
sprint: **un issue → una rama → un Pull Request.**

El Sprint 3 la aplicó. Ocho issues, ocho ramas, ocho Pull Requests, encadenados
cada uno sobre su predecesor para que el diff de cada uno muestre solo su propio
cambio:

```
s3-01 → s3-02 → s3-03 → s3-04 → s3-05 → s3-06 → s3-07 → s3-08
 #26     #27     #28     #29     #30     #31     #33     #34
```

El cambio tuvo un efecto que no se anticipó y que conviene registrar: **la
revisión por issue encontró defectos que la revisión por sprint no habría
encontrado.** Dos de los hallazgos de §8 —la traza desalineada y el fallo
propagado como contexto— salieron de observaciones sobre el PR de S3-04. En un
único PR con ocho issues dentro, ese nivel de detalle sobre un archivo concreto
es mucho menos probable que aparezca.

La cadena también obligó a corregir la configuración del CI: el workflow
filtraba por rama destino, de modo que los PR intermedios no mostraban Checks.
El filtro se eliminó, porque si cada issue tiene su PR, cada PR debe enseñar su
suite.

---

## 2. Arquitectura multiagente

### 2.1 Los tres participantes

| Componente | Responsabilidad | Fuera de su alcance |
|---|---|---|
| **Orchestrator Agent** | Clasificar la intención, decidir a quién delegar y en qué orden, repartir la consulta, consolidar y trazar. Emitir las respuestas de control del flujo | Generar contenido especializado de dominio; consultar la base de conocimiento; acceder a datos del corredor |
| **Wellness Coach Agent** | Entrenamiento: carga y progresión, intensidad, prevención de lesiones, tapering, recuperación, progreso hacia objetivos, clima | Nutrición e hidratación |
| **Nutrition Agent** | Alimentación e hidratación del corredor | Prescripción de entrenamiento y análisis de carga |

El orquestador **sí responde al corredor**, pero solo sobre la conversación:
pide aclaración cuando no reconoce la intención, redirige cuando el tema es
ajeno a la plataforma, y declara cuando un agente falla. Son respuestas fijas,
no generadas. Lo que no produce nunca es contenido de dominio. La distinción se
precisó a raíz de una observación de la revisión de S3-01.

El `WellnessAgent` del Sprint 1 permanece **fuera** del flujo multiagente. Su
salida es un JSON estructurado que el frontend renderiza como tarjeta, no una
respuesta conversacional: incorporarlo mezclaría dos contratos de salida sin
beneficio. Conserva su endpoint propio, incluido `/compare`.

### 2.2 Por qué Supervisor

Se evaluaron cuatro patrones:

| Patrón | Ajuste |
|---|---|
| **Sequential** | No. La ruta depende de la intención; una pregunta de entrenamiento no debe atravesar el agente de nutrición |
| **Hierarchical** | No. Con dos agentes no hay subgrupos que anidar; añade una capa sin contenido |
| **Swarm** | No. Sin punto central, reconstruir el recorrido de una solicitud exige correlacionar trazas de cada agente |
| **Supervisor** | **Sí** |

La razón de peso es de trazabilidad: **un solo punto de decisión es un solo
punto de traza.** Cada solicitud entra y sale por el orquestador, así que
responder *«¿qué pasó con esta solicitud?»* no exige cruzar registros. S3-06
exige *«trazabilidad suficiente para comprender el recorrido de una solicitud»*,
y Swarm juega en contra del propio sprint.

La segunda razón es que separa la lógica de coordinación de la de los agentes,
que es criterio de aceptación de S3-02.

### 2.3 La frontera de responsabilidad es estructural

**Es la decisión de diseño central del sprint.** El criterio de S3-03 pide que
cada agente evite asumir responsabilidades de otros. La forma directa es
instruirlo en el prompt, y **no es suficiente**: los hallazgos E y F del Sprint 2
documentaron tres rondas de medición corrigiendo un comportamiento que el prompt
ya prohibía.

Así que la frontera vive en el código. Las siete categorías de la taxonomía del
Sprint 1 se reparten de forma **total y disjunta**: seis para el Coach, una
—`nutricion`, el documento KB-006— para el Nutrition Agent. El filtro se aplica
en el retriever, de modo que el Coach **no puede** recuperar KB-006 aunque su
prompt se lo pidiera.

Dos pruebas verifican el reparto contra el *front-matter* real de la knowledge
base: que toda categoría tenga dueño y que ningún agente declare una categoría
inexistente. Si alguien cura un documento con una categoría nueva y no la
asigna, la suite lo dice.

---

## 3. El Orchestrator Agent (S3-02)

### 3.1 Clasificación de intención

Por LLM y no por reglas sobre palabras clave, por dos razones: las preguntas
reales son ambiguas o mixtas —*«¿qué como antes de una tirada larga y cómo
ajusto la carga?»*— y una decisión por reglas no se puede explicar en la traza.

Tres decisiones hacen que la clasificación sea verificable:

- **`response_schema` con enum**, generado desde el registro de agentes. El
  modelo no puede devolver una intención que no exista, porque el esquema no se
  lo permite. Registrar un agente nuevo lo hace visible al clasificador sin que
  nadie edite el prompt — en el Sprint 2, dos de los seis hallazgos fueron
  desajustes entre lo que el prompt describía y lo que el código hacía.
- **`temperature=0`**, para que la misma pregunta produzca la misma
  clasificación. Con matices: ver el hallazgo H.
- **Degradación sin excepciones.** `clasificar()` nunca lanza; ante una
  respuesta malformada devuelve `no_reconocida` y el orquestador pide
  aclaración.

### 3.2 La política de delegación es lógica pura

`_planificar()` traduce una clasificación en un plan sin tocar red ni modelo.
Toda la política —cuándo delegar, en quién y en qué orden— se lee de un vistazo
y se prueba exhaustivamente sin mockear nada.

El orden de las comprobaciones importa: **la confianza se evalúa primero.** Una
intención clara pero poco confiable no debe delegarse aunque tenga agente
disponible, porque una delegación equivocada entrega al corredor una respuesta
del dominio incorrecto sin avisarle del error.

---

## 4. Comunicación y delegación (S3-04)

### 4.1 El contrato

Hasta S3-03 la comunicación usaba diccionarios sueltos: cada adaptador devolvía
las claves que le parecían. Funciona con dos agentes y se vuelve frágil con más,
porque nada declara qué debe viajar.

`SolicitudAgente` y `RespuestaAgente` fijan ese contrato. No son transporte —los
agentes viven en el mismo proceso— sino la definición de qué acompaña una
delegación y qué vuelve, que es lo que habría que serializar si algún día se
separan en servicios.

**El `user_id` viaja en la solicitud y nunca en el texto.** Lo inyecta el
orquestador desde el contexto de la petición, lo que elimina por construcción
que un mensaje pueda inducir a consultar datos de otro corredor. Es la misma
decisión que el Sprint 2 tomó para `despachar()`.

### 4.2 El reparto de una consulta mixta

Lo hace el clasificador, no el orquestador: ya está leyendo el mensaje y
decidiendo qué dominios intervienen, y partirlo después exigiría una segunda
llamada al modelo sobre el mismo texto.

Sin reparto, el primer especialista contesta su parte **y además deriva la
ajena** al segundo, que responde justo debajo en la misma pantalla. El corredor
lee una derivación innecesaria hacia alguien que ya está respondiendo.

### 4.3 Consolidación sin parafrasear

El orquestador une las respuestas literalmente, atribuyendo cada parte a su
especialista. **No es una decisión de estilo.** Las citas a la knowledge base se
validan programáticamente contra los fragmentos que recuperó cada agente
(`validar_fuentes()`, Sprint 1), y esa validación aplica al texto que el agente
produjo. Si el orquestador lo reescribiera, la correspondencia entre afirmación y
fuente dejaría de estar garantizada.

### 4.4 Prevención de ciclos

Por construcción: **los agentes no delegan.** Solo el orquestador lo hace, sobre
una lista finita determinada antes de invocar al primero. Un agente que reciba
algo fuera de su alcance lo declara en su respuesta, no lo reenvía. Se refuerza
con una guarda explícita que impide invocar dos veces al mismo agente — y esa
guarda destapó el hallazgo J.

---

## 5. Integración con datos y servicios (S3-05)

### 5.1 La matriz de acceso

| | perfil | sesiones | objetivos | memoria | KB entren. | KB nutric. | clima |
|---|---|---|---|---|---|---|---|
| **Orchestrator** | — | — | — | — | — | — | — |
| **Wellness Coach** | sí | sí | sí | sí | sí | **no** | sí |
| **Nutrition** | sí | **no** | **no** | no | **no** | sí | no |

No es una afirmación de la documentación: es un invariante con pruebas. El
acceso del orquestador se comprueba de forma **estática**, sobre los nombres que
el módulo importa — un acceso a datos empieza siempre por una importación, así
que si el módulo no conoce al repositorio ni al retriever, no puede
consultarlos, y la prueba lo detecta en el momento en que alguien agregue el
`import`.

### 5.2 Verificación de integraciones

Las 241 pruebas usan mocks y no tocan ningún servicio.

**El origen de esa decisión es la estructura del equipo, no una preferencia
técnica.** Solo uno de los dos integrantes tiene credenciales de GCP, así que
desde el Sprint 1 todo se verifica primero con mocks del lado del frontend y
después contra servicios reales del lado del backend. Una restricción
organizativa acabó produciendo dos beneficios que no se buscaban: el CI corre
**sin ningún secret de GCP**, y la suite entera se puede ejecutar en cualquier
máquina del equipo sin configurar nada.

Pero deja un punto ciego que los dos sprints anteriores demostraron real: en el
Sprint 2, cincuenta pruebas en verde mientras un error 500 de Open-Meteo
tumbaba la evaluación completa. La suite verifica la lógica; no verifica que el
mundo exterior esté donde lo dejamos.

`scripts/verificacion/verificar_integraciones.py` cubre ese hueco con diez
comprobaciones sobre las cinco dependencias externas, incluidas dos de
**frontera**: falla si el Coach recupera KB-006, y falla si una consulta de
nutrición devuelve otra categoría.

---

## 6. Evaluación y observabilidad (S3-06)

### 6.1 Dos lecciones del Sprint 2, aplicadas desde el primer día

**Coincidencia exacta, no subconjunto.** El marco anterior consideraba acierto
que lo esperado fuera un *subconjunto* de lo invocado. Eso medía recall y no
precisión: invocar de más no penalizaba, y los casos que esperaban cero
herramientas no podían fallar nunca. El defecto sobrevivió cinco corridas. Aquí
la delegación se evalúa por **igualdad de conjuntos**, con sobredelegación y
subdelegación reportadas por separado.

**Memoria limpia antes de cada caso**, y no solo al inicio de la corrida.

### 6.2 La calidad se evalúa explícitamente

**Esta métrica existe por una observación de la revisión del Sprint 2.** Al
cerrar aquel sprint la cátedra pidió precisión sobre el 100 %: era la tasa de
acierto de **invocación de herramientas**, un indicador acotado, y no equivalía
a «calidad general del agente al 100 %». La corrección de entonces fue de
redacción. Este sprint la convierte en una métrica.

Porque el problema seguía ahí, solo que con otro nombre. El golden set
declaraba un `criterio_aprobacion` por caso y **ningún resultado decía si se
cumplía.** La corrida terminaba anunciando «100 % de delegación exacta»
mientras MA-05 incumplía su criterio sin que nada lo dijera.

Ahora cada caso produce un veredicto en dos partes: comprobaciones automáticas
declaradas junto al criterio —que se citen fuentes o que no se cite ninguna, que
aparezca un `doc_id`, que se invoque cierta herramienta— y un veredicto manual
documentado con nota, autor y fecha.

Dos reglas gobiernan la combinación. **Lo automático manda**, porque es la señal
que no depende de quién la mire. Y **sin juicio humano el caso queda pendiente,
nunca aprobado**: una evaluación de calidad a la que le falta juicio debe
declararlo, y los pendientes se reportan como tercera categoría.

### 6.3 Resultados

Corrida del 27 de septiembre, con el prompt restaurado y `TOP_K = 3`.

| Métrica | Valor |
|---|---|
| Casos evaluados | 12 |
| **Delegación exacta** | **100 %** |
| Intención correcta | 100 % |
| Sobredelegación / subdelegación | ninguna |
| Orden de delegación incorrecto | MA-08 |
| **Cumplen su criterio de calidad** | **12/12** |
| Tiempo de respuesta promedio | 9 602 ms |
| — clasificación | 2 579 ms |
| — agentes | 6 820 ms |
| Peor caso (MA-08, colaboración) | 25 448 ms |
| Saludo sin delegación (MA-01) | 2 856 ms |

El 12/12 salió después de corregir **dos expectativas mal escritas del propio
conjunto**, y conviene decirlo: MA-08 esperaba KB-006 en una sub-consulta sobre
qué comer *antes* de entrenar, que es exactamente la laguna documental que MA-11
existe para verificar; y MA-10 exigía citar cuando su criterio solo verifica la
clasificación. Los dos ajustes se aplicaron **sin volver a medir**, con
`--recalcular`, porque corregir un criterio y volver a correr habría mezclado el
efecto del arreglo con el de unas respuestas nuevas.

### 6.4 El costo del patrón Supervisor

El dato más incómodo: **responder «hola» cuesta casi tres segundos**, porque el
clasificador se ejecuta antes de poder decidir que no hay nada que delegar. Es
el precio que S3-01 anunció que se mediría y no se ocultaría.

Conviene no leer estas cifras con más precisión de la que tienen. Entre las dos
corridas el promedio se movió de 9 294 a 9 602 ms y el saludo de 4 050 a
2 856 ms **sobre entradas idénticas**: la variabilidad entre corridas es del
mismo orden que las diferencias que uno querría comparar. Lo que sostienen es el
orden de magnitud y la estructura del reparto, no una comparación fina.

---

## 7. Demostración y despliegue (S3-07, S3-08)

### 7.1 Tres arquitecturas conviviendo en una sola interfaz

Es el resultado más demostrable del proyecto, y no fue gratuito: **exigió no
tirar nada.**

Desde el Sprint 1 el `WellnessAgent` tiene dos modos —`legacy`, con el
conocimiento embebido en el prompt, y `rag`, que recupera de la knowledge base
curada— y en cada sprint hubo la tentación de descartar el primero por
obsoleto. Se conservó deliberadamente, y el Sprint 3 es donde esa decisión
paga: la pantalla de recomendación es hoy un hub de tres pestañas donde
**conviven las tres generaciones del sistema**.

| Pestaña | Qué ejercita | De qué sprint viene |
|---|---|---|
| **Recomendación** | Un turno, sin conversación. Conmutable entre `legacy` y `rag`, con el resultado de cada modo conservado por separado | Sprint 1 |
| **Chat** | Conversación con el sistema multiagente, con memoria persistida y panel de traza | Sprints 2 y 3 |
| **Comparativa** | Las dos arquitecturas de un turno, ejecutadas sobre el mismo estado y mostradas lado a lado | Sprint 1, demostrable por fin |

### 7.2 Por qué la comparativa es una comparación y no una ilustración

`/agent/{userId}/compare` ejecuta los dos modos **sobre el mismo estado del
corredor, en la misma petición, con el mismo modelo**. Gemini 2.5 Flash en los
dos casos: lo único que cambia es de dónde sale el conocimiento.

Esa es la parte que la hace válida. No se comparan dos modelos —eso no
permitiría atribuir la diferencia a nada— sino **dos arquitecturas de
generación con todo lo demás controlado**: mismo corredor, mismos kilómetros,
misma semana, mismo instante, mismo modelo. La arquitectura queda como única
variable.

La diferencia que la interfaz hace visible no es de estilo ni de calidad
percibida, que serían discutibles. Es de **trazabilidad**:

- El modo `legacy` responde desde conocimiento embebido en el prompt y no puede
  citar nada. La interfaz lo declara literalmente: *«ninguna — no puede citar»*.
- El modo `rag` muestra qué fragmentos recuperó, de qué documentos, y con qué
  consulta los buscó.

Un corredor viendo las dos cajas —la roja sin fuentes, la azul con KB-001 y la
consulta de recuperación a la vista— entiende en cinco segundos el argumento
que el proyecto lleva tres sprints construyendo. Es un argumento que en un
documento ocupa dos páginas y que en la pantalla se ve.

### 7.3 El panel de traza

Hace con el sistema multiagente lo que la comparativa hace con el RAG: vuelve
observable lo que de otro modo habría que creer.

Por cada respuesta muestra qué intención se detectó y con qué confianza, a qué
agentes se delegó y en qué orden, **qué mensaje recibió cada uno** —que en una
consulta mixta no es el mensaje completo sino su parte—, qué fuentes citó y
cuánto costó cada paso. No hace falta acceso al servidor para auditar una
respuesta.

Hasta este sprint todo eso existía y solo se podía ver con `curl` leyendo un
JSON. El criterio de S3-07 pide una demostración reproducible por un tercero, y
un `curl` no lo es para quien evalúa el sistema sin haberlo construido.

### 7.4 Lo que hizo falta para que la demostración fuera reproducible

Se migraron sesiones, objetivos y métricas al repositorio. Vivían en
microservicios desplegados aparte, de modo que el chat se podía reproducir pero
**los datos sobre los que razona, no**: un tercero podía levantar el orquestador
y encontrarse un corredor sin sesiones, sin objetivos y sin historial — es
decir, un agente sin nada sobre lo que razonar.

### 7.5 Despliegue continuo

S3-08 automatiza la publicación: backend en Cloud Run, frontend en Firebase
Hosting, **en ese orden**. Automatizar solo el frontend habría publicado la
interfaz nueva contra el backend viejo. El pipeline no publica si la suite
falla, si el lint falla, si falta configuración, o si `/health` no responde 200 —
porque que `gcloud run deploy` termine sin error no significa que el servicio
funcione.

### 7.6 Cómo reproducir el sistema y la demostración

El criterio de S3-07 pide una demostración **reproducible por un tercero**. Lo
que sigue es el recorrido completo, desde un clon limpio.

#### Requisitos

Python 3.11, Node 22, y credenciales de Google Cloud con acceso a Vertex AI y
Firestore en el proyecto `runcoach-ai-496921`. El índice de ChromaDB **viaja
versionado en el repositorio**, así que no hay que construirlo.

#### 1 · Backend

```bash
git clone https://github.com/YaskCode-laboratory/wellness-platform-team1.git
cd wellness-platform-team1

python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

El `.env` funciona sin editar: las cuatro variables tienen valores por defecto
correctos para este proyecto. `GOOGLE_APPLICATION_CREDENTIALS` debe quedar
**comentada** si se usan Application Default Credentials:

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project runcoach-ai-496921
```

Y se levanta desde la raíz del repositorio, con `python -m` para que los
imports absolutos `from src...` resuelvan:

```bash
python -m uvicorn src.app.main:app --reload --port 8080
```

Comprobación: `curl localhost:8080/health` debe devolver `200`.

#### 2 · Datos del corredor

Sin datos, los agentes no tienen sobre qué razonar. Hay dos caminos.

**Usuario sintético**, reproducible y anclado al lunes de la semana en curso
para que la carga semanal sea la misma corra el día que corra:

```bash
python -m scripts.evaluation.seed_agent_test_user
```

**Cuenta real**, que es lo que conviene para una demostración en vivo:

```bash
python -m scripts.evaluation.seed_agent_test_user --email tu@correo.com
```

Resuelve el `uid` de Firebase de esa cuenta y siembra sus sesiones, su objetivo
y su perfil, completando solo los campos que falten. Requiere que la cuenta ya
exista: si no, hay que registrarse antes desde la interfaz.

> **La ciudad importa.** Sin ella, la herramienta de clima del Coach no tiene
> dónde consultar y declara que no puede — correcto, pero deja una de las
> cuatro herramientas sin demostrar. Se pone desde *Perfil* en la interfaz.

#### 3 · Frontend

```bash
cd frontend
npm install
cp .env.example .env
```

Este `.env` **sí hay que editarlo**: las variables de Firebase son propias del
proyecto y no tienen valor por defecto. Las cuatro URL del backend ya apuntan a
`http://localhost:8000` — cámbialas a `8080` si levantaste el backend en ese
puerto, o arráncalo en 8000.

```bash
npm run dev
```

> Vite lee el `.env` **solo al arrancar**. Si lo editas con el servidor
> corriendo, hay que reiniciarlo: no basta con recargar el navegador. Es una
> hora perdida que ya pagamos.

#### 4 · El recorrido de la demostración

Entra con la cuenta sembrada y ve a **Recomendación**, que es el hub de tres
pestañas. Cinco momentos, en este orden:

**Modo RAG, pestaña Recomendación.** Genera una recomendación y observa que
cita sus fuentes. Es el punto de partida del Sprint 1.

**Modo legacy, misma pestaña.** El mismo estado del corredor, la otra
arquitectura. Responde bien y no cita nada, porque no tiene de dónde.

**Pestaña Comparativa.** Ejecuta las dos sobre el mismo estado, en la misma
petición. La caja roja declara *«ninguna — no puede citar»*; la azul muestra
los fragmentos recuperados y la consulta con que los buscó. **Es el argumento
central del proyecto en una sola pantalla.**

**Pestaña Chat, consulta de un solo dominio.** Por ejemplo *«¿qué significa
zona 2?»*. Abre el panel de traza: intención `entrenamiento`, confianza, un
solo agente, la herramienta que invocó y la fuente que citó.

**Pestaña Chat, consulta mixta.** Por ejemplo *«¿qué como antes de una tirada
larga y cómo ajusto el entrenamiento esta semana?»*. Aquí se ve el sistema
multiagente completo: intención `mixta`, **dos agentes**, y en la traza el
mensaje que recibió cada uno — que no es la pregunta entera sino su parte. Es
lo que distingue delegar de reenviar.

Tarda unos 25 segundos. La delegación es secuencial porque el segundo agente
recibe el contexto del primero; está declarado como limitación en §10.

#### 5 · Verificar que todo está donde debe

```bash
python -m unittest discover -s tests -p "test_*.py"

python -m scripts.verificacion.verificar_integraciones

python -u -m scripts.evaluation.evaluate_multiagent
```

La primera son las 241 pruebas con mocks, sin credenciales. La segunda son diez
comprobaciones contra los servicios reales, incluidas dos de frontera. La
tercera corre el golden set completo y tarda unos tres minutos.

---

## 8. Hallazgos

Seis, y comparten familia. Cuatro no aparecieron corriendo más pruebas, sino
leyendo lo que el sistema declaraba y contrastándolo con lo que hacía.

### 8.1 Hallazgo G — Lo que se cae al quitar el prompt es el inventario de lo no garantizado

**El más valioso del sprint, y fue accidental.**

Al aplicar la delimitación de dominio de S3-03, el prompt del Wellness Coach
quedó recortado de 105 a 42 líneas. Se perdieron la descripción de las cuatro
herramientas, el manejo de información no cubierta, los límites de alcance, las
restricciones médicas y **las reglas de citación**. Los issues S3-03 a S3-06 se
ejecutaron con esa versión, y nadie lo notó.

Cuando se descubrió y se restauró, comparar las dos corridas del mismo golden
set —idénticas salvo por el prompt— dio esto:

| Caso | Consultó la KB | Citó, prompt truncado | Citó, prompt completo |
|---|---|---|---|
| MA-05 | sí | ninguna | **KB-002** |
| MA-08 | sí | ninguna | **KB-001** |
| MA-09 | sí | ninguna | **KB-005, KB-007** |
| MA-10 | sí | ninguna | ninguna |

Con el 60 % del prompt ausente, el agente **siguió** invocando las herramientas
correctas, respetando la frontera de nutrición y sin recuperar KB-006. Eso lo
sostuvieron el filtro de categorías, las descripciones de `FunctionDeclaration`
y el registro de herramientas: estructura, no texto.

Lo único que se cayó fue la citación. Y se cayó porque **en ese agente la
citación es lo único sin respaldo estructural**: en el Nutrition Agent
`validar_fuentes()` compara lo citado contra lo recuperado sobre un campo
declarado; en el Coach depende de una instrucción en prosa.

> **Formulado como regla: lo que se rompe al quitar el prompt es exactamente el
> inventario de lo que no está garantizado por construcción.** Es un diagnóstico
> que no se obtiene leyendo el código, porque ahí las dos cosas se ven igual de
> escritas.

**Un segundo caso de la misma clase** apareció al cubrir la matriz de acceso: la
descripción de la `FunctionDeclaration` de `consultar_base_conocimiento` seguía
anunciando que cubría nutrición, heredada del Sprint 2, tres issues después de
que el filtro la excluyera. El modelo la invocaba, no recibía nada, y quedaba
ante un vacío aparente de la base en vez de derivar al otro agente. El filtro
impide *recuperar* lo ajeno; no impide que el modelo crea que debería
encontrarlo. Hacen falta las dos, y que coincidan.

### 8.2 Hallazgo H — Una sola corrida no distingue una propiedad de un accidente

El Sprint 2 sospechó que el clasificador no calibraba confianza sino que emitía
un valor por defecto. La corrida del 22 pareció refutarlo: tres valores
distintos, con el saludo en 0.90 y el tema ajeno en 1.00, lo cual resultaba
coherente.

La corrida del 27, sobre las mismas entradas y con `temperature=0`, dio **un
solo valor: 0.95.**

No es que el modelo calibre mejor o peor: **el valor no es reproducible**, y eso
descarta la tercera posibilidad que la primera corrida dejaba abierta —que
midiera algo real con poca resolución—. Una señal que cambia de 0.90 a 0.95 para
el mismo mensaje no está midiendo una propiedad del mensaje.

La consecuencia práctica: el umbral que decide si delegar está en 0.50, los
valores no bajan de 0.90, y ahora se sabe que el poco recorrido que parecían
tener era ruido. Como salvaguarda **no podría activarse de forma reproducible
aunque se recalibrara**, lo que inclina la decisión hacia retirarlo como puerta
y conservar la confianza solo como señal de traza.

El mismo efecto se observó en el **orden de delegación** de MA-08, que se
invirtió entre corridas sobre el mismo mensaje pese a determinar qué respuesta
sirve de contexto a cuál.

### 8.3 Hallazgo I — La plataforma razonaba sobre el calendario en UTC

El sistema calculaba «hoy» y «esta semana» en UTC mientras sus corredores viven
en UTC−4. Cada día, a partir de las ocho de la noche hora local, el backend
creía que ya era el día siguiente. Y el domingo a esa hora empezaba una semana
nueva: **el kilometraje semanal se reiniciaba cuatro horas antes de tiempo**,
justo en la franja en que alguien sale a correr y entra a registrar la sesión.

No es cosmético. «Esta semana» decide qué sesiones cuentan para la carga, qué
carga se compara con la meta y qué datos recibe el agente para razonar sobre
progresión. Una semana mal delimitada produce una recomendación mal fundada.

La corrección distingue dos cosas que no son la misma: **el calendario** va en la
zona del corredor —qué día es hoy, en qué semana estamos, cuántos días hace de
una sesión, preguntas sobre su vida que se responden donde vive— y los
**instantes** que se persisten van en UTC, porque marcan cuándo ocurrió algo y
se comparan entre sí.

Tener la definición de «hoy» duplicada en dos módulos fue lo que permitió que
ambos derivaran hacia UTC sin que nadie lo notara.

### 8.4 Hallazgo J — Comprobaciones cuyo resultado depende de cuándo se ejecutan

El hallazgo I estuvo tapado por sus propias pruebas, y esa es la parte
interesante.

Las pruebas comparaban contra `date.today()` —hora local— contra un código que
usaba `utcnow()`. **Pasaban dieciséis horas al día y fallaban ocho**, y en CI
pasaban siempre porque el runner está en UTC. Aparecieron en rojo por primera
vez al correr la suite de noche.

Un segundo caso, independiente, apareció el mismo día:
`test_calcular_carga_semanal` colocaba una sesión en «lunes + 2 días». Los lunes
esa fecha cae en el **futuro**, y la función suma correctamente solo hasta hoy.
Fallaba **un día de cada siete**, y pasó desapercibido en local y en seis
corridas de CI porque ninguna cayó en lunes. La séptima sí.

> Una comprobación cuyo resultado depende de la hora, del día de la semana o de
> la zona de la máquina no verifica lo que dice verificar. Es la misma familia
> que el criterio de subconjunto del Sprint 2: una prueba que no puede fallar, o
> que falla por motivos ajenos a lo que mide, da una confianza que no se ha
> ganado.

La suite pasa ahora en UTC, Caracas, Tokio y Auckland.

### 8.5 Hallazgo K — La traza mentía justo cuando actuaba una protección

Señalado en la revisión de S3-04. `_componer()` reconstruía el mensaje entregado
a cada agente indexando el **plan** por la posición de la **respuesta**. Cuando
la guarda contra repetición omite una delegación, ambas listas dejan de tener la
misma longitud, el índice se desplaza, y la traza atribuye a un agente un
mensaje que nunca recibió.

**Una traza equivocada es peor que una ausente: se lee como evidencia.** Y el
defecto era doblemente grave porque solo se manifestaba **cuando actuaba una
protección**, que es justo el momento en que hace falta poder auditar.

Se corrige devolviendo las delegaciones efectivamente ejecutadas junto a las
respuestas, emparejadas por construcción.

### 8.6 Hallazgo L — Degradar bien hacia el usuario y mal hacia el siguiente agente

También de la revisión de S3-04, y es el reverso del hallazgo D del Sprint 2.

Cuando un agente falla, el orquestador devuelve un texto genérico dirigido al
corredor. Ese texto se encadenaba como contexto al siguiente agente, produciendo
*«Nutrition Agent respondió: No pude completar tu consulta…»*, y el contrato le
pide al segundo que **complemente y no contradiga** lo que dijo el anterior.

El segundo agente trataba un mensaje de error como aportación de un colega.
Además invertía el sentido de la degradación, que S3-01 definió como *conservar
lo que sí funcionó*: así el fallo de uno contaminaba al otro.

La corrección exigió una distinción que no existía: `degradado` no basta, porque
un Coach que respondió bien pero no pudo consultar el clima viene degradado y su
texto **sí** es contexto útil. Se agrega `fallo`, más estrecho, que marca
únicamente «no produjo contenido de dominio».

### 8.7 Un hallazgo fuera de la evaluación

Al preparar el despliegue apareció algo que ninguna medición de calidad habría
encontrado: **el backend no verificaba ningún token.** El frontend enviaba
`Authorization: Bearer <idToken>` en cada llamada desde el Sprint 1 y el backend
lo ignoraba.

Con la API pública y todos los endpoints tomando el identificador del corredor
de la ruta o del cuerpo, cualquiera que conociera un `uid` podía leer y escribir
el perfil, las sesiones, los objetivos y el historial de chat de ese corredor.
Las reglas de seguridad de Firestore no cubrían nada, porque el backend usa el
Admin SDK, que las salta por diseño.

Se corrigió antes de publicar. La lección de proceso es que **automatizar el
despliegue obligó a mirar el sistema como algo que se expone**, y esa mirada
encontró en una tarde algo que tres sprints de evaluación funcional no habían
mirado nunca.

---

## 9. Tecnologías utilizadas

| Capa | Tecnología |
|---|---|
| Orquestación | SDK directo de Vertex AI, sin framework de agentes |
| Clasificación | Gemini 2.5 Flash con `response_schema` y `temperature=0` |
| Recuperación | ChromaDB, `text-embedding-004`, similitud coseno, k=3 |
| Persistencia | Firestore (perfiles, sesiones, objetivos, memoria, delegaciones) |
| API | FastAPI, handlers síncronos |
| Frontend | React 19, Vite, Tailwind |
| CI/CD | GitHub Actions, Cloud Run, Firebase Hosting |

**Se reevaluó LangGraph** y se mantuvo la decisión del Sprint 2. Con el alcance
real —dos agentes y un patrón Supervisor sin estado compartido entre pasos— el
grafo que construiría tiene tres nodos y dos aristas: se implementa en menos
código del que costaría la integración, y el conflicto de dependencias con
`firebase-admin` sigue vigente. La decisión se revisaría con un roster mayor o
con necesidad de estado persistente entre pasos.

---

## 10. Limitaciones conocidas

| Limitación | Consecuencia |
|---|---|
| El Coach no expone sus fuentes de forma estructurada | Una evaluación de fidelidad automatizada solo cubriría a uno de los dos agentes |
| No se mide fidelidad del contenido a las fuentes | Se sabe qué se recuperó y qué se citó, no si lo afirmado se sostiene en ello |
| Un solo caso por tipo en tres categorías del golden set | Un acierto puede ser suerte |
| El conjunto no contiene casos adversos | No se ha probado qué hace el sistema ante un mensaje que intente inducirlo a salirse de su dominio |
| KB-006 no cubre la alimentación previa al ejercicio | La pregunta más frecuente sobre nutrición en running no está cubierta, y se alcanza también por el camino natural de una consulta mixta |
| La delegación es secuencial | Dos agentes suman latencias: 25 s en el peor caso medido |
| Citación parcial | El Coach a veces atribuye a «la base de conocimiento» sin nombrar el documento, y entonces la afirmación no es verificable |
| Clave JSON de larga vida en el CI | Si se filtra, sirve hasta que alguien la revoque. Lo correcto es Workload Identity Federation |

---

## 11. Propuestas de mejora

**Cerrar la laguna de KB-006.** Es la carencia más visible de la knowledge base
y ya no es hipotética: se alcanza sin preguntarle directamente.

**Exponer las fuentes del Coach en su contrato de salida.** Cierra la asimetría
de trazabilidad y habilita la evaluación de fidelidad para los dos agentes.

**Medir fidelidad con juez LLM.** Es la limitación que más pesa: sin ella, la
decisión de `k` se tomó con una métrica de recuperación que no mide la calidad
de la respuesta generada.

**Decidir qué hacer con el umbral de confianza.** Retirarlo como puerta y
conservarlo como señal, o recalibrarlo — pero eso exige primero que el valor sea
reproducible, y hoy no lo es.

**Fijar el orden de delegación en el registro de agentes** en vez de dejarlo al
clasificador, o aceptar que es indiferente y paralelizar, que además resolvería
el peor caso de latencia.

**Migrar el CI a Workload Identity Federation.**

**Revisar si el SDK ya admite `tool_config` por mensaje.** Queda pendiente del
Sprint 2 y no se retomó aquí. El hallazgo C se corrigió con una heurística
textual más un reintento acotado, porque `ChatSession.send_message()` no
aceptaba `tool_config` por mensaje y aplicarlo a nivel de modelo forzaría una
llamada a herramienta en cada turno, incluidos los que legítimamente no la
requieren. Si el SDK lo permitiera hoy, esa heurística —que es una regla sobre
el texto, justo la clase de garantía que este sprint aprendió a desconfiar—
podría reemplazarse por una estructural.

---

## 12. Estado final y conclusión

### 12.1 Estado de entrega

| Issue | Entregable | Estado |
|---|---|---|
| **S3-01** · #17 | Arquitectura multiagente y patrón Supervisor | Completo |
| **S3-02** · #18 | Orchestrator Agent con clasificación y delegación | Completo |
| **S3-03** · #19 | Agente especializado con frontera estructural | Completo |
| **S3-04** · #20 | Comunicación y delegación entre agentes | Completo |
| **S3-05** · #21 | Integración con datos y servicios | Completo |
| **S3-06** · #22 | Evaluación del flujo y observabilidad | Completo |
| **S3-07** · #23 | Documentación y demostración reproducible | Completo |
| **S3-08** | Despliegue automatizado | Completo |

| | |
|---|---|
| Metodología | Un issue → una rama → un Pull Request, encadenados |
| Suite de pruebas | 241, en verde y verificadas en cada PR |
| Delegación exacta | 100 % (12/12) |
| Criterio de calidad | 12/12 |
| Tiempo de respuesta promedio | 9 602 ms |
| Agentes en producción | Orchestrator + Wellness Coach + Nutrition |
| Frontend | Firebase Hosting, publicación automática |
| Backend | Cloud Run, publicación automática |

Todas las observaciones de la revisión formal quedaron atendidas, y **dos de
ellas produjeron hallazgos** que no habrían aparecido de otro modo (§8.5, §8.6).

### 12.2 Conclusión

El sprint cumplió los ocho issues y cerró con delegación exacta al 100 % y
calidad 12/12, pero esas cifras son lo menos interesante que produjo.

Lo que deja es una idea que atraviesa los seis hallazgos. El Sprint 2 la enunció
al descubrir que un prompt describe el comportamiento deseado pero no lo
garantiza. El Sprint 3 la puso a prueba sin querer: **durante cuatro issues el
agente corrió con el 60 % de su prompt ausente y su comportamiento se sostuvo,
salvo en lo único que no tenía respaldo estructural.** Esa es la formulación más
precisa que el equipo ha alcanzado de por qué las garantías se ponen en el
código y no en el texto.

Los otros cinco son variaciones del mismo tema. Una confianza que cambia entre
corridas idénticas no es una propiedad medida sino una cifra observada una vez.
Un calendario que depende de dónde corre el servidor no es una decisión de
diseño sino una omisión. Una prueba que pasa dieciséis horas al día da una
confianza que no se ha ganado. Una traza que se desalinea justo cuando actúa
una protección convierte la evidencia en ruido. Y un mensaje de error encadenado
como si fuera la respuesta de un especialista propaga hacia adentro el fallo que
se había contenido bien hacia afuera.

Cuatro de los seis no se encontraron corriendo más pruebas. Se encontraron
**leyendo lo que el sistema declaraba y comparándolo con lo que hacía** — dos de
ellos a partir de observaciones de la revisión externa, que llegó a lo que la
medición propia no. Es la misma conclusión del Sprint 2, ahora con más
evidencia: el marco de evaluación encuentra lo que se le pide buscar, y lo que
no se le pide hay que ir a mirarlo.

El séptimo hallazgo, el de la autenticación, está fuera de esa lista porque no
salió de la evaluación sino de preparar el despliegue, y por eso mismo es el que
más dice sobre el proceso: **una API que recibe un token y no lo mira publica
los datos de sus usuarios sin que ninguna métrica de calidad se entere.** Tres
sprints de medición funcional no lo miraron nunca; automatizar la publicación
obligó a ver el sistema como algo que se expone, y apareció en una tarde.
