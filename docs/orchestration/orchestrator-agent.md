# Orchestrator Agent

**Sprint 3 — Sistemas Multiagente** · Plataforma Inteligente Wellness 2.0 · Equipo 1

El componente que coordina el sistema multiagente: recibe la solicitud del
corredor, determina qué dominios de conocimiento hacen falta, delega en los
agentes competentes y devuelve el resultado con su traza.

Código: `src/orchestration/orchestrator/`

---

## 1. Responsabilidades

| Hace | No hace |
|---|---|
| Recibir la solicitud del corredor | Responder preguntas de dominio por su cuenta |
| Clasificar la intención | Consultar la base de conocimiento |
| Decidir a qué agentes delegar y en qué orden | Acceder a Firestore para datos del corredor |
| Repartir la consulta cuando intervienen varios | Invocar herramientas |
| Consolidar las respuestas y atribuirlas | Reescribir o parafrasear lo que dicen los agentes |
| Producir y registrar la traza | — |

Cuando **no** delega —intención ajena al dominio, ambigua, o de un dominio sin
agente asignado— responde con un **texto fijo, no generado**.

Esa restricción es deliberada y es criterio de aceptación de S3-02: la lógica de
coordinación queda separada de la de los agentes. Si el orquestador empezara a
resolver casos por su cuenta dejaría de ser un coordinador para convertirse en
un agente más, y la frontera entre ambas responsabilidades se volvería difusa.

La restricción está verificada, no solo declarada: `tests/unit/test_acceso_datos.py`
comprueba que el módulo del orquestador no conoce siquiera los nombres
`RepositorioCorredor`, `recuperar`, `consultar_base_conocimiento` ni `db`.

---

## 2. Componentes

| Archivo | Responsabilidad |
|---|---|
| `agent.py` | Orquestación: planificación, ejecución, consolidación, traza |
| `clasificador.py` | Determinación de la intención y reparto de consultas mixtas |
| `registro_agentes.py` | Lista declarativa de agentes y adaptadores de contrato |
| `prompts/orchestration/clasificador_intencion.txt` | Prompt del clasificador |

### 2.1 El registro como fuente de verdad

`_AGENTES` es una lista de diccionarios Python simples, el mismo patrón que
`_HERRAMIENTAS` del Sprint 2 y por la misma razón: es lo que se inspecciona en
las pruebas y lo que se recorre al resolver una delegación.

**El catálogo que ve el clasificador se genera desde esa lista**, no se escribe
a mano en el prompt. Registrar un agente lo hace visible al clasificador
automáticamente. En el Sprint 2, dos de los seis hallazgos fueron desajustes
entre lo que el prompt describía y lo que el código hacía; aquí no pueden
desincronizarse.

### 2.2 Instancias perezosas

Los agentes se construyen la primera vez que se necesitan y se memorizan.
Construir un agente abre conexiones reales a Firestore y Vertex AI, y el
registro se importa desde las pruebas del orquestador, que no deben tocar la
red. Es la misma lección que el cliente perezoso de Firestore del issue S2-01.

---

## 3. Clasificación de intención

### 3.1 LLM con salida estructurada, no reglas

Las reglas por palabras clave fallan en los dos casos que más importan:

- **Preguntas mixtas.** *«¿Qué como antes de una tirada larga y cómo ajusto el
  entrenamiento?»* contiene términos de ambos dominios; una regla tendría que
  decidir cuál pesa más.
- **Preguntas donde el dominio no aparece en el texto.** *«Me siento sin energía
  en los últimos kilómetros»* no menciona comida, pero su respuesta depende del
  dominio nutricional. Es el caso MA-09 de la evaluación, y el clasificador lo
  resolvió correctamente razonando por dominio de conocimiento.

Además, el modelo devuelve **el motivo** de su elección, que entra en la traza.
Una regla no explica por qué descartó las alternativas.

### 3.2 La forma es una garantía estructural

La respuesta se restringe con `response_schema` del SDK, no con instrucciones en
el prompt, y **los `enum` se construyen desde el registro de agentes**. El
modelo no puede devolver una intención ni nombrar un dominio que el orquestador
no sepa resolver: no porque el prompt se lo pida, sino porque el SDK no se lo
permite.

Es la misma idea que la frontera documental por categoría. El Sprint 2 dejó
clara la diferencia: los hallazgos C, E y F son tres manifestaciones del mismo
problema de confiar un contrato al texto.

### 3.3 `temperature = 0`

Una decisión de enrutamiento no debe cambiar entre ejecuciones idénticas. El
Sprint 2 cerró con una lección sobre resultados que variaban entre corridas que
se creían iguales.

### 3.4 Nunca lanza excepción

Una respuesta malformada, una intención desconocida o un fallo del modelo
degradan a `no_reconocida` con confianza cero, que el orquestador traduce en una
petición de aclaración — nunca en una delegación equivocada.

