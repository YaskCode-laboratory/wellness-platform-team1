# Variables de Entorno

**Plataforma Inteligente Wellness 2.0 — Equipo 1**

---

## 1. Backend

Plantilla en `.env.example`. Los cinco valores tienen defecto en
`src/utils/config.py` y `src/utils/fechas.py`, así que copiar el archivo tal
cual basta para trabajar contra este proyecto:

```bash
GCP_PROJECT=runcoach-ai-496921
GCP_LOCATION=us-central1
ZONA_HORARIA=America/Caracas
GEMINI_MODEL=gemini-2.5-flash
EMBEDDING_MODEL=text-embedding-004
```

| Variable | Requerida | Descripción |
|---|---|---|
| `GCP_PROJECT` | No (`runcoach-ai-496921`) | Proyecto de Google Cloud |
| `GCP_LOCATION` | No (`us-central1`) | Región de los modelos de Vertex AI |
| `ZONA_HORARIA` | No (`America/Caracas`) | Zona en la que el sistema razona sobre el calendario |
| `GEMINI_MODEL` | No (`gemini-2.5-flash`) | Modelo generativo de los agentes y del clasificador |
| `EMBEDDING_MODEL` | No (`text-embedding-004`) | Modelo de embeddings de indexación y recuperación |
| `GOOGLE_APPLICATION_CREDENTIALS` | Solo fuera de GCP | Ruta a una clave de cuenta de servicio. **Comentada en `.env.example` a propósito**: ver 2.1 |

**Sobre `ZONA_HORARIA`.** Decide qué día es «hoy» y qué sesiones entran en la
semana en curso, así que afecta a la carga semanal, a la comparación con la
meta y a los datos con los que razona el agente. Debe ser la zona de los
**corredores**, no la del servidor: Cloud Run corre en UTC, y con los corredores
en UTC−4 eso hacía que a partir de las ocho de la noche el backend creyera que
ya era el día siguiente, reiniciando la semana cuatro horas antes de tiempo.
Los timestamps que se persisten siguen en UTC y no dependen de esta variable.

**Sobre `EMBEDDING_MODEL`.** Cambiarlo **invalida el índice existente**: los
vectores de ChromaDB se generaron con el modelo actual y no son comparables con
los de otro. Hay que reindexar.

---

## 2. Autenticación contra Google Cloud

### 2.1 Desarrollo local

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project runcoach-ai-496921
```

**Y `GOOGLE_APPLICATION_CREDENTIALS` debe quedar sin definir.** Por eso está
comentada en `.env.example`: copiar el archivo con esa línea activa dejaría la
variable apuntando a una ruta inexistente, y los clientes de Google la
prefieren por encima de las Application Default Credentials. El resultado es un
error de archivo no encontrado que no sugiere su causa.

### 2.2 Cloud Run

La identidad de la cuenta de servicio del servicio se resuelve
automáticamente. No requiere variable ni fichero de credenciales.

### 2.3 Otros entornos

Descargar la clave de la cuenta de servicio y apuntar
`GOOGLE_APPLICATION_CREDENTIALS` a su ruta. **El fichero de claves nunca debe
versionarse.**

---

## 3. Permisos requeridos

### 3.1 Identidad de ejecución

La que usa el backend para funcionar:

| Rol | Uso |
|---|---|
| `roles/aiplatform.user` | Invocar Gemini y el modelo de embeddings |
| `roles/datastore.user` | Lectura y escritura en Firestore |
| `roles/firebaseauth.viewer` | Consulta de perfiles y verificación de tokens |

### 3.2 Identidad de despliegue

La del pipeline de CI/CD es **distinta y no debe reutilizarse**: necesita
publicar, no leer datos. Sus roles están en
[`cloud-deployment.md`](cloud-deployment.md) §3.1.

---

## 4. Frontend

Plantilla en `frontend/.env.example`. A diferencia del backend, **aquí sí hay
que editar**: las claves de Firebase son propias del proyecto y no tienen
defecto.

```bash
VITE_AUTH_URL=http://localhost:8000
VITE_SESSIONS_URL=http://localhost:8000
VITE_METRICS_URL=http://localhost:8000
VITE_AGENT_URL=http://localhost:8000

VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_STORAGE_BUCKET=
VITE_FIREBASE_MESSAGING_SENDER_ID=
VITE_FIREBASE_APP_ID=
```

`VITE_ORCHESTRATOR_URL` es opcional: si no se define, el orquestador se busca
en `VITE_AGENT_URL`.

**Por qué cuatro URL para un solo backend.** La aplicación nació sobre cuatro
microservicios —`auth`, `sessions`, `metrics`, `agent`— y desde el Sprint 3
apuntan todas al backend consolidado. Se conservan separadas por si volvieran a
dividirse. En despliegue llevan la URL del servicio de Cloud Run.

> **Vite lee el `.env` solo al arrancar.** Editarlo con el servidor de
> desarrollo corriendo no surte efecto, y recargar el navegador tampoco: hay
> que reiniciar `npm run dev`.

### 4.1 Estas variables no son secretos, y tratarlas como tales sería engañoso

Vite las incrusta en el bundle en tiempo de compilación, así que cualquiera
puede leerlas abriendo el JavaScript publicado. La clave de API web de Firebase
no es una credencial: identifica al proyecto, no autoriza nada. Por eso en el
pipeline van como *variables* de repositorio y no como *secrets*
(`cloud-deployment.md` §3.3).

**Lo que protege los datos es la verificación del token en el backend**
(`src/api/seguridad.py`), y conviene ser preciso sobre por qué es la única
capa: las reglas de seguridad de Firestore **no aplican**, porque el backend usa
el Admin SDK, que las salta por diseño. Ninguna petición llega a Firestore
desde el navegador; todas pasan por la API.

*(Versiones anteriores de este documento afirmaban lo contrario —que la
protección recaía en las reglas de Firestore—. Era falso por partida doble:
esas reglas no aplican con el Admin SDK, y hasta el Sprint 3 el backend ni
siquiera miraba el token que el frontend le enviaba.)*

---

## 5. Centralización de la configuración

Hasta el Sprint 1, el proyecto y la región estaban declarados **como constantes
en cuatro módulos** —`firestore_client.py`, `wellness/agent.py`, `embedder.py`
y `generator.py`—, lo que contradecía la existencia de `.env.example` y obligaba
a editar código para desplegar en otro proyecto.

**Resuelto en el Sprint 2, issue #10.** Hoy `src/utils/config.py` lee las cuatro
del entorno con valor por defecto, y los módulos importan de ahí:

```python
GCP_PROJECT = os.getenv("GCP_PROJECT", "runcoach-ai-496921")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
```

El Sprint 3 agregó `src/utils/fechas.py` con el mismo criterio para
`ZONA_HORARIA`, por la misma razón que motivó la centralización original:
**tener la definición duplicada en dos módulos fue lo que permitió que ambos
derivaran hacia UTC sin que nadie lo notara.**

---

## 6. Ficheros excluidos del control de versiones

Declarados en `.gitignore`:

```
.env
venv/
__pycache__/
*.py[codz]
node_modules/
dist/
.DS_Store
**/.DS_Store
```

Nunca deben versionarse claves de cuentas de servicio ni ficheros `.env` con
valores reales.
