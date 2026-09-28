# Imagen del backend FastAPI de la Plataforma Inteligente Wellness.
#
# POR QUE EXISTE ESTE ARCHIVO
#
# Hasta el Sprint 3 el backend eran cuatro microservicios, cada uno con su
# Dockerfile en su carpeta. Al consolidarlos en una sola aplicacion FastAPI el
# repositorio se quedo sin ninguno, de modo que no contenia la informacion
# necesaria para desplegarlo: un tercero podia levantar el sistema en local
# siguiendo local-setup.md, pero no reproducir el despliegue. Eso contradecia
# el criterio de S3-07 sobre reproducibilidad.
#
# POR QUE UNA IMAGEN Y NO BUILDPACKS
#
# 'gcloud run deploy --source .' sin Dockerfile usa buildpacks, que buscan un
# main.py en la raiz o un Procfile para saber que arrancar. La aplicacion vive
# en src/app/main.py, asi que haria falta un Procfile igualmente. Con una
# imagen explicita, ademas, se controla la version de Python -- la misma 3.11
# del CI y del entorno de desarrollo -- y se controla que entra y que no.

FROM python:3.11-slim

# PYTHONDONTWRITEBYTECODE: no escribir .pyc en una imagen que es de solo
#   lectura en la practica.
# PYTHONUNBUFFERED: sin esto, los logs de la aplicacion se quedan en el buffer
#   y Cloud Logging los recibe a destiempo o los pierde si el contenedor
#   termina. Depurar un despliegue sin logs fiables es innecesariamente caro.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Las dependencias en su propia capa, antes del codigo. Docker reutiliza esta
# capa mientras requirements.txt no cambie, y es la unica que tarda minutos:
# chromadb y google-cloud-aiplatform arrastran bastante.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo lo que el backend necesita en ejecucion. Lo que queda fuera esta en
# .dockerignore y no es accidental: el frontend, las pruebas, la documentacion,
# los scripts de evaluacion y el entorno virtual no pintan nada en la imagen.
COPY src/ ./src/
COPY prompts/ ./prompts/

# El indice de ChromaDB viaja DENTRO de la imagen, a proposito.
#
# Son unos 5 MB y la alternativa -- reconstruirlo al arrancar -- costaria una
# llamada de embeddings por fragmento en cada arranque en frio de Cloud Run, y
# haria que dos instancias del mismo servicio pudieran responder con indices
# distintos si el modelo de embeddings cambiara entre una y otra.
#
# La contrapartida: curar un documento nuevo en la base de conocimiento exige
# reindexar ANTES de construir la imagen. Si no, el backend sirve el indice
# viejo sin avisar de nada.
COPY data/vector_store/ ./data/vector_store/
COPY data/knowledge_base/ ./data/knowledge_base/

# Usuario sin privilegios. Cloud Run ya aisla el contenedor, pero correr como
# root dentro de el no aporta nada y amplia lo que un fallo de la aplicacion
# podria tocar.
RUN useradd --create-home --uid 1000 wellness && chown -R wellness:wellness /app
USER wellness

# Cloud Run inyecta PORT y espera que el proceso escuche ahi. El valor por
# defecto es 8080, pero fijarlo a mano rompe el dia que la plataforma decida
# otro. Se usa la forma shell del CMD para que ${PORT} se expanda.
ENV PORT=8080
EXPOSE 8080

CMD exec uvicorn src.app.main:app --host 0.0.0.0 --port ${PORT}
