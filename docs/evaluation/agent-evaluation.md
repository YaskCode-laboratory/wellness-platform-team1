# Evaluación del Comportamiento del Agente

**Issue #15 — Sprint técnico 2: Agentes Inteligentes Modernos**
Plataforma Inteligente Wellness 2.0 · Equipo 1

---

## 1. Metodología

Se diseñó un conjunto de 10 casos de prueba (`data/evaluation/agent_golden_set.json`)
cubriendo las cinco dimensiones que exige el issue #15:

| Tipo | Casos | Qué verifica |
|---|---|---|
| `sin_herramientas` | AG-01, AG-10 | El agente responde sin invocar herramientas cuando no las necesita (AG-01), y sí las invoca para terminología técnica del dominio aunque parezca una pregunta simple (AG-10) |
| `tool_calling` | AG-02, AG-03, AG-07 | Invocación correcta de una herramienta según la pregunta; AG-07 exige combinar dos en el mismo turno |
| `rag` | AG-04, AG-05 | Fundamentación en la base de conocimiento para preguntas de dominio; AG-05 verifica además que no se emite diagnóstico médico |
| `memoria` | AG-06 | Un segundo turno que solo tiene sentido si el agente recuerda el turno anterior |
| `react` | AG-08 | Encadenar una herramienta de datos con una de conocimiento para responder |
| `limite_alcance` | AG-09 | El agente redirige preguntas fuera del dominio en vez de responderlas |

Cada caso define `herramientas_esperadas`: no como un requisito exacto y
rígido (el modelo puede razonar válidamente de más de una forma), sino como
un criterio objetivo de partida. El script de evaluación
(`scripts/evaluation/evaluate_agent.py`) calcula una **tasa de acierto**
automática (¿se invocaron al menos las herramientas esperadas?) y guarda la
respuesta completa de cada caso para el **análisis cualitativo** posterior,
que es donde se juzgan aspectos que una métrica automática no puede capturar
bien: si la respuesta es realmente útil, si el tono es adecuado, si el
razonamiento en AG-08 fue genuino o casualidad.

Se usa un usuario de prueba fijo (`usuario-eval-agente`), sembrado por
`scripts/evaluation/seed_agent_test_user.py` con un perfil, tres sesiones y
un objetivo activo conocidos, para que los resultados sean reproducibles —
mismo criterio que el `golden_set.json` del Sprint 1.

## 2. Precondiciones para ejecutar

1. Credenciales de GCP configuradas (Vertex AI + Firestore).
2. Correr una vez: `python -m scripts.evaluation.seed_agent_test_user`
3. Correr: `python -m scripts.evaluation.evaluate_agent`

## 3. Resultados

**Pendiente de ejecución real.** Esta sección se completa con la salida de
`scripts/evaluation/evaluate_agent.py` corrido contra Vertex AI real. El
script produce `data/evaluation/agent_resultados.json` con el detalle por
caso y las métricas agregadas (tasa de acierto de herramientas, casos con
límite de iteraciones alcanzado, latencia promedio, desglose por tipo).

## 4. Análisis cualitativo

**Pendiente de ejecución real.** Para cada caso, revisar `respuesta_final`
en `agent_resultados.json` contra el `criterio_aprobacion` correspondiente
en el golden set. Prestar atención particular a:

- **AG-05**: ¿la respuesta evita diagnóstico médico como exige el prompt?
- **AG-06**: ¿el segundo turno realmente usó el contexto del primero, o
  respondió de forma genérica sin conectar con la rodilla mencionada antes?
- **AG-07 y AG-08**: ¿las herramientas se invocaron en el mismo turno de
  razonamiento, o el agente necesitó que el usuario insistiera?
- **AG-09**: ¿la redirección es amable y clara, o el agente intenta
  responder parcialmente la pregunta fuera de dominio?

## 5. Limitaciones encontradas

**Pendiente de ejecución real.** Registrar aquí, sin filtrar, cualquier caso
donde el agente se comportó de forma incorrecta o inesperada — es más
defendible documentar honestamente lo que no funciona bien que presentar
solo resultados favorables (mismo criterio que el Sprint 1 con el caso
EV-16).

## 6. Propuestas de mejora

**Pendiente**, se completa junto con la sección anterior una vez
identificadas las limitaciones reales.