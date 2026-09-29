# Despliegue en la Nube

**Sprint 3 — Sistemas Multiagente** · Plataforma Inteligente Wellness 2.0 · Equipo 1

Qué se publica, dónde, qué lo dispara y qué sigue haciéndose a mano.

---

## 1. Qué se publica y dónde

| Pieza | Dónde vive | Cómo se despliega |
|---|---|---|
| Backend (FastAPI) | Cloud Run, servicio `wellness-backend` en `us-central1` | **Automático** al integrar en `main` |
| Frontend (PWA React) | Firebase Hosting, proyecto `runcoach-ai-496921` | **Automático**, después del backend |
| Firestore, Vertex AI | Servicios gestionados de GCP | No se despliegan |
| Índice de ChromaDB | Versionado en el repositorio, viaja en la imagen | Se reindexa con un script antes de construir |

### 1.1 El orden importa: backend primero

La primera versión de este pipeline automatizaba solo el frontend, con el
argumento de que publicar archivos estáticos necesita permisos mucho más
estrechos que publicar el backend. El argumento sobre los permisos es cierto,
pero la conclusión era mala: **automatizar solo una mitad introduce un desfase
que antes no existía.**

Con los dos despliegues manuales, nadie publica media versión sin darse cuenta.
Con uno solo automatizado, un cambio que toca las dos partes publica la
interfaz nueva contra el backend viejo, y el síntoma es un 404 en endpoints que
la interfaz da por existentes. No es hipotético: es exactamente lo que pasó al
probar el chat multiagente mientras el frontend apuntaba todavía a los
servicios desplegados del Sprint 2.

Por eso el job del frontend **depende** del job del backend. Si el backend
falla, el frontend no se publica y el sistema se queda entero en la versión
anterior, que es un estado coherente.

### 1.2 Los cuatro servicios del Sprint 2 siguen en pie

Hasta el Sprint 2 el backend eran cuatro microservicios desplegados por
separado —`auth-service`, `sessions-service`, `metrics-service`,
`agent-service`, todos en `us-central1`— y el frontend publicado apuntaba a
ellos. El Sprint 3 los consolidó en una sola aplicación FastAPI, que es la que
este pipeline despliega como `wellness-backend`.

La cobertura se verificó ruta por ruta, no de memoria: **las veinte rutas de
los cuatro servicios existen en el backend consolidado**, que además añade
`/agent/{userId}/compare` y los tres endpoints del orquestador.

Aun así **no se apagan**, por una razón que no es funcional sino operativa:
son la vía de vuelta. Si una revisión del backend nuevo falla durante una
demostración, revertir es cambiar las cuatro `VITE_*_URL` a los servicios
viejos y relanzar el workflow, un par de minutos. Sin ellos no hay a dónde
volver. Cloud Run escala a cero, así que tenerlos parados no tiene coste
apreciable.

**Conviene no confundirlos con el «modo legacy».** Son cosas distintas con
nombre parecido. El modo legacy es una de las dos arquitecturas de
`WellnessAgent` —prompt estático frente a RAG— y vive **dentro** del backend
consolidado, en `src/agents/wellness/agent.py`. La pestaña de comparativa lo
ejercita contra este backend, no contra los servicios antiguos. Apagarlos no
afectaría al modo legacy en absoluto.

### 1.3 Por qué no GitHub Pages para la aplicación

Se evaluó y se descartó **para la aplicación**. Pages sirve archivos estáticos
y no puede ejecutar FastAPI, así que el backend seguiría en Cloud Run de todas
formas. Mover solo el frontend obligaría a:

- cambiar la ruta base del bundle (`base` en `vite.config.js`), porque el sitio
  colgaría de `/wellness-platform-team1/` y no de la raíz;
- añadir un `404.html` que replique el `index.html`, porque Pages no reescribe
  las rutas y recargar `/dashboard` daría un 404;
- dar de alta el dominio `*.github.io` en los *authorized domains* de Firebase
  Auth, o el login dejaría de funcionar;
- permitir ese origen en el CORS del backend.

Cuatro cambios para terminar en el mismo sitio: un frontend estático llamando a
Cloud Run. Hosting ya lo hace, ya está configurado y ya sirve el dominio que la
aplicación usa.

