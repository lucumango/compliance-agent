# Cómo levantar el proyecto

Necesitas dos terminales. Las rutas son relativas a la raíz del repo.

## 1. Backend (puerto 8000)

```bash
cd backend
source .venv/bin/activate
uvicorn api:app --reload --port 8000
```

Comprobar: http://127.0.0.1:8000/api/salud
Documentación interactiva: http://127.0.0.1:8000/docs

La primera vez:

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # o requirements-ingesta.txt para procesar PDFs
cp .env.example .env                   # y coloca tu GOOGLE_API_KEY
```

## 2. Frontend (puerto 5173)

```bash
cd frontend
npm install      # la primera vez
npm run dev
```

Abrir: http://localhost:5173

## Sin interfaz gráfica

```bash
cd backend && source .venv/bin/activate
python -m rag.cli                 # chat en terminal
python -m rag.eval                # evaluación de recuperación
python -m ingestion.validate      # calidad del corpus
```

## Si cambias el corpus

Reconstruye el índice tras reingerir (tarda ~6 min por los límites de cuota):

```bash
python -m ingestion.ingest
python -m rag.index
```

Para añadir documentos nuevos, sigue [docs/INGESTA.md](docs/INGESTA.md).
