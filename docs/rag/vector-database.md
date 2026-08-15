# Base de Datos Vectorial

**Sprint 1 — Ingeniería del Conocimiento y Sistemas RAG**
Plataforma Inteligente Wellness 2.0 · Equipo 1

Implementación: [`src/rag/vector_store/store.py`](../../src/rag/vector_store/store.py)

---

## 1. Función en la arquitectura

Con 82 chunks sería técnicamente viable comparar la consulta contra todos los vectores secuencialmente. El problema es de escalabilidad y de persistencia:

- **Escalabilidad.** La comparación exhaustiva es lineal en el número de vectores. Con decenas de miles de fragmentos deja de ser viable en tiempo de respuesta aceptable.
- **Persistencia.** Recalcular los embeddings en cada arranque del servicio es lento y tiene coste monetario.

Una base vectorial resuelve ambos: indexa los vectores en estructuras de búsqueda aproximada de vecinos más próximos y los persiste en disco.

---

## 2. Selección: ChromaDB

| Parámetro | Valor |
|---|---|
| Motor | ChromaDB 0.5.23 |
| Modo | `PersistentClient` (embebido, sin servidor) |
| Ubicación | `data/vector_store/` |
| Colección | `wellness_knowledge` |
| Espacio métrico | Coseno (`hnsw:space: cosine`) |
| Índice | HNSW |

### Justificación frente a FAISS

El programa de la asignatura menciona ambas opciones. Se seleccionó ChromaDB por tres razones:

**Persistencia nativa.** ChromaDB escribe a disco de forma transparente. FAISS requiere serialización y carga manual del índice, además de gestionar por separado el almacenamiento de documentos y metadata.

**Filtrado por metadata integrado.** ChromaDB admite filtros sobre metadata en la propia consulta (`where={"categoria": "nutricion"}`). En FAISS habría que implementar el filtrado como capa externa, ya sea prefiltrando y reconstruyendo índices o posfiltrando resultados con pérdida de precisión en el top-k.

**Inspeccionabilidad.** La colección puede consultarse, contarse y examinarse directamente, lo cual tiene valor didáctico y facilita la depuración.

FAISS ofrece ventaja sustancial en rendimiento a escala de millones de vectores. A escala de 82 fragmentos esa ventaja es irrelevante, mientras que la trazabilidad y el filtrado sí aportan valor inmediato.

| Criterio | ChromaDB | FAISS |
|---|---|---|
| Persistencia | Nativa | Manual |
| Filtrado por metadata | Integrado | Externo |
| Almacenamiento de documentos | Integrado | Separado |
| Rendimiento a gran escala | Bueno | Superior |
| Complejidad operativa | Baja | Media |

---

## 3. Configuración crítica: espacio métrico

**ChromaDB emplea distancia L2 (euclídea) por defecto.** Es necesario declarar explícitamente el espacio coseno al crear la colección:

```python
get_client().get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)
```

Omitir esta configuración no produce error: el sistema funciona pero ordena los resultados con una métrica distinta a la esperada. Dado que los embeddings de texto se comparan convencionalmente por coseno —la magnitud del vector correlaciona con la longitud del texto, que no es dimensión semántica—, emplear L2 introduce un sesgo por longitud.

Es un fallo silencioso: sin síntoma visible, con degradación real de la recuperación.

---

## 4. Distancia frente a similitud

ChromaDB devuelve **distancia**, no similitud. En espacio coseno la conversión es:

```
similitud = 1 − distancia
```

Confundirlas invierte el orden de relevancia. La conversión se realiza en la capa de acceso para que el resto del sistema opere siempre con similitud:

```python
salida.append({
    "distancia": resultado["distances"][0][i],
    "similitud": 1 - resultado["distances"][0][i],
})
```

---

## 5. Idempotencia del índice

El pipeline de ingesta debe poder ejecutarse repetidamente sin duplicar contenido y reflejando las modificaciones de los documentos. Se implementa mediante dos mecanismos.

### 5.1 Identificador determinista

```python
def chunk_id(doc_id, chunk_index, texto):
    huella = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:12]
    return f"{doc_id}-{chunk_index:03d}-{huella}"
```

El identificador combina documento, posición y huella del contenido. Un mismo contenido produce siempre el mismo identificador, lo que permite detectar duplicados y verificar integridad.

