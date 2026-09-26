## 7. Decisión implementada: formato de observaciones, herramientas múltiples, límite de iteraciones y degradación de errores

(Sección anteriormente presentada como pendiente de definición junto con la
implementación de #13/#14. Documenta aquí la decisión final tal como quedó
implementada, no un diseño provisional.)

- **Formato de las observaciones:** cada resultado de herramienta se
  devuelve al modelo mediante `Part.from_function_response(name=...,
  response={"result": resultado})` — el mismo formato para las cuatro
  herramientas, sin distinguir JSON estructurado de texto narrativo: el
  `resultado` es siempre un diccionario Python, tal como lo produce cada
  función de `src/agents/wellness_coach/tools/`.
- **Múltiples herramientas en un mismo turno:** soportado. El ciclo ReAct
  (`WellnessCoachAgent.conversar()`, issue #14) procesa todas las
  `function_calls` que el modelo solicite en una misma respuesta, las
  despacha, y devuelve todas las observaciones antes de continuar el ciclo
  — verificado en pruebas unitarias con más de una herramienta invocada en
  el mismo turno.
- **Orden de invocación:** no se impone un orden fijo entre herramientas;
  el modelo decide cuáles necesita y en qué secuencia las solicita, y el
  orquestador las despacha en ese mismo orden.
- **Límite de iteraciones:** `MAX_ITERACIONES_HERRAMIENTAS = 5` en
  `src/agents/wellness_coach/agent.py`, para evitar ciclos innecesarios,
  tal como exige el criterio de aceptación del issue #14.
- **Manejo de degradación cuando una herramienta falla:** centralizado en
  el punto de despacho (`conversar()`, alrededor de la llamada a
  `despachar(...)`), no en cada herramienta por separado. Si una
  herramienta lanza una excepción no controlada, el orquestador la
  captura y le devuelve al modelo una observación de error uniforme, en
  vez de propagar la excepción y terminar la conversación — corrección
  aplicada tras la revisión de la Dra. Yedra sobre el issue S2-04.