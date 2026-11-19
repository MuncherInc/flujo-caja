# Despliegue del Prototipo de Flujo de Caja

## Opción 1: Streamlit Community Cloud (más fácil y gratis)

1. Sube la carpeta `flujo_caja_prototipo` a un repositorio de GitHub.
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu cuenta de GitHub y selecciona el repo.
4. Archivo principal: `app.py`
5. Listo. Te da una URL pública.

## Opción 2: Docker (local o servidor)

```bash
cd flujo_caja_prototipo
docker build -t flujo-caja .
docker run -p 8501:8501 -v $(pwd)/flujo_caja.db:/app/flujo_caja.db flujo-caja
```

Abre `http://localhost:8501`

## Opción 3: Google Cloud Run (recomendado para producción)

```bash
# Autenticarte
gcloud auth login
gcloud config set project TU_PROYECTO

# Build y deploy
gcloud run deploy flujo-caja \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 8501
```

## Opción 4: Railway / Render / Fly.io

- Conecta el repo de GitHub.
- Detecta el Dockerfile automáticamente o usa:
  - Build command: `pip install -r requirements.txt`
  - Start command: `streamlit run app.py --server.port=$PORT --server.address=0.0.0.0`

## Variables de entorno (opcionales)

| Variable | Descripción |
|----------|-------------|
| `DATABASE_PATH` | Ruta de la base SQLite (por defecto `flujo_caja.db`) |

## Notas de producción

- La base SQLite es local al contenedor. Para persistencia real usa un volumen o migra a Postgres.
- Para multi-usuario agrega autenticación (Streamlit Authenticator o Google OAuth).
- El archivo `.streamlit/config.toml` ya está optimizado para headless.
