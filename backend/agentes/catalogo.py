"""Los agentes que existen hoy.

CARLOS ya corría; se declara aquí para que no sea el caso especial de un
sistema donde todos los demás sí están declarados. DIEGO es el primero que
nace con alcance y casos desde el principio.

Los otros dos del plan —IVÁN, investigación; ELENA, línea ética— no están
porque su corpus no lo está. Un agente sin corpus responde de memoria, que es
justo lo que este sistema existe para no hacer.
"""

from __future__ import annotations

from .definicion import Agente, CasoAlcance, CasoRecuperacion

CARLOS = Agente(
    id="carlos",
    nombre="CARLOS",
    acronimo="Compliance Audit Regulatory Logic Operational System",
    area="Compliance",
    # Todo el corpus: es el agente general y el que responde cuando la consulta
    # cruza materias.
    materias=None,
    alcance=(
        "obligaciones normativas de una organización en el Perú: protección de "
        "datos, seguridad y salud en el trabajo, prevención del lavado de "
        "activos, responsabilidad administrativa de la persona jurídica y "
        "sistemas de gestión antisoborno."
    ),
    fuera_de_alcance=(
        "tipificar delitos, materia tributaria, societaria, ambiental y "
        "sectorial, y cualquier norma que no esté en las FUENTES."
    ),
    casos_recuperacion=(
        CasoRecuperacion(
            "¿Cuál es la multa máxima por una infracción muy grave en protección de datos?",
            "ley_29733::ley::art_39",
            3,
        ),
        CasoRecuperacion(
            "¿Cada cuánto deben hacerse las auditorías del sistema de gestión de SST?",
            "ley_29783::ley::art_43",
            3,
        ),
    ),
    casos_alcance=(
        CasoAlcance(
            "¿Qué debe incluir la política antisoborno de la organización?",
            True,
            "la ISO 37001 está cargada y es materia suya",
        ),
        CasoAlcance(
            "¿Qué requisitos exige la norma para la receta de un ceviche mixto?",
            False,
            "no hay norma cargada que lo cubra",
        ),
    ),
)


DIEGO = Agente(
    id="diego",
    nombre="DIEGO",
    acronimo="Due dIligence, Evaluation & Governance Operator",
    area="Debida diligencia",
    # Las cuatro normas de LA/FT son exactamente el corpus de la materia:
    # DL 1106, Ley 27693, Ley 29038, DL 1372, DS 003-2019-EF y la Resolución
    # SBS 789-2018. 132 unidades de las 824.
    materias=("laft",),
    alcance=(
        "la debida diligencia sobre clientes, proveedores y contrapartes en el "
        "Perú: qué información hay que obtener de cada uno, qué régimen le "
        "corresponde —general, reforzado o simplificado—, cuándo escala, cómo "
        "se identifica al beneficiario final y qué hay que conservar y por "
        "cuánto tiempo."
    ),
    fuera_de_alcance=(
        "consultar registros por ti. No tienes acceso a SUNAT, SUNARP, el RNP, "
        "el RNSSC ni a las listas OFAC, ONU, UE o HMT. Puedes decir qué hay que "
        "consultar en cada una y por qué; no puedes decir qué aparece en ellas. "
        "Tampoco emites un veredicto sobre si un tercero es aceptable: eso lo "
        "decide una persona con el expediente delante."
    ),
    reglas=(
        "Distingue siempre entre lo que la norma EXIGE y lo que es buena "
        "práctica. Si algo no sale de una fuente, no lo presentes como "
        "requisito: dilo como práctica y di que es práctica.",
        "El vocabulario interno de una firma —diligencia básica, mejorada, "
        "reforzada— no es el de la norma. La Resolución SBS 789-2018 nombra "
        "tres regímenes: general, reforzado y simplificado. Usa los de la norma "
        "y, si el usuario emplea los otros, di a cuál corresponde.",
        "Si te preguntan por un tercero concreto, responde qué hay que "
        "verificar y dónde, no si ese tercero está limpio. No tienes acceso a "
        "ningún registro y no debes aparentarlo.",
    ),
    casos_recuperacion=(
        CasoRecuperacion(
            "¿Cuándo se aplica el régimen reforzado de debida diligencia?",
            "res_sbs_789_2018::ley::art_16",
            5,
        ),
        CasoRecuperacion(
            "¿Qué información mínima debo pedirle a un proveedor?",
            "res_sbs_789_2018::ley::art_18",
            5,
        ),
        CasoRecuperacion(
            "¿Quién es el beneficiario final de una persona jurídica?",
            "dl_1372::ley::art_4",
            5,
        ),
        CasoRecuperacion(
            "¿Quiénes están obligados a presentar la declaración del beneficiario final?",
            "ds_003_2019_ef::reglamento::art_3",
            5,
        ),
    ),
    casos_alcance=(
        CasoAlcance(
            "¿Qué etapas tiene la debida diligencia en el conocimiento del cliente?",
            True,
            "artículo 15 de la Resolución SBS, materia suya",
        ),
        CasoAlcance(
            "¿Cada cuánto deben hacerse las auditorías del sistema de gestión de SST?",
            False,
            "seguridad y salud en el trabajo es de CARLOS; su filtro de materia "
            "no ve la Ley 29783 aunque esté en el índice",
        ),
        CasoAlcance(
            "¿Está sancionada la empresa Constructora Ejemplo SAC?",
            False,
            "no tiene acceso a ningún registro y no debe aparentarlo",
        ),
    ),
)


AGENTES: dict[str, Agente] = {a.id: a for a in (CARLOS, DIEGO)}

POR_DEFECTO = CARLOS


def obtener(id_agente: str | None) -> Agente:
    """El agente pedido, o CARLOS. Un id desconocido no es un error del
    usuario final: la interfaz puede quedarse vieja tras un despliegue, y
    responder con el general es mejor que un 400."""
    if not id_agente:
        return POR_DEFECTO
    return AGENTES.get(id_agente.strip().lower(), POR_DEFECTO)
