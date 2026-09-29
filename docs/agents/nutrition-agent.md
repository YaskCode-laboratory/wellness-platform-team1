# Nutrition Agent

**Sprint 3 — Sistemas Multiagente** · Plataforma Inteligente Wellness 2.0 · Equipo 1

Agente especializado en alimentación e hidratación del corredor.

Código: `src/agents/nutrition/agent.py` · Prompt:
`prompts/agents/nutrition_agent.txt`

---

## 1. Por qué existe

El agente especializado asignado a este equipo es el **Wellness Coach**,
construido en el Sprint 2. El Nutrition Agent se incorpora en S3-03 como
**segundo participante del sistema multiagente**, no como un segundo entregable
de especialización.

La razón es concreta: los criterios de aceptación de S3-04 y S3-06 exigen *«al
menos un escenario verificable de colaboración entre agentes»*, y con un único
agente especializado la delegación degenera en un enrutador con un solo destino.
Un orquestador que siempre delega en el mismo agente no es un sistema
multiagente.

Se eligió nutrición y no otro dominio porque **KB-006 ya estaba curado desde el
Sprint 1** y el retriever ya filtraba por categoría, lo que cumple de forma
literal el criterio de *«reutilizar capacidades desarrolladas durante los
sprints anteriores»*.

---

## 2. Responsabilidad

| Su dominio | Fuera de su alcance |
|---|---|
| Qué comer antes, durante y después de entrenar | Prescripción de entrenamiento |
| Reposición de carbohidratos y electrolitos | Carga semanal y su progresión |
| Hidratación | Zonas de intensidad |
| Pautas nutricionales para resistencia | Prevención de lesiones |

Si la pregunta incluye entrenamiento, el prompt le instruye a responder la parte
nutricional y derivar la otra, **sin dar recomendaciones de entrenamiento ni de
pasada**.

---

## 3. Entradas y salidas

### Entrada

`responder(user_id, mensaje)`, invocado a través del adaptador del registro con
una `SolicitudAgente`. El `user_id` lo inyecta el orquestador; nunca proviene
del modelo.

### Salida

| Campo | Qué lleva |
|---|---|
| `respuesta` | Texto en lenguaje natural |
| `fuentes` | `doc_id` validados contra lo recuperado |
| `fuentesInventadas` | Citas que el modelo produjo sin haberlas recibido |
| `fragmentosRecuperados` | Qué llegó a su contexto |
| `cubierto` | Si la base de conocimiento alcanzaba para responder |

---

## 4. Por qué es más simple que el Wellness Coach

Una sola llamada al modelo sobre contexto recuperado: **sin ciclo ReAct, sin
tool calling y sin memoria conversacional**.

No es una versión incompleta de algo que debería ser mayor. Una pregunta
nutricional se responde con documentación curada y el peso del corredor, no con
una secuencia de decisiones sobre qué consultar. Añadirle un ciclo de
razonamiento sería pagar latencia y complejidad por una capacidad que no usa.

Los datos lo respaldan: en la evaluación de S3-06 el Nutrition Agent promedió
**6 775 y 8 761 ms** en sus dos casos propios, frente a los 9 000–10 400 ms del
Coach.

---

## 5. Fuentes y frontera documental

La recuperación se restringe a la categoría `nutricion` (KB-006). Las otras seis
categorías de la taxonomía pertenecen al Wellness Coach, y **este agente no
puede recuperarlas**: la frontera se aplica en el filtro, no solo en el prompt.

Evidencia, con la misma consulta bajo los dos filtros:

```
"cuantos carbohidratos debo consumir durante una tirada larga"

dominio del Coach      KB-001  carga_entrenamiento   sim 0.604
                       KB-005  tapering              sim 0.600

dominio de nutrición   KB-006  nutricion             sim 0.725
```

### 5.1 Validación programática de citas

Las fuentes se validan con `validar_fuentes()` del Sprint 1: se separan las
citadas en válidas e inventadas contra los fragmentos realmente recuperados.