Que el sistema no sepa a quién delegar es recuperable; que se caiga por intentar
averiguarlo, no.

### 3.5 El umbral de confianza

`UMBRAL_CONFIANZA = 0.5`: por debajo, el orquestador pide aclaración en vez de
delegar. Se evalúa **antes** que la intención, porque una delegación equivocada
entrega al corredor una respuesta del dominio incorrecto sin avisarle del error.

> **Limitación medida.** En los doce casos de S3-06 los valores de confianza
> observados fueron `0.90`, `0.95` y `1.00`, con diez de doce en `0.95`. La señal
> discrimina algo, pero la banda completa está muy por encima del umbral: como
> salvaguarda, nunca se acerca a activarse. Ver
> `docs/evaluation/multiagent-evaluation.md`, sección 4.1.

---

## 4. Manejo de errores

| Situación | Comportamiento |
|---|---|
| Confianza insuficiente | No delega, pide aclaración |
| Intención fuera del dominio de la plataforma | Redirige sin delegar |
| Intención ambigua o incoherente | Pide aclaración |
| Dominio de la plataforma sin agente asignado | Lo declara honestamente |
| Clasificación mixta sin dominios resolubles | Pide aclaración |
| Un agente delegado falla | Respuesta degradada para ese paso; el flujo continúa |
| En colaboración, falla el primero | El segundo se invoca igual; el corredor recibe la mitad que funcionó |
| Falla el registro de la traza | La solicitud se responde igual |

La protección de la invocación de agentes vive **en el punto de despacho**,
misma decisión que la corrección S2-04 tomó un nivel más abajo para las
herramientas: es el único lugar por donde pasan todas, así que cualquier agente
que se registre después hereda la protección sin implementarla.

La excepción real va al log con traza completa (`logger.exception`); al corredor
le llega un mensaje genérico. Exponer detalles de infraestructura en la
superficie conversacional no le sirve y filtra información del sistema.

---

## 5. La traza

Cada solicitud produce una traza que viaja **en la respuesta**, no solo en los
logs, para que la evaluación y la demo puedan reconstruir el recorrido sin
acceso al servidor.

```json
{
  "trazaId": "90ceb767-921c-4473-9fc0-81e656c6de0b",
  "intencion": "mixta",
  "dominios": ["nutricion", "entrenamiento"],
  "motivoClasificacion": "El mensaje requiere conocimiento sobre nutrición y entrenamiento",
  "confianza": 0.95,
  "delegado": true,
  "colaboracion": true,
  "agentes": ["nutrition", "wellness_coach"],
  "motivoNoDelegacion": null,
  "degradado": false,
  "pasos": [
    {
      "paso": 1,
      "agente": "nutrition",
      "mensajeDelegado": "Qué debo comer antes de una tirada larga?",
      "herramientasInvocadas": [],
      "fuentes": ["KB-006"],
      "degradado": false,
      "latenciaMs": 6627
    },
    {
      "paso": 2,
      "agente": "wellness_coach",
      "mensajeDelegado": "Cómo debo ajustar mi entrenamiento esta semana, considerando que tengo una tirada larga?",
      "herramientasInvocadas": ["consultar_base_conocimiento"],
      "fuentes": [],
      "degradado": false,
      "latenciaMs": 13936
    }
  ],
  "latencias": { "clasificacionMs": 5329, "agentesMs": 20563, "totalMs": 25893 }
}
```

`mensajeDelegado` no lo exigía ningún criterio. Se añadió porque ante una
respuesta inesperada la primera pregunta es siempre qué se le pidió al agente, y
sin ese campo la traza no permitiría auditar el reparto de una consulta mixta.

La traza se persiste además en la colección `delegaciones` de Firestore, un
documento por solicitud. Ver `communication-flow.md`, sección 6.

---

## 6. Endpoint

```
POST /orchestrator/{userId}/chat
Content-Type: application/json

{ "mensaje": "Como voy esta semana respecto a mi meta?" }
```

Devuelve la traza completa de la sección 5.

Es la **primera superficie HTTP conversacional del sistema**: hasta el Sprint 2
el Wellness Coach solo se invocaba desde las pruebas y el script de evaluación,
sin ruta propia. Se expone a través del orquestador y no de cada agente, que es
lo coherente con el patrón Supervisor — el cliente no necesita saber qué agentes
existen ni cuál le corresponde a su pregunta.

Los endpoints del Sprint 1 permanecen intactos, incluido `/compare`.

---

## 7. Documentos relacionados

| Tema | Documento |
|---|---|
| Justificación del patrón | `orchestration-pattern.md` |
| Política de delegación y reparto | `delegation-rules.md` |
| Contrato de mensajes | `communication-flow.md` |
| Diagramas del flujo | `docs/architecture/orchestration-flow.md` |
| Resultados de la evaluación | `docs/evaluation/multiagent-evaluation.md` |
