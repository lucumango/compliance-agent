"""Registry of the corpus documents.

Deliberately conservative: only fields that can be read off the source PDF are
filled in. `fecha_publicacion` and `url_fuente` stay None until verified
against SPIJ / El Peruano, and `metadata_verificada` records that state. In a
compliance product an invented date is worse than a missing one, so nothing
here is asserted from memory.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Tipos de relación entre normas. Deliberadamente pocos: cada uno tiene que
# significar algo distinto a la hora de responder "¿puedo fiarme de esta cita?".
#
# Las formas pasivas (`modificada_por`, `reglamentada_por`) no sobran: la norma
# que modifica suele ser justo la que NO está cargada, así que la relación solo
# se puede anotar desde el lado que sí tenemos.
RELACIONES_VALIDAS = {
    "modifica_a",
    "modificada_por",
    "reglamenta_a",
    "reglamentada_por",
    "deroga_a",
    "derogada_por",
    "sustituye_a",
    "complementa_a",
}


@dataclass
class Relacion:
    """Una arista del grafo de trazabilidad.

    `en_corpus=False` es la parte útil: deja constancia de lo que sabemos que
    falta. Que la Ley 30835 modifica a la 30424 se sabe, pero el texto no está
    cargado; anotarlo como arista convierte ese hueco en algo consultable en
    vez de una frase enterrada en una nota.
    """

    tipo: str
    destino: str  # norma_id si está en el corpus; si no, un identificador legible
    nota: str = ""
    en_corpus: bool = False

    def __post_init__(self) -> None:
        if self.tipo not in RELACIONES_VALIDAS:
            raise ValueError(
                f"Relación '{self.tipo}' no válida. "
                f"Disponibles: {', '.join(sorted(RELACIONES_VALIDAS))}"
            )


@dataclass
class NormaMeta:
    norma_id: str
    archivo: str
    tipo: str  # "ley" | "norma_tecnica"
    numero: str
    nombre: str
    materia: str
    entidad_reguladora: list[str]
    parser: str  # "ley" | "iso"
    # Maquetación del PDF de origen. Cambia cómo se interpreta el articulado:
    #   "el_peruano"  publicación en el diario oficial, cada artículo una vez
    #   "spij"        descarga concordada del SPIJ, que trae el texto original
    #                 y detrás cada versión que lo sustituyó. Se toma la última.
    formato: str = "el_peruano"
    fecha_publicacion: str | None = None
    url_fuente: str | None = None
    metadata_verificada: bool = False
    notas: str = ""

    # Por qué esta norma está en el corpus. Una o dos frases, en términos de a
    # quién obliga y a qué. Se deduce hoy de `materia`, que no es lo mismo: con
    # cuarenta normas cargadas, "por qué entró esta" no sobrevive en la cabeza
    # de nadie. Obligatorio para toda norma nueva (ver docs/INGESTA.md).
    por_que_relevante: str = ""

    # Estado del texto como dato, no como prosa. `notas` lo sigue contando en
    # lenguaje natural para el usuario final; esto es para poder filtrar.
    #   "consolidado" texto actualizado a la fecha de `consolidado_a`
    #   "original"    publicación original, sin modificatorias posteriores
    #   "parcial"     solo una parte del documento
    estado_texto: str = "consolidado"
    consolidado_a: str | None = None

    # Cómo se nombra la norma al citarla. Vacío = "Ley <numero>", que vale para
    # una ley y para nada más: un decreto legislativo citado como "Ley 1372" o
    # un reglamento como "Reglamento de la Ley 003-2019-EF" son citas que no
    # existen, y una cita que no se puede buscar no sirve de nada.
    cita_como: str = ""

    # Documentos del PDF que NO entran al corpus, por su clave: "ley",
    # "decreto_aprobatorio", "reglamento".
    #
    # Existe por un caso concreto: el PDF de la Ley 29733 trae anexo el
    # reglamento de 2013, derogado por el DS 016-2024-JUS. Cargar los dos deja
    # al índice con dos reglamentos de la misma ley compitiendo por la misma
    # consulta, y el que gane depende del embedding, no de cuál rige. Excluir
    # es preferible a marcar como no vigente: el aviso llega DESPUÉS de que la
    # recuperación ya haya gastado una plaza en texto derogado.
    documentos_excluidos: list[str] = field(default_factory=list)

    relaciones: list[Relacion] = field(default_factory=list)


REGISTRY: list[NormaMeta] = [
    NormaMeta(
        norma_id="ley_29733",
        archivo="ley_29733.pdf",
        tipo="ley",
        numero="29733",
        nombre="Ley de Protección de Datos Personales",
        materia="proteccion_datos",
        entidad_reguladora=["ANPD", "MINJUSDH"],
        parser="ley",
        notas=(
            "Texto consolidado (Editora Perú). El PDF trae anexo el Reglamento "
            "de 2013, que NO se carga: fue derogado por el DS 016-2024-JUS, "
            "que sí está en el corpus como norma propia."
        ),
        por_que_relevante=(
            "Obliga a toda entidad que trate datos personales en el Perú: "
            "consentimiento, bancos de datos, derechos del titular y régimen "
            "sancionador. Es la base del cumplimiento en privacidad, y la "
            "única norma del corpus cuya escala de multas está cargada en la "
            "calculadora."
        ),
        estado_texto="consolidado",
        documentos_excluidos=["reglamento"],
        relaciones=[
            Relacion(
                tipo="reglamentada_por",
                destino="ds_016_2024_jus",
                nota="Reglamento vigente desde 2024.",
                en_corpus=True,
            ),
            Relacion(
                tipo="reglamentada_por",
                destino="DS 003-2013-JUS",
                nota=(
                    "Reglamento anterior, derogado. Viene en el mismo PDF y se "
                    "excluye a propósito para no competir con el vigente."
                ),
            ),
        ],
    ),
    NormaMeta(
        norma_id="ley_29783",
        archivo="ley_29783.pdf",
        tipo="ley",
        numero="29783",
        nombre="Ley de Seguridad y Salud en el Trabajo",
        materia="sst_laboral",
        entidad_reguladora=["SUNAFIL", "MTPE"],
        parser="ley",
        notas=(
            "Texto consolidado actualizado al 28/04/2022 según portada. "
            "Incluye el Reglamento aprobado por DS 005-2012-TR."
        ),
        por_que_relevante=(
            "Obliga a todo empleador: sistema de gestión de SST, comité de "
            "seguridad, notificación de accidentes y enfermedades "
            "ocupacionales. Es el corpus más extenso cargado (252 unidades) y "
            "el que responde la mayoría de consultas procedimentales."
        ),
        estado_texto="consolidado",
        consolidado_a="2022-04-28",  # leído de la portada
        relaciones=[
            Relacion(
                tipo="reglamentada_por",
                destino="DS 005-2012-TR",
                nota="Incluido en el mismo PDF como documento anexo.",
                en_corpus=True,
            ),
        ],
    ),
    NormaMeta(
        norma_id="ley_27693",
        archivo="ley_27693.pdf",
        tipo="ley",
        numero="27693",
        nombre="Ley que crea la Unidad de Inteligencia Financiera - Perú",
        materia="laft",
        entidad_reguladora=["SBS", "UIF-Perú"],
        parser="ley",
        formato="spij",
        fecha_publicacion="2002-04-12",  # leído de la portada del concordado
        notas=(
            "Texto concordado del SPIJ, actualizado al 01/10/2025 según "
            "portada. Sustituye al escaneo con OCR que se cargó primero. "
            "Cuando un artículo ha sido modificado, el corpus recoge la "
            "última versión, no la original de 2002."
        ),
        por_que_relevante=(
            "Crea la UIF y fija el deber de los sujetos obligados de comunicar "
            "operaciones sospechosas. Es la norma cabecera del régimen de "
            "LA/FT: casi todo lo demás del corpus en esta materia la "
            "reglamenta o la modifica."
        ),
        estado_texto="consolidado",
        consolidado_a="2025-10-01",
        relaciones=[
            # Estas tres están absorbidas en el texto concordado: su articulado
            # vive ya dentro de la Ley 27693 tal como se carga. Se registran
            # como aristas y no como texto propio porque cargarlas aparte
            # duplicaría los mismos artículos en dos redacciones distintas, y
            # la recuperación devolvería la vieja tan a menudo como la vigente.
            Relacion(
                tipo="modificada_por",
                destino="Ley 28009",
                nota="Absorbida en el texto concordado.",
            ),
            Relacion(
                tipo="modificada_por",
                destino="Ley 28306",
                nota="Absorbida en el texto concordado.",
            ),
            Relacion(
                tipo="modificada_por",
                destino="ley_29038",
                nota="Incorpora la UIF a la SBS. Absorbida en el concordado.",
                en_corpus=True,
            ),
            Relacion(
                tipo="reglamentada_por",
                destino="DS 020-2017-JUS",
                nota="Reglamento vigente. Aún no cargado.",
            ),
        ],
    ),
    NormaMeta(
        norma_id="ley_29038",
        archivo="ley_29038.pdf",
        tipo="ley",
        numero="29038",
        nombre=(
            "Ley que incorpora la Unidad de Inteligencia Financiera del Perú "
            "(UIF-Perú) a la Superintendencia de Banca, Seguros y AFP"
        ),
        materia="laft",
        entidad_reguladora=["SBS", "UIF-Perú"],
        parser="ley",
        por_que_relevante=(
            "Traslada la UIF a la SBS, que es lo que explica que hoy el "
            "supervisor en materia de LA/FT sea la Superintendencia y no un "
            "organismo aparte. Corta, pero determina a quién se reporta."
        ),
        estado_texto="consolidado",
        relaciones=[
            Relacion(
                tipo="modifica_a",
                destino="ley_27693",
                nota="Su contenido está absorbido en el concordado de la 27693.",
                en_corpus=True,
            ),
        ],
    ),
    NormaMeta(
        norma_id="dl_1106",
        cita_como="DL 1106",
        archivo="dl_1106.pdf",
        tipo="ley",
        numero="1106",
        nombre=(
            "Decreto Legislativo de lucha eficaz contra el lavado de activos y "
            "otros delitos relacionados a la minería ilegal y crimen organizado"
        ),
        materia="laft",
        entidad_reguladora=["Ministerio Público", "UIF-Perú"],
        parser="ley",
        por_que_relevante=(
            "Tipifica el lavado de activos y sus penas. La Ley 27693 dice a "
            "quién hay que reportar; esta dice qué conducta es delito, que es "
            "lo que un programa de prevención tiene que evitar."
        ),
        estado_texto="consolidado",
    ),
    NormaMeta(
        norma_id="dl_1372",
        cita_como="DL 1372",
        archivo="dl_1372.pdf",
        tipo="ley",
        numero="1372",
        nombre=(
            "Decreto Legislativo que regula la obligación de las personas "
            "jurídicas y entes jurídicos de informar la identificación de los "
            "beneficiarios finales"
        ),
        materia="laft",
        entidad_reguladora=["SUNAT", "UIF-Perú"],
        parser="ley",
        por_que_relevante=(
            "Obliga a identificar y declarar al beneficiario final. Es una "
            "obligación operativa concreta, con plazos y sanciones, que recae "
            "sobre cualquier persona jurídica: de las pocas del corpus que "
            "generan trabajo periódico y no solo deberes genéricos."
        ),
        estado_texto="consolidado",
    ),
    NormaMeta(
        norma_id="ley_30424",
        archivo="ley_30424.pdf",
        tipo="ley",
        numero="30424",
        nombre=(
            "Ley que regula la responsabilidad administrativa de las personas "
            "jurídicas en el proceso penal"
        ),
        materia="anticorrupcion",
        entidad_reguladora=["MINJUSDH", "Ministerio Público"],
        parser="ley",
        formato="spij",
        fecha_publicacion="2016-04-21",
        notas=(
            "Texto concordado del SPIJ, actualizado a diciembre de 2024. "
            "Sustituye al escaneo con OCR del texto original de 2016 que se "
            "cargó primero. Cuando un artículo o una disposición han sido "
            "modificados, el corpus recoge la última versión: el alcance "
            "vigente ya no es solo cohecho activo transnacional."
        ),
        por_que_relevante=(
            "Establece la responsabilidad administrativa de la persona "
            "jurídica y el modelo de prevención que la atenúa. Es la norma que "
            "justifica tener un programa de compliance, no solo políticas "
            "sueltas."
        ),
        estado_texto="consolidado",
        consolidado_a="2024-12-31",
        relaciones=[
            # Absorbidas en el texto concordado: su articulado vive ya dentro
            # del texto tal como se carga. Cargarlas aparte duplicaría los
            # mismos artículos en dos redacciones distintas.
            Relacion(
                tipo="modificada_por",
                destino="DL 1352",
                nota="Absorbido en el texto concordado.",
            ),
            Relacion(
                tipo="modificada_por",
                destino="Ley 30835",
                nota="Amplía el catálogo de delitos. Absorbida en el concordado.",
            ),
            Relacion(
                tipo="modificada_por",
                destino="Ley 31740",
                nota="Absorbida en el texto concordado.",
            ),
            Relacion(
                tipo="reglamentada_por",
                destino="DS 002-2019-JUS",
                nota=(
                    "Desarrolla el modelo de prevención, que es la parte "
                    "accionable de la ley. No cargado."
                ),
            ),
        ],
    ),
    NormaMeta(
        norma_id="ds_016_2024_jus",
        cita_como="DS 016-2024-JUS",
        archivo="ds_016_2024_jus.pdf",
        tipo="ley",
        numero="016-2024-JUS",
        nombre="Reglamento de la Ley de Protección de Datos Personales",
        materia="proteccion_datos",
        entidad_reguladora=["ANPD", "MINJUSDH"],
        parser="ley",
        notas=(
            "Publicación en El Peruano de noviembre de 2024. Deroga el "
            "Reglamento aprobado por DS 003-2013-JUS, que venía anexo al PDF "
            "de la Ley 29733 y por eso se excluye allí."
        ),
        por_que_relevante=(
            "Es el reglamento vigente de la norma más consultada del corpus. "
            "Desarrolla lo que la ley enuncia: plazos, formas del "
            "consentimiento, medidas de seguridad y procedimiento "
            "sancionador. Sin él, una consulta de privacidad se responde con "
            "la ley a secas, que casi nunca trae el detalle que se pregunta."
        ),
        estado_texto="consolidado",
        relaciones=[
            Relacion(
                tipo="reglamenta_a",
                destino="ley_29733",
                nota="Reglamento vigente.",
                en_corpus=True,
            ),
            Relacion(
                tipo="deroga_a",
                destino="DS 003-2013-JUS",
                nota="Reglamento anterior, excluido del corpus.",
            ),
        ],
    ),
    NormaMeta(
        norma_id="ds_003_2019_ef",
        cita_como="DS 003-2019-EF",
        archivo="ds_003_2019_ef.pdf",
        tipo="ley",
        numero="003-2019-EF",
        nombre="Reglamento del Decreto Legislativo 1372, beneficiario final",
        materia="laft",
        entidad_reguladora=["SUNAT", "MEF"],
        parser="ley",
        fecha_publicacion="2019-01-08",  # leído de la cabecera de El Peruano
        notas="Publicación en El Peruano del 08/01/2019.",
        por_que_relevante=(
            "Define los umbrales y la forma de la declaración de beneficiario "
            "final: qué porcentaje de participación obliga a declarar, quién "
            "declara y con qué formato. El DL 1372 fija el deber; esto es lo "
            "que se aplica en una debida diligencia real."
        ),
        estado_texto="consolidado",
        relaciones=[
            Relacion(
                tipo="reglamenta_a",
                destino="dl_1372",
                nota="Reglamento del deber de informar el beneficiario final.",
                en_corpus=True,
            ),
        ],
    ),
    NormaMeta(
        norma_id="res_sbs_789_2018",
        cita_como="Resolución SBS 789-2018",
        archivo="res_sbs_789_2018.pdf",
        tipo="ley",
        numero="789-2018",
        nombre=(
            "Norma para la prevención del lavado de activos y del "
            "financiamiento del terrorismo aplicable a los sujetos obligados "
            "bajo supervisión de la UIF-Perú"
        ),
        materia="laft",
        entidad_reguladora=["SBS", "UIF-Perú"],
        parser="ley",
        fecha_publicacion="2018-03-03",  # publicada 03/03/2018, emitida 28/02/2018
        notas=(
            "Versión descargada del portal de la SBS, marcada como vigente a "
            "abril de 2026. Existe una descarga anterior de octubre de 2025 "
            "cuyo texto difiere; se cargó la más reciente."
        ),
        por_que_relevante=(
            "Determina a quién aplica qué régimen de prevención de lavado: "
            "define los sujetos obligados bajo supervisión de la UIF y las "
            "obligaciones concretas de cada uno. Es la norma que decide si un "
            "tercero evaluado está o no dentro del sistema."
        ),
        estado_texto="consolidado",
        relaciones=[
            Relacion(
                tipo="reglamenta_a",
                destino="ley_27693",
                nota="Desarrolla el régimen de los sujetos obligados.",
                en_corpus=True,
            ),
        ],
    ),
    NormaMeta(
        norma_id="iso_37001",
        cita_como="ISO 37001:2016",
        archivo="iso_37001.pdf",
        tipo="norma_tecnica",
        numero="37001:2016",
        nombre="Sistemas de gestión antisoborno — Requisitos con orientación para su uso",
        materia="antisoborno",
        entidad_reguladora=[],
        parser="iso",
        fecha_publicacion="2016-10-15",  # leído de la portada
        notas=(
            "Traducción oficial al español. Documento con copyright ISO: uso "
            "interno del proyecto; no redistribuir el texto íntegro."
        ),
        por_que_relevante=(
            "No es derecho peruano: es el estándar contra el que se diseña y "
            "audita un sistema de gestión antisoborno. Aporta el 'cómo' "
            "(debida diligencia, controles, función de cumplimiento) allí "
            "donde la Ley 30424 solo fija el 'qué'."
        ),
        estado_texto="consolidado",
        # Deliberadamente sin relaciones. La conexión con la Ley 30424 es real
        # pero editorial, no normativa: ISO no modifica ni reglamenta una ley
        # peruana. Anotarla exige decidir con la fuente delante qué se está
        # afirmando, y este registro no afirma nada de memoria.
    ),
]
