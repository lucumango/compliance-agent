"""Parse raw extracted text of a Peruvian norma into a hierarchical structure:

Ley -> Título -> Capítulo/Sección -> Artículo

Designed for the "Normas Legales actualizadas" (Editora Perú) consolidated
format and for raw "El Peruano" gazette scans. Tolerant of common OCR
mistakes (e.g. "°" read as "*", roman numeral "I" read as "|" or "l").
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- text cleanup ------------------------------------------------------

_HYPHEN_BREAK_RE = re.compile(r"(\w)-\n(\w)")
_MULTI_SPACE_RE = re.compile(r"[ \t]+")
_MULTI_NEWLINE_RE = re.compile(r"\n{3,}")
_FORM_FEED_RE = re.compile(r"\f")


# Running heads and footers repeat on every page and, because a page break can
# fall mid-article, they end up embedded in article bodies. They must go before
# parsing, not after, or they also corrupt the marker positions.
_FURNITURE_LINE_RE = re.compile(
    r"^\s*(?:"
    r"NORMAS LEGALES(?:\s+actualizadas|\s+ACTUALIZADAS)?"
    r"|Inicio"
    r"|Tabla de Contenido"
    r"|.*El Peruano\s*/.*"
    r"|.*/\s*.*El Peruano.*"
    # Cabecera y pie de las descargas de SPIJ, que se repiten en cada página y
    # se cuelan a mitad de un artículo cuando este cruza el salto de página.
    r"|Sistema Peruano de Informaci[óo]n Jur[íi]dica.*"
    r"|Ministerio de Justicia\s*"
    r"|Actualizado al:.*"
    # "El Peruano" a solas. En el DS 016-2024-JUS la cabecera no cabe en una
    # línea y sale repartida en tres —fecha, "El Peruano", barra— así que los
    # patrones de arriba, que la esperan entera, no la reconocían.
    r"|El Peruano"
    r")\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_BARE_PAGE_NUM_RE = re.compile(r"^\s*\d{1,3}\s*$")


# Vecinos de la cabecera cuando la maqueta la reparte en varias líneas: la
# fecha con día de la semana encima, y la barra separadora sola debajo. Ni una
# ni otra se borran por su cuenta —una fecha suelta puede ser texto legítimo—,
# solo cuando acompañan a una línea de cabecera.
_FECHA_DIARIO_RE = re.compile(
    r"^\s*(?:Lunes|Martes|Mi[ée]rcoles|Jueves|Viernes|S[áa]bado|Domingo)\s+\d{1,2}\s+de\s+"
    r"\w+\s+de\s+\d{4}\s*$",
    re.IGNORECASE,
)
_BARRA_SOLA_RE = re.compile(r"^\s*/\s*$")


def strip_page_furniture(text: str) -> str:
    lines = text.split("\n")
    keep: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if _FURNITURE_LINE_RE.match(line):
            # El número de página, o la fecha del diario, van en la línea de
            # encima; se quitan solo en ese contexto para que un ítem numerado
            # o una fecha del articulado sobrevivan.
            while keep and (
                _BARE_PAGE_NUM_RE.match(keep[-1]) or _FECHA_DIARIO_RE.match(keep[-1])
            ):
                keep.pop()
            # Y la barra separadora, en la de abajo.
            j = i + 1
            while j < len(lines) and (
                not lines[j].strip() or _BARRA_SOLA_RE.match(lines[j])
            ):
                if _BARRA_SOLA_RE.match(lines[j]):
                    i = j
                j += 1
            i += 1
            continue
        if _BARE_PAGE_NUM_RE.match(line):
            nxt = next((ln for ln in lines[i + 1 :] if ln.strip()), "")
            if _FURNITURE_LINE_RE.match(nxt):
                i += 1
                continue
        keep.append(line)
        i += 1
    return "\n".join(keep)


# Espacios que no son el espacio de siempre: el duro (\xa0), el fino y el de
# cifra. La exportación a PDF del SPIJ los usa como sangría —"\xa0 \xa0 \xa0
# Artículo 1."— y ahí dejan de ser presentación para convertirse en un
# problema: `str.strip(" ")` no los quita, así que la comprobación de
# principio de línea de `_find_markers` veía prefijo no vacío y descartaba
# TODOS los artículos del documento. Se normalizan antes de nada.
_ESPACIOS_RAROS_RE = re.compile(r"[\u00a0\u2007\u202f\u2009\u2002-\u2006]")

# Ligaduras tipográficas. El Peruano compone con ellas y la extracción las
# devuelve tal cual, a veces con un espacio detrás que parte la palabra:
# "Notiﬁ cación", "beneﬁ ciario ﬁ nal". Así escritas no coinciden con la
# palabra que alguien teclea en una consulta, y el embedding las trata como
# otra cosa. El espacio se absorbe solo cuando detrás sigue la palabra.
_LIGADURAS = {
    "\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl",
    "\ufb03": "ffi", "\ufb04": "ffl", "\ufb05": "st", "\ufb06": "st",
}
_LIGADURA_RE = re.compile("([" + "".join(_LIGADURAS) + r"])(\s?)(?=\w)")


def _normalizar_ligaduras(texto: str) -> str:
    return _LIGADURA_RE.sub(lambda m: _LIGADURAS[m.group(1)], texto)


def clean_text(text: str) -> str:
    text = _normalizar_ligaduras(text)
    text = _ESPACIOS_RAROS_RE.sub(" ", text)
    text = _FORM_FEED_RE.sub("\n", text)
    text = _HYPHEN_BREAK_RE.sub(r"\1\2", text)  # rejoin hyphenated line breaks
    text = _MULTI_SPACE_RE.sub(" ", text)
    text = strip_page_furniture(text)
    text = _MULTI_NEWLINE_RE.sub("\n\n", text)
    return text.strip()


_ROMAN_OCR_CHARS = set("IVXLCDMl|")


def normalize_roman_ocr(token: str) -> str:
    """Fix common OCR confusions in roman numerals: '|' and 'l' -> 'I'."""
    if token and set(token) <= _ROMAN_OCR_CHARS:
        return token.replace("|", "I").replace("l", "I").upper()
    return token


# --- hierarchy markers ---------------------------------------------------

_TITULO_RE = re.compile(
    r"^\s*T[ÍI]TULO\s+(PRELIMINAR|[IVXLCDM|l]+)\b[ \t]*(.*)$", re.MULTILINE
)
_CAPITULO_RE = re.compile(r"^\s*CAP[ÍI]TULO\s+([IVXLCDM|l]+)\b[ \t]*(.*)$", re.MULTILINE)
_SECCION_RE = re.compile(r"^\s*SECCI[ÓO]N\s+([IVXLCDM|l]+)\b[ \t]*(.*)$", re.MULTILINE)

# "Artículo 37." / "Artículo 38.-" / "Artículo 13-A." / OCR: "Articulo 1." / "Artículo 2*"
# Note: no leading \s* here on purpose. It must not swallow the preceding
# newline, otherwise the line-start check in _find_markers can't tell a real
# header from a cross-reference like "...visto en el artículo 24".
# El sufijo de artículo insertado ("13-A", "3-B") va DENTRO del grupo: si se
# deja fuera, el guion lo consume el separador y "Artículo 3-B" se registra
# como un segundo "Artículo 3". En El Peruano eso solo producía una unidad
# mal numerada; en SPIJ, donde las repeticiones son versiones sucesivas del
# mismo artículo, hacía que un artículo insertado se confundiera con la
# versión vigente del anterior.
_ARTICULO_RE = re.compile(
    r'["“]?Art[íi]culo\s+(\d+(?:\s*[-–]\s*[A-Za-z])?)\s*[°ºª\*]?\s*[.\-–:]?\s*',
)

_MODIFICADO_RE = re.compile(
    r"\(?\*\)?\s*Art[íi]culo\s+modificado\s+por[^.]*\.", re.IGNORECASE
)
_DEROGADO_RE = re.compile(r"\bderogad[oa]\b", re.IGNORECASE)

# "DISPOSICIONES COMPLEMENTARIAS FINALES" and friends. The ley typesets these
# in caps and the reglamento in title case, so matching is case-insensitive;
# what keeps prose out ("modificado por la Tercera Disposición Complementaria
# Modificatoria del Decreto Legislativo N° 1353") is the full-line anchor plus
# the lookahead in _block_precedes_ordinal. Excludes "DISPOSICIONES
# GENERALES", an ordinary Título heading.
# The trailing comma is real in some titles ("DISPOSICIONES COMPLEMENTARIAS,
# TRANSITORIAS Y FINALES"), where the rest wraps to the following line.
_DISPOSICIONES_RE = re.compile(
    r"^[ \t]*DISPOSIC(?:IONES|I[ÓO]N)\s+(?:COMPLEMENTARIA(?:S)?|TRANSITORIA(?:S)?"
    r"|FINAL(?:ES)?|MODIFICATORIA(?:S)?|DEROGATORIA(?:S)?)[ \t]*"
    r"(FINALES|TRANSITORIAS|MODIFICATORIAS|DEROGATORIAS)?[ \t]*[,;.]?[ \t]*$",
    re.MULTILINE | re.IGNORECASE,
)
_BLOCK_LOOKAHEAD_LINES = 5

# Individual disposiciones are labelled with ordinal words, not numbers.
# "Sétima" (no "p") is the spelling Peruvian legislative drafting uses, and
# compound ordinals ("Décimo Primera") appear in the longer laws. The trailing
# separator is required: it distinguishes the heading "Primera. Reglamento de
# la Ley" from a run of ordinals in prose ("las primera, segunda, tercera ...
# disposiciones complementarias finales rigen a partir de ...").
_ORDINAL_SIMPLE = (
    r"PRIMERA|SEGUNDA|TERCERA|CUARTA|QUINTA|SEXTA|S[ÉE]PTIMA|S[ÉE]TIMA"
    r"|OCTAVA|NOVENA|UND[ÉE]CIMA|DUOD[ÉE]CIMA|[ÚU]NICA"
)
# The leading quote marks text substituted by a later norma, exactly as it
# does for articles ("“Cuarta.- Las auditorías ..."), so it must be optional
# here too or every amended disposición is missed.
# El espacio va ANTES de la comilla, no solo después: en el SPIJ la versión que
# sustituye a una disposición se abre así —' “ PRIMERA. Vigencia'—, con sangría
# delante del entrecomillado. Con la comilla obligada al principio de línea, esa
# versión no se reconocía como disposición, y el corpus se quedaba con la
# redacción derogada más la nota al pie pegada detrás.
_DISPOSICION_ITEM_RE = re.compile(
    rf"^[ \t]*[\"“]?[ \t]*((?:D[ÉE]CIM[OA]|VIG[ÉE]SIM[OA])\s+(?:{_ORDINAL_SIMPLE})"
    rf"|D[ÉE]CIMA|VIG[ÉE]SIMA|{_ORDINAL_SIMPLE})"
    r"\s*[.\-–]+\s*",
    re.MULTILINE | re.IGNORECASE,
)

# Promulgation boilerplate closing a ley: everything from here on is signatures.
_CIERRE_RE = re.compile(
    r"^\s*(?:POR TANTO:|Comun[íi]quese al se[ñn]or Presidente"
    r"|Mando se publique y cumpla|Dado en la Casa de Gobierno)",
    re.MULTILINE,
)


@dataclass
class Articulo:
    numero: str
    titulo: str
    texto: str
    tipo: str = "articulo"  # "articulo" | "disposicion"
    bloque: str | None = None  # for disposiciones, e.g. "COMPLEMENTARIAS FINALES"
    titulo_numero: str | None = None  # roman numeral of the Título, e.g. "III"
    titulo_capitulo: str | None = None  # heading text of the Título
    capitulo: str | None = None
    seccion: str | None = None
    modificado_por: str | None = None
    vigente: bool = True


@dataclass
class Marker:
    kind: str  # "titulo" | "capitulo" | "seccion" | "articulo"
    start: int  # where the header begins, i.e. the end of the previous body
    body_start: int  # where the content after the header begins
    label: str  # e.g. "I", "PRELIMINAR", "37"
    heading: str  # name of the titulo/capitulo/seccion


_UPPER_HEADING_RE = re.compile(r"^[^a-záéíóúñ]*[A-ZÁÉÍÓÚÑ][^a-záéíóúñ]*$")


def _heading_after(text: str, pos: int, inline: str) -> str:
    """Titles are typeset as `TÍTULO VII\\nINFRACCIONES Y SANCIONES\\nADMINISTRATIVAS`,
    so the name usually sits on the lines *after* the marker rather than on it.
    Collect the consecutive all-caps lines that follow."""
    if inline.strip():
        return inline.strip()

    lines: list[str] = []
    cursor = text.find("\n", pos)
    while cursor != -1 and len(lines) < 4:
        nxt = text.find("\n", cursor + 1)
        line = text[cursor + 1 : nxt if nxt != -1 else len(text)].strip()
        if not line or not _UPPER_HEADING_RE.match(line):
            break
        lines.append(line)
        cursor = nxt
    return " ".join(lines)


def _block_precedes_ordinal(text: str, pos: int) -> bool:
    """A real disposiciones block is immediately followed by its first
    ordinal item ("Primera.- ..."), possibly after a wrapped heading line.
    The same words appearing in a sentence are not."""
    cursor = pos
    for _ in range(_BLOCK_LOOKAHEAD_LINES):
        nxt = text.find("\n", cursor + 1)
        line = text[cursor + 1 : nxt if nxt != -1 else len(text)].strip()
        if line:
            m = _DISPOSICION_ITEM_RE.match(line)
            if m and m.group(1)[0].isupper():
                return True
            if not _UPPER_HEADING_RE.match(line):
                return False
        if nxt == -1:
            return False
        cursor = nxt
    return False


def _find_markers(text: str) -> list[Marker]:
    markers: list[Marker] = []

    for kind, regex in (
        ("titulo", _TITULO_RE),
        ("capitulo", _CAPITULO_RE),
        ("seccion", _SECCION_RE),
    ):
        for m in regex.finditer(text):
            markers.append(
                Marker(
                    kind,
                    m.start(),
                    m.end(),
                    normalize_roman_ocr(m.group(1)),
                    _heading_after(text, m.start(), m.group(2)),
                )
            )

    for m in _ARTICULO_RE.finditer(text):
        # avoid matching "Artículo" inside cross-references like "el artículo 24"
        # by requiring the match to start at a line boundary (after strip).
        line_start = text.rfind("\n", 0, m.start()) + 1
        prefix = text[line_start : m.start()]
        if prefix.strip(' "“”') != "":
            continue
        markers.append(Marker("articulo", line_start, m.end(), m.group(1), ""))

    for m in _DISPOSICIONES_RE.finditer(text):
        if not _block_precedes_ordinal(text, m.end()):
            continue
        # "DISPOSICIONES COMPLEMENTARIAS" often wraps, with "FINALES" alone on
        # the next line; pull the continuation in so the block is named fully.
        nombre = " ".join(
            filter(None, [m.group(0).strip(), _heading_after(text, m.start(), "")])
        )
        markers.append(Marker("disposiciones_bloque", m.start(), m.end(), "", nombre))
    for m in _DISPOSICION_ITEM_RE.finditer(text):
        # Matching is case-insensitive to absorb both "PRIMERA." and
        # "Primera.", but a lowercase ordinal is running prose, not a heading.
        if not m.group(1)[0].isupper():
            continue
        markers.append(
            Marker("disposicion", m.start(), m.end(), m.group(1).upper(), "")
        )
    for m in _CIERRE_RE.finditer(text):
        markers.append(Marker("cierre", m.start(), m.end(), "", ""))

    markers.sort(key=lambda x: x.start)
    return markers


_LEADING_INT_RE = re.compile(r"^\d+")
_MAX_ARTICLE_JUMP = 10

# In the scanned gazette text the ordinal marker of "Artículo 9º.-" is often
# recognised as a digit, yielding "Artículo 92.-". Left alone that both loses
# article 9 and invents a nonexistent article 92, so a trailing digit that
# could be a mangled ordinal is a candidate for stripping, but only when
# doing so is what makes the sequence line up.
_ORDINAL_OCR_DIGITS = ("2", "9", "0")


def _fits(n: int, max_seen: int) -> bool:
    return n > max_seen and n - max_seen <= _MAX_ARTICLE_JUMP


def _drop_spurious_matches(articulos: list[Articulo]) -> list[Articulo]:
    """Article numbers in a Peruvian norma always increase monotonically
    (with only small gaps, e.g. an inserted "13-A"). OCR'd text and
    line-wrapped cross-references (e.g. "...visto en el\nArtículo 24 de la
    ley...", or a quoted article of another code inside a disposición
    modificatoria) can trigger a false header match. Any match that breaks
    monotonicity is folded back into the previous article's text instead of
    being dropped, so no content is lost."""
    result: list[Articulo] = []
    max_seen = 0
    for art in articulos:
        m = _LEADING_INT_RE.match(art.numero)
        if m is None:
            result.append(art)
            continue

        n = int(m.group())
        if result and not _fits(n, max_seen):
            # Before treating it as spurious, test the mangled-ordinal reading.
            digits = m.group()
            if len(digits) > 1 and digits[-1] in _ORDINAL_OCR_DIGITS:
                stripped = int(digits[:-1])
                if _fits(stripped, max_seen):
                    art.numero = str(stripped) + art.numero[len(digits):]
                    max_seen = stripped
                    result.append(art)
                    continue
            prev = result[-1]
            prev.texto = f"{prev.texto}\n\nArtículo {art.numero}.- {art.texto}".strip()
            continue

        max_seen = max(max_seen, n)
        result.append(art)
    return result


def _ultima_version(articulos: list[Articulo]) -> list[Articulo]:
    """Se queda con la versión vigente de cada artículo repetido.

    Una descarga concordada de SPIJ no trae el articulado una vez: trae el
    texto original y, a continuación, cada versión que lo fue sustituyendo,
    todas con el mismo número y entrecomilladas. La vigente es la última.

    Sin esto, la monotonicidad trata las repeticiones como coincidencias
    falsas y las pliega dentro del primer artículo, con el resultado de que el
    corpus se queda con el texto ORIGINAL de un documento cuya portada dice
    'Actualizado al ...'. Es el peor fallo posible aquí: un texto derogado
    presentado como vigente, y sin ninguna señal de que lo sea.
    """
    result: list[Articulo] = []
    for art in articulos:
        if result and result[-1].numero == art.numero:
            result[-1] = art
        else:
            result.append(art)
    return result


def parse_articulos(raw_text: str, formato: str = "el_peruano") -> list[Articulo]:
    text = clean_text(raw_text)
    markers = _find_markers(text)

    articulos: list[Articulo] = []
    cur_titulo: str | None = None
    cur_titulo_heading: str | None = None
    cur_capitulo: str | None = None
    cur_seccion: str | None = None
    cur_bloque: str | None = None

    for i, marker in enumerate(markers):
        if marker.kind == "titulo":
            cur_titulo = marker.label
            cur_titulo_heading = marker.heading or None
            cur_capitulo = None
            continue
        if marker.kind == "capitulo":
            cur_capitulo = marker.label
            continue
        if marker.kind == "seccion":
            cur_seccion = marker.label
            cur_capitulo = None
            continue
        if marker.kind == "disposiciones_bloque":
            cur_bloque = marker.heading
            continue
        if marker.kind == "cierre":
            # Signatures and promulgation formulae carry no obligations; they
            # only exist here to bound the preceding unit's text.
            continue
        # Dentro de un bloque de disposiciones, las unidades se rotulan con
        # ordinales ("Primera", "Segunda"), nunca con números. Un "Artículo 18"
        # aquí es el articulado de OTRA norma citado por una disposición
        # modificatoria —el artículo 18 del Código Tributario dentro del
        # DL 1372, por ejemplo—, no articulado propio. La monotonicidad no lo
        # detecta porque 18 viene después de 10 y parece continuar la serie.
        if marker.kind == "articulo" and cur_bloque is not None:
            continue

        if marker.kind == "disposicion" and cur_bloque is None:
            # An ordinal word outside a disposiciones block is ordinary prose.
            continue

        # body runs from just after this header to just before the next
        # marker's header (not its body), so the next header's own text does
        # not leak into this unit.
        end = markers[i + 1].start if i + 1 < len(markers) else len(text)
        body = text[marker.body_start : end].strip()

        # strip trailing lone closing quote left over from the header match
        body = body.lstrip('"“” ').strip()

        mod_match = _MODIFICADO_RE.search(body)
        modificado_por = mod_match.group(0) if mod_match else None

        first_line = body.split("\n", 1)[0]
        titulo_unidad = first_line[:120].strip() if len(first_line) < 140 else ""

        articulos.append(
            Articulo(
                numero=marker.label,
                titulo=titulo_unidad,
                texto=body,
                tipo="disposicion" if marker.kind == "disposicion" else "articulo",
                bloque=cur_bloque if marker.kind == "disposicion" else None,
                titulo_numero=cur_titulo,
                titulo_capitulo=cur_titulo_heading,
                capitulo=cur_capitulo,
                seccion=cur_seccion,
                modificado_por=modificado_por,
                vigente=not bool(_DEROGADO_RE.search(modificado_por or "")),
            )
        )

    if formato == "spij":
        articulos = _ultima_version(articulos)
    return _drop_spurious_matches(articulos)


# --- multi-document splitting ---------------------------------------------
#
# The Editora Perú "Normas Legales actualizadas" PDFs (e.g. ley_29733.pdf,
# ley_29783.pdf) bundle three logically independent documents, each with its
# own article numbering starting back at 1:
#   1. La Ley
#   2. El Decreto Supremo que aprueba el reglamento (~4 short articles)
#   3. El Reglamento anexo al Decreto Supremo
#
# Single-law scans (ley_27693.pdf, ley_30424.pdf) have no such boundary and
# are returned as one "ley" document.

_DECRETO_SUPREMO_RE = re.compile(r"^DECRETO SUPREMO\b", re.MULTILINE)
_REGLAMENTO_HEADER_RE = re.compile(r"^REGLAMENTO DE LA (?:presente )?LEY\b", re.MULTILINE)
_PRESIDENTE_RE = re.compile(r"^EL PRESIDENTE DE LA REP[ÚU]BLICA\b", re.MULTILINE)

# El encabezado "REGLAMENTO DE LA LEY..." no basta para situar dónde empieza el
# reglamento, porque aparece hasta tres veces y solo una es la buena:
#
#   1. dentro del título del propio decreto ("DECRETO SUPREMO QUE APRUEBA EL
#      REGLAMENTO DE LA LEY Nº 29733"), partido en dos líneas por la maqueta;
#   2. como cabecera repetida en cada página de la sección del reglamento,
#      que puede caer a mitad de una frase;
#   3. como encabezado real, cuando el documento lo lleva.
#
# Tomar el primero dejaba el articulado del decreto y el del reglamento en un
# mismo documento. Como la numeración se reinicia en 1, la desambiguación por
# monotonicidad plegaba TODO el reglamento dentro del artículo 4 del decreto:
# el DS 016-2024-JUS entraba con 13 unidades en vez de 135.
#
# El límite fiable es la fórmula de cierre del decreto: después de la firma no
# queda nada del decreto, y lo siguiente que abre estructura es el reglamento.
_CIERRE_DECRETO_RE = re.compile(
    r"^[ \t]*(?:Dado en la Casa de Gobierno|Reg[íi]strese, com[uú]n[íi]quese)",
    re.MULTILINE,
)
_DECRETA_RE = re.compile(r"^[ \t]*(?:DECRETA|RESUELVE)\s*:", re.MULTILINE)
_APERTURA_REGLAMENTO_RE = re.compile(
    r"^[ \t]*(?:T[ÍI]TULO\b|CAP[ÍI]TULO\b|Art[íi]culo\s+(?:I\b|1\b))", re.MULTILINE
)


@dataclass
class Documento:
    tipo: str  # "ley" | "decreto_aprobatorio" | "reglamento"
    texto: str


def split_documents(text: str) -> list[Documento]:
    decreto_match = _DECRETO_SUPREMO_RE.search(text)
    if not decreto_match:
        return [Documento("ley", text)]

    decreto_pos = decreto_match.start()
    reglamento_matches = list(_REGLAMENTO_HEADER_RE.finditer(text))
    before = [m.start() for m in reglamento_matches if m.start() < decreto_pos]
    after = [m.start() for m in reglamento_matches if m.start() > decreto_pos]

    # The reglamento's cover heading sits right before "DECRETO SUPREMO";
    # the closest one before it marks where the Ley text ends.
    ley_end = max(before, default=decreto_pos)

    # Solo valen los encabezados posteriores a la parte dispositiva: los que
    # caen antes son el título del propio decreto.
    decreta = _DECRETA_RE.search(text, decreto_pos)
    if decreta:
        after = [pos for pos in after if pos > decreta.end()]
    reglamento_start = min(after, default=None)

    # Y si tras la firma del decreto empieza una estructura nueva, ese es el
    # límite bueno aunque haya un encabezado más adelante: el de más adelante
    # suele ser la cabecera de página, que cae a mitad de frase.
    cierre = _CIERRE_DECRETO_RE.search(text, decreta.end() if decreta else decreto_pos)
    if cierre:
        apertura = _APERTURA_REGLAMENTO_RE.search(text, cierre.end())
        if apertura and (reglamento_start is None or apertura.start() < reglamento_start):
            reglamento_start = apertura.start()

    presidente_match = _PRESIDENTE_RE.search(text)
    ley_start = presidente_match.start() if presidente_match else 0

    docs = [Documento("ley", text[ley_start:ley_end])]
    if reglamento_start is not None:
        docs.append(Documento("decreto_aprobatorio", text[ley_end:reglamento_start]))
        docs.append(Documento("reglamento", text[reglamento_start:]))
    else:
        docs.append(Documento("decreto_aprobatorio", text[ley_end:]))
    return docs


def parse_norma(raw_text: str, formato: str = "el_peruano") -> dict[str, list[Articulo]]:
    """Split a raw PDF text into its constituent documents and parse each
    into a flat list of Articulo. Keys are "ley", "decreto_aprobatorio",
    "reglamento" (the latter two only present when found)."""
    text = clean_text(raw_text)
    return {
        doc.tipo: parse_articulos(doc.texto, formato)
        for doc in split_documents(text)
    }
