# Imagen de runtime: solo sirve la API.
#
# La ingesta del CORPUS se hace en local y aquí viaja ya indexado, así que no
# entran OpenCV ni Tesseract, que son los que pesan.
#
# PyMuPDF sí entra, porque los documentos que sube el usuario se leen aquí. Lo
# que sigue fuera es el OCR: un escaneo sin capa de texto se rechaza con un
# mensaje que lo dice, en vez de triplicar el tamaño de la imagen.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Todo lo que importa api.py, y nada más. Si se añade un módulo nuevo al
# backend, va aquí: el error se ve solo al arrancar el contenedor, no al
# construirlo, así que un build verde no significa que la imagen esté completa.
COPY api.py auth.py nube.py ./
COPY rag/ rag/
COPY documentos/ documentos/
# El índice (9 MB) y el corpus parseado se copian ya construidos.
COPY data/index/ data/index/
COPY data/uit.json data/

EXPOSE 8000

# El host debe ser 0.0.0.0 para aceptar tráfico fuera del contenedor, y el
# puerto lo asigna la plataforma (Render, Railway y Fly inyectan $PORT).
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