---

## 2. El pipeline

`.github/workflows/deploy.yml`

```
push a main
   │
   ├─► suite de pruebas ───────────────────────────┐
   │                                                │
   └─► detectar qué cambió ─────────────────────────┤
                                                    ▼
                    ¿cambió el backend? ──► build ──► Cloud Run ──► /health
                                                              │
                                                              ▼
                    ¿cambió el frontend? ──► lint ──► config ──► build ──► Hosting
```

**Solo se despliega lo que cambió.** Reconstruir la imagen del backend tarda
minutos, así que el job `cambios` mira qué rutas se tocaron y salta lo que no
hace falta, sin perder el orden cuando cambian las dos. En un
`workflow_dispatch` no hay diff contra el que comparar y se despliegan ambas,
que es lo que se espera de una publicación manual.

### 2.1 Las puertas del backend

1. **La suite de pruebas.** Invoca `tests.yml` con `workflow_call` en lugar de
   repetir sus pasos. Duplicarlos habría creado dos definiciones de «las
   pruebas pasan» que se desincronizan a la primera de cambio.
2. **La construcción de la imagen.**
3. **`/health` responde 200.** Que `gcloud run deploy` termine sin error no
   significa que el servicio funcione: Cloud Run puede publicar una revisión
   que arranca y responde 500 a todo. Se comprueba, con cinco reintentos
   espaciados para absorber el arranque en frío, **antes** de dejar que el
   frontend se publique contra ese backend.

### 2.2 Las puertas del frontend

1. **El lint.** Quedó en cero errores al montar el pipeline. Dos reglas que
   solo afectan a la experiencia de desarrollo están degradadas a aviso, con el
   motivo escrito en `eslint.config.js`; siguen apareciendo en cada corrida.
2. **La configuración.** La más importante y la menos obvia: **si falta una
   variable, el build no falla.** Vite sustituye las ausentes por cadenas
   vacías y produce un bundle que compila y se publica, pero que no puede
   autenticar a nadie ni hablar con el backend. Sin esta comprobación, el
   síntoma aparecería en el navegador de quien abra la aplicación y no en el
   log del pipeline.
3. **El build.**

También se puede lanzar todo a mano desde la pestaña Actions
(`workflow_dispatch`), útil para ensayar la demostración sin integrar en
`main`.

### 2.3 Por qué el frontend usa `always()` en su condición

Un job saltado hace que sus dependientes se salten también. Cuando solo cambia
el frontend, el job del backend se salta **legítimamente**, y sin `always()`
el frontend no llegaría a ejecutarse nunca en ese caso. La condición acepta que
el backend se haya saltado y rechaza que haya fallado o se haya cancelado.

### 2.4 Por qué `vite build` y no `npm run build`

El script de npm ejecuta antes `scripts/bump-version.js`, que incrementa el
patch en `package.json`. En CI ese cambio se descarta al terminar el job, de
modo que **la versión publicada no existiría en el repositorio**: el
`Beta vX.Y.Z` de la pantalla de login apuntaría a un número imposible de
encontrar en la historia, y saltaría valores cada vez que alguien construyera
en local.

Invocando `vite build` directamente, lo publicado siempre lleva la versión
commiteada. Subirla sigue siendo deliberado: `npm run build` en local y
commitear el `package.json` resultante.

---

## 3. Qué hay que configurar una sola vez

### 3.1 Un secreto

| Nombre | Qué es |
|---|---|
| `GCP_SERVICE_ACCOUNT` | JSON completo de una cuenta de servicio con permiso para desplegar |

Se genera en la consola de GCP (IAM → Cuentas de servicio → Claves → Crear
clave JSON) y se pega entero en **Settings → Secrets and variables → Actions →
Secrets**.

Los roles que necesita, y solo esos:

| Rol | Para qué |
|---|---|
| Cloud Run Admin | Publicar revisiones del backend |
| Cloud Build Editor | Construir la imagen desde el Dockerfile |
| Artifact Registry Writer | Guardar la imagen construida |
| Service Account User | Asignar al servicio su identidad de ejecución |
| Firebase Hosting Admin | Publicar el frontend |

