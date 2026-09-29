# MCP — Model Context Protocol

**Sprint 3 — Sistemas Multiagente** · Plataforma Inteligente Wellness 2.0 · Equipo 1

Análisis arquitectónico de cómo el sistema evolucionaría hacia MCP. **No se
implementa en este sprint**, conforme al alcance del issue S3-04, que plantea
considerar estos mecanismos *«arquitectónicamente, sin requerir una
implementación completa»*.

Para el protocolo entre agentes, ver `a2a.md`. **No compiten**: MCP mira hacia
abajo, a cómo los agentes alcanzan sus capacidades; A2A mira hacia los lados, a
cómo los agentes se hablan entre sí.

---

## 1. Qué estandariza MCP

La forma en que un modelo accede a **herramientas y fuentes de datos**: cómo se
descubren las capacidades disponibles, cómo se describen sus parámetros y cómo
se invocan. Relación cliente ↔ servidor de capacidades.

---

## 2. Qué se expondría aquí

Las capacidades que hoy son funciones Python invocadas por tool calling:

| Capacidad actual | Como servidor MCP |
|---|---|
| `consultar_historial_sesiones` | Servidor de datos del corredor (Firestore) |
| `consultar_progreso_objetivo` | Servidor de datos del corredor (Firestore) |
| `consultar_clima` | Servidor de clima (Open-Meteo) |
| `consultar_base_conocimiento` | Servidor de conocimiento (ChromaDB, con filtro por categoría) |

---

## 3. Qué está ya preparado

### 3.1 El registro de herramientas es declarativo

`_HERRAMIENTAS` en `src/agents/wellness_coach/tools/registro.py` es una lista de
diccionarios con nombre, descripción y esquema de parámetros — que es, en
esencia, lo que un servidor MCP publica en su descubrimiento de herramientas.

La conversión sería **una transformación de formato, no un rediseño**.

### 3.2 El despacho está centralizado

Todas las invocaciones pasan por `despachar()`, así que sustituir la ejecución
local por una llamada a un servidor MCP toca un solo punto del código.

### 3.3 La degradación ya está resuelta ahí mismo

`_despachar_con_degradacion()`, de la corrección S2-04, convierte cualquier
fallo en una observación controlada. Un servidor MCP remoto añade modos de fallo
nuevos —red, timeout, servidor caído— pero **el punto donde tratarlos ya existe
y ya los absorbe**, porque captura `Exception` de forma amplia precisamente para
no depender de anticipar qué puede fallar.

---

## 4. Qué habría que construir

- Un servidor MCP por grupo de capacidades, con su descubrimiento.
- **Autenticación entre el agente y los servidores**, que hoy no existe porque
  todo corre en el mismo proceso con las mismas credenciales.
- Manejo de la latencia adicional por salto de red, sobre una latencia que ya es
  alta: 9 294 ms de promedio y 26 s en el peor caso medido.

---

## 5. Cuándo convendría

El beneficio real de MCP aparece cuando **las capacidades se comparten entre
consumidores distintos**. Hoy la base de conocimiento la usan dos agentes del
mismo proceso; exponerla por MCP no aporta nada que un `import` no resuelva.

Convendría si:

- El **módulo administrativo de ingesta documental** previsto en el roadmap se
  construyera como servicio aparte y necesitara consultar la misma knowledge
  base.
- Un **cliente externo a la plataforma** necesitara acceder al conocimiento
  curado.
- Los agentes de motivación y analítica se desplegaran por separado y
  compartieran las capacidades de datos.

---

## 6. Recomendación

**No adoptar MCP en el estado actual.** Resuelve un problema de sistemas
distribuidos que este sistema todavía no tiene, y cobra por adelantado en
autenticación, latencia de red y modos de fallo nuevos.

Si llegara el momento, **MCP conviene antes que A2A**: es el cambio más acotado
—toca un solo punto de despacho— y el que menos superficie de seguridad abre,
porque no implica propagar la identidad del corredor entre servicios.

---

## 7. Estado en el repositorio

`src/orchestration/communication/mcp/` permanece vacío **a propósito**. Crear
estructura para algo que no se va a construir en este sprint solo produciría la
impresión de un avance que no existe.
