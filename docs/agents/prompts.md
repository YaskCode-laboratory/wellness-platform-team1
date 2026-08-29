# Prompts Especializados — Wellness Coach Agent 2.0

**Issue #11 — Sprint técnico 2: Agentes Inteligentes Modernos**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Este documento explica las decisiones de diseño detrás del prompt del Wellness
Coach Agent 2.0. El texto ejecutable del prompt vive en
`prompts/agents/wellness_coach_agent.txt`; este documento explica por qué está
escrito como está.

---

## 1. Naturaleza distinta al prompt RAG del Sprint 1

El prompt RAG existente (`prompts/rag/wellness_rag.txt`) es un prompt de
**generación fundamentada**: recibe todo el contexto ya resuelto de antemano
—chunks recuperados, estado completo del corredor— y produce una respuesta en
un único paso, sin decisiones intermedias que tomar.

El prompt del coach agent es de **orquestación de herramientas**: no recibe el
contexto resuelto por adelantado. En su lugar, describe qué herramientas están
disponibles y bajo qué condiciones debe invocarlas el modelo, turno a turno,
según lo que el corredor pregunte. Las herramientas en sí (nombre, parámetros,
tipos de dato) no se declaran en este texto — eso se define como estructuras
separadas en el código Python que arma la llamada a la API de function calling
de Vertex AI (issue #13). El prompt aporta las reglas de comportamiento: cuándo
usar cada herramienta, cómo combinar sus resultados, y las restricciones de
citación y alcance.

## 2. Qué datos se precargan y por qué

El prompt inyecta `nivel` y `ciudad` del corredor directamente, sin pasar por
una herramienta. Todo lo demás —sesiones, progreso hacia el objetivo, clima
detallado, conocimiento de dominio— se obtiene mediante tool calling, decidido
por el modelo en cada turno.

**Justificación:** `nivel` y `ciudad` son datos casi siempre relevantes para
adaptar el tono y el contenido de cualquier respuesta, independientemente de
qué pregunte el corredor. Exigir una herramienta solo para obtenerlos en cada
turno habría significado una llamada adicional prácticamente garantizada en
toda conversación, sin beneficio real: no hay ningún caso en el que sea más
correcto *no* saber el nivel del corredor antes de responder.

**Alternativa considerada:** no precargar nada, y exponer también `nivel` y
`ciudad` como parte de una herramienta más general de "consultar perfil". Se
descartó porque habría convertido un dato casi siempre necesario en una
decisión del modelo que probablemente terminaría invocándose en cada turno de
todas formas — añadiendo latencia sin aportar la ventaja real de tool calling,
que es evitar herramientas *innecesarias*, no las necesarias casi siempre.

## 3. Reglas de citación extendidas al canal conversacional

El pipeline RAG del Sprint 1 demostró empíricamente (documentado en
`docs/rag/retrieval-pipeline.md` §7) que un modelo puede citar un documento que
nunca recibió, y que el prompt por sí solo reduce mas no elimina ese
comportamiento — la validación programática (`validar_fuentes()` en
`rag_pipeline.py`) es la que garantiza la ausencia de citas inventadas.

El prompt del coach agent traslada ese mismo principio al modo conversacional:
instruye explícitamente a no citar ningún `doc_id` que no provenga de una
invocación real de `consultar_base_conocimiento`. La validación programática
equivalente para el canal conversacional es responsabilidad de la
implementación de la herramienta en el issue #13, no de este prompt — el
prompt reduce la frecuencia del problema, el código la garantiza, exactamente
el mismo reparto de responsabilidades que en el Sprint 1.

## 4. Por qué la base de conocimiento es obligatoria para preguntas de dominio

El prompt instruye explícitamente: *"NO respondas estas preguntas desde tu
conocimiento general"* para cualquier pregunta sobre lesiones, zonas de
intensidad, tapering, nutrición, recuperación o sobreentrenamiento.

Sin esta instrucción, el coach agent respondería preguntas de dominio desde el
conocimiento paramétrico de Gemini —exactamente el comportamiento del modo
`legacy`, sin fuentes ni garantía de exactitud verificable— incluso teniendo
disponible la misma base de conocimiento curada que ya demostró (Recall@3 de
0.944, Sprint 1) ser efectiva para ese propósito. Esta instrucción existe para
que la ventaja central del proyecto —trazabilidad— no se pierda simplemente
porque el canal de acceso cambió de un formulario a una conversación.

## 5. Contexto conversacional en la recuperación

El prompt instruye a formular la consulta de recuperación incorporando
contexto de turnos anteriores cuando la pregunta actual lo requiera ("si la
pregunta depende de contexto mencionado en turnos anteriores... formula la
consulta incorporando ese contexto, no solo el último mensaje").

**Motivación:** a diferencia del modo RAG de un solo turno, donde
`construir_consulta()` tiene todo el estado del corredor disponible de una vez
(`rag_pipeline.py`), en una conversación el tema relevante para una búsqueda
semántica puede haberse establecido varios turnos atrás. Por ejemplo, "¿y si
sigo corriendo igual esta semana?" no es una consulta de búsqueda útil por sí
sola; necesita el contexto de que la conversación viene hablando de una
posible lesión de rodilla. Documentado también en
`docs/agents/wellness-agent.md` §4, como riesgo identificado para el diseño
de memoria (#12) y ReAct (#14).

## 6. Límites de alcance y seguridad

El prompt restringe el dominio de conversación (running y bienestar del
corredor) y prohíbe explícitamente el diagnóstico médico, redirigiendo hacia
un profesional de la salud ante síntomas de lesión. Esta restricción no existe
en los prompts del Sprint 1 porque aquellos generan una recomendación de
entrenamiento estructurada, sin superficie para que el corredor pregunte
libremente algo fuera de ese formato. El canal conversacional, al ser abierto,
sí necesita este límite explícito.

## 7. Pendiente de definición junto con la implementación (#13/#14)

Este documento describe las reglas del prompt; los siguientes aspectos se
resuelven al implementar el mecanismo de tool calling y no están cerrados
todavía:

- El formato exacto en que la observación de cada herramienta se devuelve al
  modelo (JSON estructurado vs. texto narrativo).
- Qué ocurre si dos herramientas son necesarias en el mismo turno (por
  ejemplo, progreso de objetivo y clima, para una pregunta sobre si conviene
  entrenar hoy) — orden de invocación y límite de iteraciones antes de
  responder, tal como exige el criterio de aceptación del issue #14 ("evitar
  ciclos innecesarios").