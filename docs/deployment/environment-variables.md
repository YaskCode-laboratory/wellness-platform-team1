# Variables de Entorno

**Plataforma Inteligente Wellness 2.0 — Equipo 1**

---

## 1. Backend

Plantilla en `.env.example`:

```bash
GCP_PROJECT=runcoach-ai-496921
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/ruta/a/service-account.json
```

| Variable | Requerida | Descripción |
|---|---|---|
| `GCP_PROJECT` | Sí | Proyecto de Google Cloud |
| `GCP_LOCATION` | Sí | Región de los modelos de Vertex AI |
| `ZONA_HORARIA` | No (`America/Caracas`) | Zona en la que el sistema razona sobre el calendario. Ver más abajo |
| `GOOGLE_APPLICATION_CREDENTIALS` | En despliegue | Ruta a la cuenta de servicio. No necesaria en local si se usan ADC ni en Cloud Run, que provee identidad nativa |

**Sobre `ZONA_HORARIA`.** Decide qué día es «hoy» y qué sesiones entran en la
semana en curso, así que afecta a la carga semanal, a la comparación con la
meta y a los datos con los que razona el agente. Debe ser la zona de los
corredores, no la del servidor: Cloud Run corre en UTC, y con los corredores en
UTC−4 eso hacía que a partir de las ocho de la noche el backend creyera que ya
era el día siguiente. Los timestamps que se persisten siguen en UTC y no
dependen de esta variable.

---

## 2. Autenticación

### Desarrollo local

```bash
gcloud auth application-default login
gcloud auth application-default set-quota-project runcoach-ai-496921
```

No requiere `GOOGLE_APPLICATION_CREDENTIALS`.

### Cloud Run

La identidad de la cuenta de servicio del servicio se resuelve automáticamente. No requiere variable ni fichero de credenciales.

### Otros entornos

Descargar la clave de la cuenta de servicio y apuntar `GOOGLE_APPLICATION_CREDENTIALS` a su ruta. **El fichero de claves nunca debe versionarse.**

---

## 3. Permisos requeridos

La identidad empleada necesita:

| Rol | Uso |
|---|---|
| `roles/aiplatform.user` | Invocar Gemini y el modelo de embeddings |
| `roles/datastore.user` | Lectura y escritura en Firestore |
| `roles/firebaseauth.viewer` | Consulta de perfiles de usuario |

---

## 4. Frontend

`frontend/.env`:

```bash
VITE_API_URL=https://<servicio-cloud-run>.run.app
VITE_FIREBASE_API_KEY=...
VITE_FIREBASE_AUTH_DOMAIN=...
VITE_FIREBASE_PROJECT_ID=runcoach-ai-496921
```

Para desarrollo contra el backend local:

```bash
VITE_API_URL=http://localhost:8080
```

> Las variables de Vite se exponen en el bundle del cliente. No deben contener secretos. Las claves de Firebase para web son públicas por diseño; la protección de datos recae en las reglas de seguridad de Firestore.

---

## 5. Deuda técnica identificada

Actualmente el proyecto y la región **están declarados como constantes en el código**, no leídos del entorno:

| Módulo | Constantes |
|---|---|
| `src/database/firestore_client.py` | `GCP_PROJECT` |
| `src/agents/wellness/agent.py` | `GCP_PROJECT`, `GCP_LOCATION`, `GEMINI_MODEL` |
| `src/rag/embeddings/embedder.py` | `GCP_PROJECT`, `GCP_LOCATION`, `EMBEDDING_MODEL` |
| `src/rag/generation/generator.py` | `GCP_PROJECT`, `GCP_LOCATION`, `GEMINI_MODEL` |

Esto contradice la existencia de `.env.example` y dificulta desplegar en un proyecto distinto sin modificar código.

**Corrección propuesta para el Sprint 2:** centralizar en `src/utils/config.py` con lectura de entorno y valores por defecto:

```python
import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT = os.getenv("GCP_PROJECT", "runcoach-ai-496921")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-004")
```

Los cuatro módulos importarían de ahí en lugar de declarar sus propias constantes.

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

Nunca deben versionarse claves de cuentas de servicio ni ficheros `.env` con valores reales.