Conviene que sea una cuenta **creada para esto y nada más**, no la que ya usa
el backend en ejecución: esa tiene acceso a Firestore y a Vertex AI, que un
workflow de despliegue no necesita.

**Esta clave es una credencial de larga vida.** Si se filtra, sirve hasta que
alguien la revoque a mano, y con esos roles permite publicar código
arbitrario en el proyecto. La alternativa correcta es **Workload Identity
Federation**: GitHub intercambia su token OIDC por credenciales temporales y
no queda nada permanente guardado. Se eligió la clave por tiempo, con la
entrega encima, y queda anotado aquí como deuda explícita y no como decisión
definitiva. Migrarlo es media hora de `gcloud` y cambiar cuatro líneas del
workflow.

### 3.2 Tres variables del backend

| Variable | Valor típico |
|---|---|
| `GEMINI_MODEL` | `gemini-2.5-flash` |
| `EMBEDDING_MODEL` | `text-embedding-004` |
| `ZONA_HORARIA` | `America/Caracas` |

`ZONA_HORARIA` no es cosmética. Es la zona en la que el sistema decide qué día
es hoy y qué sesiones caen dentro de la semana en curso, y debe ser la de los
corredores, **no la del servidor**. Cloud Run corre en UTC: dejarlo así hacía
que a partir de las ocho de la noche en Venezuela el backend creyera que ya era
el día siguiente, y el domingo a esa hora reiniciaba la semana cuatro horas
antes de tiempo, con el kilometraje acumulado desapareciendo del panel.

Los timestamps que se persisten (`createdAt`, `generadoEn`) siguen en UTC y no
dependen de esta variable: marcan **cuándo** ocurrió algo, no en qué día del
calendario del corredor.

`GCP_PROJECT` y `GCP_LOCATION` las fija el propio workflow, porque son las del
servicio donde despliega y no tendría sentido que discreparan.

Cambiar `EMBEDDING_MODEL` **invalida el índice existente**: los vectores de
ChromaDB se generaron con el modelo actual y no son comparables con los de
otro. Hay que reindexar y reconstruir la imagen.

### 3.3 Diez variables del frontend, que no son secretos

Van en **Variables**, no en Secrets, y la distinción es deliberada:

| Variable | Qué lleva |
|---|---|
| `VITE_AUTH_URL` | URL del backend en Cloud Run |
| `VITE_SESSIONS_URL` | La misma |
| `VITE_METRICS_URL` | La misma |
| `VITE_AGENT_URL` | La misma |
| `VITE_FIREBASE_API_KEY` | Configuración web de Firebase |
| `VITE_FIREBASE_AUTH_DOMAIN` | Íd. |
| `VITE_FIREBASE_PROJECT_ID` | Íd. |
| `VITE_FIREBASE_STORAGE_BUCKET` | Íd. |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Íd. |
| `VITE_FIREBASE_APP_ID` | Íd. |

`VITE_ORCHESTRATOR_URL` es opcional: si no se define, el orquestador se busca
en `VITE_AGENT_URL`.

**Ninguno de estos valores es secreto, y tratarlos como si lo fueran sería
engañoso.** Vite los incrusta en el bundle en tiempo de compilación, así que
cualquiera puede leerlos abriendo el JavaScript publicado. La clave de API web
de Firebase no es una credencial: identifica al proyecto, no autoriza nada.
Guardarlos como secretos daría la impresión de una protección que no existe, y
esconde de la vista una configuración que conviene poder revisar.

**Lo que sí protege los datos es la verificación del token en el backend**
(`src/api/seguridad.py`), y conviene ser preciso sobre por qué es la única
capa: las reglas de seguridad de Firestore **no aplican aquí**, porque el
backend usa el Admin SDK, que las salta por diseño. Ninguna petición llega a
Firestore desde el navegador; todas pasan por la API.

Esa verificación se añadió al montar este pipeline, y su ausencia era un
agujero real: el frontend enviaba el token desde el Sprint 1 y el backend lo
ignoraba, de modo que cualquiera que conociera un `uid` podía leer y escribir
el perfil, las sesiones, los objetivos y el historial de chat de ese corredor
con un `curl`. Con `--allow-unauthenticated` y el CORS abierto, publicar el
backend sin esa capa habría dejado los datos de los corredores accesibles
desde cualquier navegador.

