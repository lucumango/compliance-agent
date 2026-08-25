"""PDF o DOCX a bloques de texto con su ubicación.

La ubicación importa tanto como el texto: una cita a "tu política de compras"
sin número de página no es verificable, y todo el producto se sostiene en que
cada afirmación se pueda ir a comprobar.

El PDF conserva la página real. El DOCX no tiene páginas —la paginación la
decide el programa que lo abre, no el archivo—, así que sus bloques van sin
página y se citan por su orden dentro del documento.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

TIPOS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

EXTENSIONES = {".pdf": "pdf", ".docx": "docx"}

# 20 MB. Por encima de esto la extracción tarda más que el tiempo de espera de
# la petición y hay que pasar a un trabajo en segundo plano.
MAX_BYTES = 20 * 1024 * 1024


class ErrorExtraccion(RuntimeError):
    """El archivo no se pudo leer, o no tiene texto que leer."""


@dataclass
class Bloque:
    texto: str
    pagina: int | None


def tipo_de(nombre: str, content_type: str | None) -> str:
    """Deduce el tipo por el content-type, y si no cuadra, por la extensión.

    El navegador no siempre manda el content-type correcto —Windows sin Office
    instalado manda application/octet-stream para un .docx— así que la
    extensión es el respaldo, no al revés.
    """
    if content_type and content_type.split(";")[0].strip() in TIPOS:
        return TIPOS[content_type.split(";")[0].strip()]
    for ext, tipo in EXTENSIONES.items():
        if nombre.lower().endswith(ext):
            return tipo
    raise ErrorExtraccion("Solo se admiten archivos PDF y DOCX.")


def _limpiar(texto: str) -> str:
    # Los PDF traen guiones de corte de línea que parten palabras a la mitad;
    # dejarlos rompe la palabra en el embedding y en la cita.
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    texto = texto.replace("\r\n", "\n").replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


def _de_pdf(datos: bytes) -> list[Bloque]:
    try:
        import pymupdf
    except ImportError as e:  # pragma: no cover - depende del despliegue
        raise ErrorExtraccion(
            "El servidor no tiene PyMuPDF instalado y no puede leer PDF."
        ) from e

    bloques: list[Bloque] = []
    try:
        documento = pymupdf.open(stream=datos, filetype="pdf")
    except Exception as e:
        # PyMuPDF lanza mensajes suyos ("Failed to open stream") que no dicen
        # nada a quien acaba de arrastrar un archivo a la ventana.
        raise ErrorExtraccion(
            "El archivo no es un PDF legible o está dañado."
        ) from e

    with documento as doc:
        if doc.is_encrypted and not doc.authenticate(""):
            raise ErrorExtraccion("El PDF está protegido con contraseña.")
        for numero, pagina in enumerate(doc, 1):
            texto = _limpiar(pagina.get_text("text"))
            if texto:
                bloques.append(Bloque(texto=texto, pagina=numero))
    return bloques


def _de_docx(datos: bytes) -> list[Bloque]:
    try:
        import docx
    except ImportError as e:  # pragma: no cover - depende del despliegue
        raise ErrorExtraccion(
            "El servidor no tiene python-docx instalado y no puede leer DOCX."
        ) from e

    try:
        documento = docx.Document(io.BytesIO(datos))
    except Exception as e:
        # Un .doc antiguo renombrado a .docx entra por aquí, y el error de
        # python-docx ("File is not a zip file") no ayuda a nadie.
        raise ErrorExtraccion(
            "El archivo no es un DOCX legible. Si es un .doc antiguo, "
            "guárdalo como .docx o como PDF."
        ) from e

    partes: list[str] = [p.text for p in documento.paragraphs if p.text.strip()]

    # Las tablas de un DOCX suelen llevar lo que más se consulta —umbrales,
    # matrices de autorización— y no aparecen entre los párrafos.
    for tabla in documento.tables:
        for fila in tabla.rows:
            celdas = [c.text.strip() for c in fila.cells if c.text.strip()]
            if celdas:
                partes.append(" | ".join(celdas))

    texto = _limpiar("\n\n".join(partes))
    return [Bloque(texto=texto, pagina=None)] if texto else []


def extraer(datos: bytes, tipo: str) -> list[Bloque]:
    if len(datos) > MAX_BYTES:
        raise ErrorExtraccion(
            f"El archivo pesa más de {MAX_BYTES // (1024 * 1024)} MB."
        )
    if not datos:
        raise ErrorExtraccion("El archivo está vacío.")

    bloques = _de_pdf(datos) if tipo == "pdf" else _de_docx(datos)
    if not bloques:
        raise ErrorExtraccion(
            "No se extrajo texto. Si es un escaneo, hay que pasarlo por OCR "
            "antes de subirlo: este servidor no lo hace."
        )
    return bloques
