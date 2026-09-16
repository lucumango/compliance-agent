"""Qué pedirle a una contraparte, y con qué régimen.

Determinista y sin modelo, como `rag/multas.py`. La entrada son hechos que el
analista ya conoce del tercero; la salida es el régimen que le corresponde, los
datos que hay que obtener y de dónde sale cada exigencia.

**La regla de este módulo: cada requisito lleva su artículo, o va marcado como
práctica.** La Resolución SBS 789-2018 dice qué información mínima obtener; el
resto —fotos de instalaciones, referencias bancarias, licencia municipal— es
buena práctica de debida diligencia y no lo exige ninguna norma cargada.
Mezclar las dos cosas es el error que le cuesta caro a un cliente: se le acaba
exigiendo como ley lo que era criterio de la firma.

**Vocabulario.** El manual interno habla de diligencia *básica, mejorada y
reforzada*. La norma nombra otros tres: **general, reforzado y simplificado**
(artículo 16). Aquí manda el de la norma, y la equivalencia se dice en voz
alta.

**El simplificado no se deduce.** El artículo 16.3 lo describe como una
reducción de requisitos, pero quién puede acogerse depende del Título II, que
va por tipo de sujeto obligado. Este módulo no lo asigna nunca: dice que
existe y que hay que mirarlo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

RES_SBS = "res_sbs_789_2018::ley"
DL_1372 = "dl_1372::ley"


@dataclass(frozen=True)
class Detonador:
    id: str
    etiqueta: str
    # "norma" = la norma obliga a escalar. "practica" = criterio de la firma.
    origen: str
    unidad: str = ""
    cita: str = ""
    nota: str = ""


# Los seis del artículo 16.2.2: la norma dice "se aplica obligatoriamente".
_LEGALES = (
    Detonador("no_residente", "Nacional o extranjero no residente", "norma",
              f"{RES_SBS}::art_16", "Resolución SBS 789-2018, art. 16.2.2 (1)"),
    Detonador("pj_no_domiciliada", "Persona jurídica no domiciliada", "norma",
              f"{RES_SBS}::art_16", "Resolución SBS 789-2018, art. 16.2.2 (2)"),
    Detonador("fideicomiso", "Fideicomiso", "norma",
              f"{RES_SBS}::art_16", "Resolución SBS 789-2018, art. 16.2.2 (3)"),
    Detonador("pep", "PEP, pariente hasta 2.º grado, cónyuge o conviviente, "
              "o persona jurídica donde un PEP es beneficiario final", "norma",
              f"{RES_SBS}::art_16", "Resolución SBS 789-2018, art. 16.2.2 (4)",
              "También si se convierte en PEP después de iniciada la relación."),
    Detonador("investigado_lavado", "Se sabe que está siendo investigado por "
              "lavado de activos, delito precedente o financiamiento del "
              "terrorismo", "norma",
              f"{RES_SBS}::art_16", "Resolución SBS 789-2018, art. 16.2.2 (5)"),
    Detonador("vinculado_investigado", "Vinculado a persona investigada o "
              "procesada por esos delitos", "norma",
              f"{RES_SBS}::art_16", "Resolución SBS 789-2018, art. 16.2.2 (6)"),
)

# Los del manual de la firma. Escalan por criterio propio, no por mandato. Se
# devuelven marcados para que nadie los cite como si fueran ley.
_PRACTICA = (
    Detonador("pais_riesgo", "Jurisdicción con controles débiles o secreto "
              "societario", "practica"),
    Detonador("contacto_gobierno", "El tercero interactúa con funcionarios en "
              "nombre del cliente", "practica",
              nota="Es el detonador que más importa para riesgo de soborno."),
    Detonador("monto", "Exposición económica por encima del umbral definido",
              "practica"),
    Detonador("ubo_opaco", "No se llega a persona natural, o la cadena pasa "
              "por vehículos sin actividad", "practica",
              nota="Contrastar el organigrama del tercero con la declaración "
                   "de beneficiario final presentada ante SUNAT."),
)

DETONADORES: dict[str, Detonador] = {d.id: d for d in _LEGALES + _PRACTICA}

TIPOS = ("persona_natural", "persona_juridica", "proveedor")


@dataclass(frozen=True)
class Requisito:
    texto: str
    # "norma" o "practica". Lo mismo que en Detonador y por el mismo motivo.
    origen: str
    unidad: str = ""
    cita: str = ""


# Artículo 16.1.1: información mínima de una persona natural.
_PN = (
    ("Nombres y apellidos", "art_16", "art. 16.1.1 (1)"),
    ("Tipo y número de documento de identidad", "art_16", "art. 16.1.1 (2)"),
    ("Nacionalidad, si es extranjero", "art_16", "art. 16.1.1 (3)"),
    ("Domicilio", "art_16", "art. 16.1.1 (4)"),
    ("Ocupación", "art_16", "art. 16.1.1 (5)"),
    ("Teléfono y correo electrónico, de ser el caso", "art_16", "art. 16.1.1 (6)"),
    ("Propósito de la relación, si no se desprende del objeto del contrato",
     "art_16", "art. 16.1.1 (7)"),
    ("Declaración de si es o ha sido PEP, con cargo e institución; y de si es "
     "pariente, cónyuge o conviviente de PEP", "art_16", "art. 16.1.1 (8)"),
    ("Identidad del beneficiario de la operación", "art_16", "art. 16.1.1 (9)"),
)

# Artículo 16.1.2: información mínima de una persona jurídica o ente jurídico.
_PJ = (
    ("Denominación o razón social", "art_16", "art. 16.1.2 (1)"),
    ("RUC, o registro equivalente si no es domiciliada", "art_16", "art. 16.1.2 (2)"),
    ("Objeto social, actividad económica principal o finalidad de constitución",
     "art_16", "art. 16.1.2 (3)"),
    ("Identificación de los beneficiarios finales conforme al artículo 4 del "
     "DL 1372", "art_16", "art. 16.1.2 (4)"),
    ("Propósito de la relación, si no se desprende del objeto del contrato",
     "art_16", "art. 16.1.2 (5)"),
    ("Identificación del representante, con los datos del poder: instrumento "
     "público notarial y partida registral de SUNARP", "art_16", "art. 16.1.2 (6)"),
    ("Dirección y teléfono de la oficina o local principal donde opera",
     "art_16", "art. 16.1.2 (7)"),
    ("Identidad del beneficiario de la operación y origen de los fondos",
     "art_16", "art. 16.1.2 (8)"),
)

# Artículo 18: conocimiento de proveedores. Es su propio artículo y no un caso
# del 16, así que va aparte.
_PROV = (
    ("Nombres y apellidos, o denominación o razón social", "art_18", "art. 18.1 (a)"),
    ("RUC, o registro equivalente si no es domiciliado", "art_18", "art. 18.1 (b)"),
    ("Tipo y número de documento de identidad, y nacionalidad si es extranjero",
     "art_18", "art. 18.1 (c)"),
    ("Domicilio", "art_18", "art. 18.1 (d)"),
    ("Dirección de la oficina o local principal", "art_18", "art. 18.1 (e)"),
    ("Años de experiencia en el mercado", "art_18", "art. 18.1 (f)"),
    ("Rubros en los que brinda sus productos o servicios", "art_18", "art. 18.1 (g)"),
    ("Identificación del beneficiario final conforme al artículo 4 del DL 1372",
     "art_18", "art. 18.1 (h)"),
    ("Nombres y apellidos del representante legal, con los datos exigidos a una "
     "persona natural", "art_18", "art. 18.1 (i)"),
)

# Artículo 16.2.3: medidas que se añaden en el régimen reforzado.
_REFORZADO = (
    ("Tratándose de PEP: nombres de parientes hasta segundo grado de "
     "consanguinidad y afinidad, cónyuge o conviviente, y las personas o entes "
     "jurídicos donde sea beneficiario final", "art_16", "art. 16.2.3 (1)"),
    ("Aumentar la frecuencia de revisión de la actividad transaccional",
     "art_16", "art. 16.2.3 (2)"),
    ("Indagaciones adicionales: principales clientes y proveedores, fuentes "
     "públicas o abiertas, visita al domicilio", "art_16", "art. 16.2.3 (3)"),
    ("La aceptación o el mantenimiento de la relación la decide el nivel "
     "gerencial más alto, o el comité en quien delegue", "art_16", "art. 16.2.3 (4)"),
)

# Lo que pide el manual de la firma y no exige ninguna norma cargada. Va
# marcado, siempre, y nunca con una cita.
_PRACTICA_DOCS = (
    "Ficha RUC de SUNAT: estado del contribuyente y condición del domicilio. "
    "Es gratuita, pública e instantánea; se consulta antes de pedirle nada al "
    "tercero",
    "Partida registral en SUNARP y vigencia de poderes con antigüedad no mayor "
    "a 30 días",
    "Estados financieros de dos o tres ejercicios, auditados si los hay",
    "Reporte de deuda coactiva y situación ante SUNAT",
    "Evidencia de operación real: licencia de funcionamiento, contrato de "
    "arrendamiento, fotos de instalaciones, planilla",
    "Cotejo contra listas restrictivas: OFAC, ONU, UE y Reino Unido (hay un "
    "cotejo automático en DIEGO), más el RNP y el RNSSC, que no lo tienen",
    "Certificación anticorrupción y declaración de conflicto de interés "
    "firmadas por el tercero",
)


@dataclass
class Evaluacion:
    tipo: str
    regimen: str
    porque: list[str] = field(default_factory=list)
    requisitos: list[Requisito] = field(default_factory=list)
    practica: list[str] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)

    def como_dict(self) -> dict:
        return {
            "tipo": self.tipo,
            "regimen": self.regimen,
            "porque": self.porque,
            "requisitos": [r.__dict__ for r in self.requisitos],
            "practica": self.practica,
            "avisos": self.avisos,
        }


def _req(filas, origen="norma") -> list[Requisito]:
    return [
        Requisito(
            texto=texto,
            origen=origen,
            unidad=f"{RES_SBS}::{art}",
            cita=f"Resolución SBS 789-2018, {cita}",
        )
        for texto, art, cita in filas
    ]


def evaluar(tipo: str, detonadores: list[str] | None = None) -> Evaluacion:
    """El régimen y los requisitos, a partir de hechos ya conocidos.

    No decide si el tercero es aceptable. Dice qué hay que obtener y por qué.
    """
    if tipo not in TIPOS:
        raise KeyError(f"Tipo desconocido: {tipo}. Usa uno de {list(TIPOS)}.")

    marcados = [DETONADORES[d] for d in (detonadores or []) if d in DETONADORES]
    legales = [d for d in marcados if d.origen == "norma"]
    practicos = [d for d in marcados if d.origen == "practica"]

    base = {"persona_natural": _PN, "persona_juridica": _PJ, "proveedor": _PROV}[tipo]
    ev = Evaluacion(tipo=tipo, regimen="general", requisitos=_req(base))

    if legales:
        ev.regimen = "reforzado"
        ev.porque = [f"{d.etiqueta} — {d.cita}" for d in legales]
        ev.requisitos += _req(_REFORZADO)
    elif practicos:
        # No escala por norma. Escala porque la firma lo decidió, y hay que
        # poder distinguir las dos cosas seis meses después.
        ev.porque = [
            f"{d.etiqueta} — criterio interno, no lo exige ninguna norma cargada"
            for d in practicos
        ]
        ev.avisos.append(
            "Ninguno de los detonadores marcados obliga a escalar según la "
            "Resolución SBS 789-2018. El régimen legal sigue siendo el general; "
            "si se aplica un tratamiento más exigente, es criterio de la firma "
            "y conviene dejarlo escrito como tal."
        )

    ev.practica = list(_PRACTICA_DOCS)
    for d in marcados:
        if d.nota:
            ev.avisos.append(f"{d.etiqueta}: {d.nota}")

    ev.avisos.append(
        "El beneficiario final se identifica conforme al artículo 4 del "
        "Decreto Legislativo 1372, y se aplica cualquiera que sea el régimen "
        "(Resolución SBS 789-2018, art. 14.2)."
    )
    ev.avisos.append(
        "Existe un régimen simplificado (art. 16.3), pero quién puede acogerse "
        "depende del Título II de la norma, que va por tipo de sujeto obligado. "
        "Esto no lo determina: hay que mirarlo."
    )
    if tipo == "proveedor":
        ev.avisos.append(
            "El artículo 18 se aplica a proveedores de bienes o servicios "
            "relacionados directamente con la actividad supervisada por la "
            "UIF-Perú, no a cualquier compra."
        )
    return ev


def unidades_citadas() -> set[str]:
    """Todas las unidades del corpus que este módulo cita.

    La usa `agentes.evaluar` para comprobar que ninguna cita apunte a un
    artículo que ya no está en el índice. Un cuestionario que cita una unidad
    inexistente es exactamente el fallo que este proyecto no se permite.
    """
    citadas = {d.unidad for d in DETONADORES.values() if d.unidad}
    for filas in (_PN, _PJ, _PROV, _REFORZADO):
        citadas |= {f"{RES_SBS}::{art}" for _, art, _ in filas}
    return citadas