Las cuatro URL están separadas porque la aplicación nació sobre cuatro
microservicios. Desde el Sprint 3 apuntan al mismo backend, y se conservan
separadas por si volvieran a dividirse.

---

## 4. Desplegar el backend a mano

El pipeline lo hace solo, pero conviene poder reproducirlo: es lo que se usa
para depurar un despliegue que falla y lo que necesita cualquiera que levante
el sistema en su propio proyecto de GCP.

Desde la raíz del repositorio, con `gcloud` autenticado:

```bash
gcloud run deploy wellness-backend \
  --source . \
  --region us-central1 \
  --project runcoach-ai-496921 \
  --allow-unauthenticated
```

Construye desde el `Dockerfile` de la raíz. Ese archivo no existía hasta el
Sprint 3: el backend eran cuatro microservicios, cada uno con el suyo, y al
consolidarlos el repositorio se quedó sin ninguno. Podía levantarse en local
siguiendo `local-setup.md`, pero no desplegarse, lo cual contradecía el
criterio de S3-07 sobre reproducibilidad.

Tres cosas que conviene recordar:

**Las variables de entorno del backend** (`GCP_PROJECT`, `GCP_LOCATION`,
`GEMINI_MODEL`, `EMBEDDING_MODEL`) se configuran en el servicio de Cloud Run,
no en un `.env`. Ver `docs/deployment/environment-variables.md`.

**Las credenciales no van en un archivo.** Cloud Run aporta la identidad del
servicio; `GOOGLE_APPLICATION_CREDENTIALS` debe quedar sin definir, que es la
razón de que esté comentada en `.env.example`.

**El índice de ChromaDB viaja en la imagen.** Si se cura un documento nuevo en
la base de conocimiento, hay que reindexar antes de desplegar, o el backend
servirá el índice viejo sin avisar de nada.

### 4.1 Qué queda pendiente

**Migrar a Workload Identity Federation**, por lo dicho en 3.1.

**Canales de vista previa de Hosting por Pull Request.** Firebase puede
publicar cada PR en una URL temporal propia, lo que permitiría revisar un
cambio de interfaz antes de integrarlo en lugar de después.

**Partir el bundle del frontend.** Sale en unos 840 kB, 249 kB comprimido, y
Vite avisa. La causa es que todo va en un solo chunk, con `recharts` y
`firebase` pesando lo suyo. Se arregla con `import()` dinámico por ruta.

---

## 5. Verificar que un despliegue salió bien

```bash
curl https://<backend>/health

python -m scripts.verificacion.verificar_integraciones
```

El primero confirma que el backend responde. El segundo ejercita las cinco
dependencias externas con diez comprobaciones, y devuelve código de salida
distinto de cero si alguna falla, de modo que se puede encadenar. Existe porque
la suite usa mocks y no toca ningún servicio: la suite verifica la lógica, esto
verifica que el mundo exterior está donde lo dejamos.

El pipeline ya comprueba `/health` antes de publicar el frontend, pero no
ejecuta el script de integraciones: necesita credenciales de GCP y un usuario
sembrado, y hacerlo en cada despliegue escribiría en Firestore desde el CI.
Se corre a mano cuando hay dudas.

### 5.1 Volver atrás

Cloud Run conserva las revisiones anteriores. Para devolver todo el tráfico a
la última que funcionaba:

```bash
gcloud run services update-traffic wellness-backend \
  --to-revisions <revision-anterior>=100 \
  --region us-central1 --project runcoach-ai-496921
```

Si el problema no es una revisión concreta sino el backend consolidado
entero, la vía de vuelta son los cuatro servicios del Sprint 2 (ver 1.2):
apuntar las cuatro `VITE_*_URL` a sus URL y relanzar el workflow.

---

## 6. Documentos relacionados

| Documento | Qué cubre |
|---|---|
| `local-setup.md` | Levantar el sistema completo en local |
| `environment-variables.md` | Cada variable, qué hace y de dónde sale |
| `../architecture/integraciones-datos.md` | Qué servicios externos consume el sistema |