El prompt reduce la frecuencia de las citas inventadas pero no las elimina, y en
un sistema cuya ventaja es la trazabilidad, una cita inventada anula el
beneficio. **Una cita inventada se considera degradación**; una laguna
documental, no.

---

## 6. Personalización por peso

Las pautas nutricionales se expresan en gramos por kilogramo, así que el agente
consulta el perfil del corredor para convertirlas en cantidades concretas. Si el
peso no está registrado, da la pauta por kilogramo y **lo declara**, en vez de
suponer un peso.

Es el único dato del corredor al que accede. No consulta sesiones, carga ni
objetivos: verificado en `tests/unit/test_acceso_datos.py`.

---

## 7. Manejo de errores

Este agente **no captura excepciones propias a propósito**. La protección vive
en el punto de despacho del orquestador, que es por donde pasan todas las
invocaciones a agentes: protegerla ahí significa que cualquier agente que se
registre después la hereda sin implementarla. Es la misma decisión que la
corrección S2-04 tomó un nivel más abajo para las herramientas.

Si la recuperación no devuelve fragmentos, declara el vacío **sin llamar al
modelo**: si no hay nada que fundamentar, generar una respuesta solo puede
producir contenido no verificado.

---

## 8. Limitaciones

| Limitación | Consecuencia |
|---|---|
| **Sin memoria conversacional** | Cada pregunta se responde de forma aislada. No recuerda turnos anteriores ni lo que respondió el Coach en el mismo flujo, más allá del contexto que le llegue en la solicitud |
| **Sin acceso al historial de entrenamiento** | Conoce nivel y peso, no sesiones ni carga. Una pauta que dependa del volumen real de entrenamiento queda fuera de su alcance |
| **Una sola fuente documental** | KB-006. La cobertura del dominio es estrecha: responde bien sobre carbohidratos, hidratación y reposición, y declara el vacío en lo demás |

### 8.1 La laguna de KB-006

**El documento no tiene sección de alimentación previa al ejercicio.** Su
estructura cubre requerimiento según carga, durante el ejercicio, recuperación
posterior, hidratación y micronutrientes — pero no el antes.

Detectado en S3-03 y reproducido sistemáticamente en la evaluación (caso MA-11):

> *«…los fragmentos de información que tengo a mi disposición no contienen
> pautas específicas sobre la alimentación previa al entrenamiento matutino. Se
> centran en la nutrición durante el esfuerzo, la recuperación posterior y el
> marco general…»*

`cubierto: false`, `fuentes: []`, `degradado: false`. **El agente se comportó
correctamente**: declaró el vacío en vez de rellenarlo con conocimiento general.

Que la pregunta más frecuente sobre nutrición en running no esté cubierta es una
laguna de la knowledge base, no del agente. Curar ese contenido está en las
propuestas de mejora.

---

## 9. Resultados de evaluación

| Caso | Mensaje | Fuentes | Cubierto | Latencia |
|---|---|---|---|---|
| MA-06 | «¿Cuánta agua debo tomar mientras corro?» | KB-006 | sí | 6 775 ms |
| MA-07 | «¿Cuántos carbohidratos durante una carrera larga?» | KB-006 | sí | 8 761 ms |
| MA-11 | «¿Qué debo desayunar antes de entrenar?» | — | **no** | 4 687 ms |
| MA-08 | Colaboración con el Coach | — | no | paso 1 |
| MA-09 | Colaboración con el Coach | KB-006 | sí | paso 1 |

Cero citas inventadas en toda la corrida.

---

## 10. Documentos relacionados

| Tema | Documento |
|---|---|
| El otro agente especializado | `wellness-agent.md` |
| Cómo se le invoca | `docs/orchestration/delegation-rules.md` |
| Contrato de mensajes | `docs/orchestration/communication-flow.md` |
| Acceso a datos por agente | `docs/architecture/integraciones-datos.md` |
| Resultados completos | `docs/evaluation/multiagent-evaluation.md` |