### 5.2 Reemplazo por documento

Antes de indexar un documento se eliminan sus fragmentos previos:

```python
def borrar_documento(doc_id: str) -> int:
    coleccion = get_collection()
    existentes = coleccion.get(where={"doc_id": doc_id})
    ids = existentes.get("ids", [])
    if ids:
        coleccion.delete(ids=ids)
    return len(ids)
```

Esto garantiza que editar un documento —añadir una sección, corregir contenido— se refleje limpiamente en el índice sin residuos de la versión anterior.

### 5.3 Orden de operaciones

El script de ingesta genera **los embeddings antes de modificar el estado persistente**:

```
[1] Chunking
[2] Generación de embeddings   ← paso que puede fallar
[3] Eliminación de versiones previas
[4] Inserción
```

La versión inicial invertía los pasos 2 y 3. Al fallar la generación de embeddings por exceso de tokens, la colección quedaba vaciada sin contenido de reemplazo.

El principio general: **ejecutar primero las operaciones que pueden fallar y modificar el estado persistente solo cuando se dispone de todo lo necesario.**

---

## 6. Preparación para gestión documental dinámica

El diseño idempotente y dirigido por metadata anticipa un módulo administrativo de carga documental previsto para sprints posteriores. Las piezas ya resueltas:

- Identificación por `doc_id` sin rutas fijas
- Reemplazo selectivo por documento
- Identificadores deterministas por contenido
- Estadísticas de colección por documento

La implementación de ese módulo requeriría únicamente una capa de API y de interfaz sobre el pipeline existente.

**Precisión terminológica:** ese módulo no realizaría *autoentrenamiento*. El modelo de lenguaje permanece invariable. Lo que se modifica es el corpus recuperable mediante reindexación. La distinción es relevante para caracterizar correctamente el sistema en la documentación técnica.

---

## 7. Estado del índice

```
COLECCIÓN: 82 chunks
  KB-001:  13 chunks
  KB-002:  12 chunks
  KB-003:  12 chunks
  KB-004:  14 chunks
  KB-005:  10 chunks
  KB-006:  10 chunks
  KB-007:  11 chunks
```

Consultable mediante:

```python
from src.rag.vector_store.store import estadisticas
estadisticas()
```

---

## 8. Incidencia operativa: telemetría

ChromaDB 0.5.23 presenta una incompatibilidad de firma con su biblioteca de telemetría PostHog, que genera mensajes de error repetidos:

```
Failed to send telemetry event ClientCreateCollectionEvent:
capture() takes 1 positional argument but 3 were given
```

Los mensajes son inocuos —no afectan a la funcionalidad— pero contaminan la salida. Se suprimen mediante variable de entorno y silenciado del logger correspondiente, antes de importar la biblioteca:

```python
os.environ["ANONYMIZED_TELEMETRY"] = "False"
logging.getLogger("chromadb.telemetry").setLevel(logging.CRITICAL)
logging.getLogger("chromadb.telemetry.product.posthog").setLevel(logging.CRITICAL)
```

---

## 9. Limitaciones

**Sin réplica ni alta disponibilidad.** El cliente embebido escribe en el sistema de archivos local. Para despliegue en Cloud Run con múltiples instancias sería necesario un volumen compartido o migrar a un servicio vectorial gestionado —Vertex AI Vector Search o ChromaDB en modo servidor.

**Índice versionado en el repositorio.** El directorio `data/vector_store/` contiene ficheros binarios que se versionan en Git. Es aceptable a esta escala y garantiza reproducibilidad inmediata, pero no escala: en un corpus grande correspondería regenerar el índice en el proceso de despliegue en lugar de versionarlo.

**Sin control de concurrencia.** No hay mecanismo de bloqueo. Dos procesos de ingesta simultáneos podrían producir estado inconsistente. No es problema en el flujo actual —la ingesta es manual y puntual— pero requeriría atención en el módulo administrativo previsto.

**Parámetros HNSW por defecto.** No se ajustaron los parámetros de construcción del índice (`ef_construction`, `M`). A esta escala los valores por defecto son adecuados; en corpus mayores su optimización afectaría al equilibrio entre precisión y velocidad de búsqueda.
