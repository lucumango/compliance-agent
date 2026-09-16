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
COPY api.py auth.py nube.py auditoria.py cobertura.py ./
COPY rag/ rag/
COPY agentes/ agentes/
COPY registros/ registros/
COPY documentos/ documentos/
# El índice (9 MB) y el corpus parseado se copian ya construidos.
COPY data/index/ data/index/
COPY data/uit.json data/

# Nada de aquí dentro necesita root. Un fallo en la lectura de un PDF subido
# —PyMuPDF procesa ficheros de origen desconocido— se queda con los permisos de
# un usuario que no puede escribir en /app ni instalar nada.
#
# Va DESPUÉS de los COPY: los ficheros se copian como root y quedan de solo
# lectura para `carlos`, que es exactamente lo que se quiere. La aplicación no
# escribe en disco.
# Las listas de sanciones se bajan AL CONSTRUIR la imagen, no se versionan:
# cambian a diario y una foto guardada en git sería vieja el día siguiente. Así
# cada despliegue lleva las de ese día. Son ~90 MB de descarga y 2 MB de índice.
#
# Si una fuente está caída el build NO falla: la API arranca sin cotejo y lo
# dice en /api/diego/registros. Un despliegue bloqueado porque la ONU tarda en
# responder es peor que un cotejo que avisa de que no está.
#
# El padrón de SUNAT no entra: son 1,5 GB y no caben en el plan gratuito. En
# producción el cotejo por RUC responde que no está disponible.
# El crudo se borra pase lo que pase: son ~80 MB que la imagen no necesita.
RUN (python -m registros.actualizar \
     || echo "AVISO: no se pudieron bajar todos los registros públicos; el cotejo lo dirá") \
    && rm -rf data/registros/crudo

RUN useradd --create-home --uid 10001 carlos
USER carlos

EXPOSE 8000

# El host debe ser 0.0.0.0 para aceptar tráfico fuera del contenedor, y el
# puerto lo asigna la plataforma (Render, Railway y Fly inyectan $PORT).
CMD ["sh", "-c", "uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}"]
