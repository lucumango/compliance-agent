"""Listas de sanciones: OFAC, ONU, UE y Reino Unido.

    python -m registros.listas --actualizar    # descarga y reconstruye
    python -m registros.listas "nombre"         # busca

**Una coincidencia es siempre potencial.** Cotejar un nombre contra una lista es
comparar cadenas de texto, no identificar a una persona. "JUAN CARLOS PEREZ" en
la lista OFAC no es el Juan Carlos Pérez que es proveedor de tu cliente hasta
que alguien lo contrasta con fecha de nacimiento, documento o nacionalidad.
Todo lo que sale de aquí lleva esa advertencia, y ninguna función de este
módulo devuelve "está sancionado".

**Y un "no aparece" siempre lleva fecha.** Cada lista guarda la fecha en que la
generó su emisor. Una búsqueda sin coincidencias dice contra qué listas se
comparó y a qué fecha, y avisa si alguna tiene más de una semana.

Fuentes, verificadas el 16/09/2026:

  OFAC  Tesoro de EE. UU., lista SDN y sus alias
  ONU   Consejo de Seguridad, lista consolidada
  UE    Lista consolidada de sanciones financieras (FSF)
  UK    UK Sanctions List, de la FCDO. NO la "Consolidated List" de OFSI que sale
        primero en los buscadores: esa se retiró el 28/01/2026 y no se actualiza.
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path

from rapidfuzz import fuzz, process

from .normalizar import normalizar

BASE = Path(__file__).resolve().parent.parent / "data" / "registros"
CRUDO = BASE / "crudo"
DATOS = BASE / "listas.json.gz"

FUENTES = {
    "ofac_sdn.csv": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN.CSV",
    "ofac_alt.csv": "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ALT.CSV",
    "onu.xml": "https://scsanctions.un.org/resources/xml/en/consolidated.xml",
    "ue.csv": "https://webgate.ec.europa.eu/fsd/fsf/public/files/csvFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw",
    "uk.csv": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv",
}

NOMBRES_LISTA = {
    "OFAC": "OFAC — Specially Designated Nationals (EE. UU.)",
    "ONU": "Consejo de Seguridad de las Naciones Unidas — lista consolidada",
    "UE": "Unión Europea — sanciones financieras consolidadas",
    "UK": "Reino Unido — UK Sanctions List (FCDO)",
}

# Por encima de esto, una coincidencia se enseña. Elegido con los casos de
# `registros.evaluar`: a 85 "BANCO NACIONAL DE CUBA" ya no encuentra
# "NATIONAL BANK OF CUBA" —otro idioma— pero sí aguanta erratas y el orden
# apellido-nombre, que es lo que más varía entre listas.
UMBRAL = 85

# Una lista más vieja que esto se avisa. Las cuatro se publican a diario o casi.
DIAS_VIGENCIA = 7


@dataclass
class Designado:
    lista: str
    id: str
    nombre: str
    tipo: str  # persona | entidad | nave | aeronave
    alias: list[str] = field(default_factory=list)
    programa: str = ""
    paises: list[str] = field(default_factory=list)
    fecha_designacion: str = ""
    identificadores: list[str] = field(default_factory=list)


# ----------------------------------------------------------------- descarga


def descargar() -> None:
    CRUDO.mkdir(parents=True, exist_ok=True)
    for nombre, url in FUENTES.items():
        destino = CRUDO / nombre
        print(f"  {nombre:14} ", end="", flush=True)
        req = urllib.request.Request(url, headers={"User-Agent": "CARLOS-DIEGO/1.0"})
        with urllib.request.urlopen(req, timeout=300) as resp, open(destino, "wb") as f:
            f.write(resp.read())
        print(f"{destino.stat().st_size / 1e6:.1f} MB")


# ----------------------------------------------------------------- lectura


def _ofac() -> tuple[list[Designado], str]:
    alias: dict[str, list[str]] = {}
    with open(CRUDO / "ofac_alt.csv", encoding="latin-1") as f:
        for fila in csv.reader(f):
            if len(fila) >= 4:
                alias.setdefault(fila[0].strip(), []).append(fila[3].strip())

    tipos = {"individual": "persona", "vessel": "nave", "aircraft": "aeronave"}
    salida = []
    with open(CRUDO / "ofac_sdn.csv", encoding="latin-1") as f:
        for fila in csv.reader(f):
            if len(fila) < 12 or not fila[0].strip().isdigit():
                continue
            ent = fila[0].strip()
            observ = fila[11].strip() if fila[11].strip() != "-0-" else ""
            salida.append(
                Designado(
                    lista="OFAC",
                    id=ent,
                    nombre=fila[1].strip(),
                    tipo=tipos.get(fila[2].strip(), "entidad"),
                    alias=alias.get(ent, []),
                    programa=fila[3].strip(),
                    # OFAC mete documentos y nacionalidades en observaciones,
                    # en texto libre. Se conserva entero: es lo que permite
                    # descartar un homónimo.
                    identificadores=[observ[:400]] if observ else [],
                )
            )
    # OFAC no pone fecha dentro del CSV. La del fichero es la de la descarga,
    # que es lo más honesto que se puede decir.
    fecha = datetime.fromtimestamp((CRUDO / "ofac_sdn.csv").stat().st_mtime).date()
    return salida, fecha.isoformat()


def _texto(nodo, ruta: str) -> str:
    hijo = nodo.find(ruta)
    return (hijo.text or "").strip() if hijo is not None else ""


def _onu() -> tuple[list[Designado], str]:
    raiz = ET.parse(CRUDO / "onu.xml").getroot()
    fecha = (raiz.get("dateGenerated") or "")[:10]
    salida = []

    for ind in raiz.iterfind("INDIVIDUALS/INDIVIDUAL"):
        partes = [_texto(ind, t) for t in ("FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME")]
        alias = [_texto(a, "ALIAS_NAME") for a in ind.iterfind("INDIVIDUAL_ALIAS")]
        docs = [
            " ".join(filter(None, (_texto(d, "TYPE_OF_DOCUMENT"), _texto(d, "NUMBER"))))
            for d in ind.iterfind("INDIVIDUAL_DOCUMENT")
        ]
        salida.append(
            Designado(
                lista="ONU",
                id=_texto(ind, "REFERENCE_NUMBER"),
                nombre=" ".join(p for p in partes if p),
                tipo="persona",
                alias=[a for a in alias if a],
                programa=_texto(ind, "UN_LIST_TYPE"),
                paises=[_texto(n, "VALUE") for n in ind.iterfind("NATIONALITY") if _texto(n, "VALUE")],
                fecha_designacion=_texto(ind, "LISTED_ON"),
                identificadores=[d for d in docs if d],
            )
        )

    for ent in raiz.iterfind("ENTITIES/ENTITY"):
        alias = [_texto(a, "ALIAS_NAME") for a in ent.iterfind("ENTITY_ALIAS")]
        salida.append(
            Designado(
                lista="ONU",
                id=_texto(ent, "REFERENCE_NUMBER"),
                nombre=_texto(ent, "FIRST_NAME"),
                tipo="entidad",
                alias=[a for a in alias if a],
                programa=_texto(ent, "UN_LIST_TYPE"),
                fecha_designacion=_texto(ent, "LISTED_ON"),
            )
        )
    return salida, fecha


def _ue() -> tuple[list[Designado], str]:
    # Una fila por cada combinación de alias, dirección, fecha de nacimiento...
    # del mismo sujeto. Se agrupan por Entity_LogicalId.
    por_id: dict[str, Designado] = {}
    fecha = ""
    tipos = {"person": "persona", "enterprise": "entidad"}
    with open(CRUDO / "ue.csv", encoding="utf-8-sig") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            fecha = fecha or fila.get("fileGenerationDate", "")
            ident = fila["Entity_LogicalId"]
            d = por_id.get(ident)
            if d is None:
                d = por_id[ident] = Designado(
                    lista="UE",
                    id=fila.get("Entity_EU_ReferenceNumber") or ident,
                    nombre="",
                    tipo=tipos.get(fila.get("Entity_SubjectType_ClassificationCode", ""), "entidad"),
                    programa=fila.get("Entity_Regulation_Programme", ""),
                    fecha_designacion=fila.get("Entity_DesignationDate", ""),
                )
            completo = (fila.get("NameAlias_WholeName") or "").strip()
            if completo:
                if not d.nombre:
                    d.nombre = completo
                elif completo not in d.alias and completo != d.nombre:
                    d.alias.append(completo)
            pais = (fila.get("Address_CountryDescription") or "").strip()
            if pais and pais not in d.paises:
                d.paises.append(pais)
    # La UE escribe la fecha como DD/MM/AAAA.
    try:
        fecha = datetime.strptime(fecha, "%d/%m/%Y").date().isoformat()
    except ValueError:
        pass
    return [d for d in por_id.values() if d.nombre], fecha


def _uk() -> tuple[list[Designado], str]:
    por_id: dict[str, Designado] = {}
    tipos = {"Individual": "persona", "Entity": "entidad", "Ship": "nave"}
    with open(CRUDO / "uk.csv", encoding="utf-8-sig") as f:
        primera = f.readline()  # "Report Date: 11-Sep-2026"
        try:
            fecha = datetime.strptime(primera.split(":", 1)[1].strip().rstrip(","), "%d-%b-%Y").date().isoformat()
        except (IndexError, ValueError):
            fecha = ""
        for fila in csv.DictReader(f):
            ident = fila["Unique ID"]
            # En el Reino Unido "Name 6" es el apellido o el nombre de la
            # entidad, y "Name 1" a "Name 5" los nombres de pila.
            nombre = " ".join(
                p.strip() for p in (fila[f"Name {i}"] for i in (1, 2, 3, 4, 5, 6)) if p.strip()
            )
            if not nombre:
                continue
            d = por_id.get(ident)
            if d is None:
                d = por_id[ident] = Designado(
                    lista="UK",
                    id=ident,
                    nombre="",
                    tipo=tipos.get(fila["Designation Type"], "entidad"),
                    programa=fila["Regime Name"],
                    fecha_designacion=fila["Date Designated"],
                )
            principal = fila["Name type"].strip().lower() == "primary name"
            if principal and not d.nombre:
                d.nombre = nombre
            elif nombre != d.nombre and nombre not in d.alias:
                d.alias.append(nombre)
            for col in ("Nationality(/ies)", "Address Country"):
                valor = fila.get(col, "").strip()
                if valor and valor not in d.paises:
                    d.paises.append(valor)
            doc = fila.get("Passport number", "").strip() or fila.get("National Identifier number", "").strip()
            if doc and doc not in d.identificadores:
                d.identificadores.append(doc)
    for d in por_id.values():
        if not d.nombre and d.alias:
            d.nombre = d.alias.pop(0)
    return list(por_id.values()), fecha


def construir() -> dict:
    todos: list[Designado] = []
    meta: dict[str, dict] = {}
    for clave, lector in (("OFAC", _ofac), ("ONU", _onu), ("UE", _ue), ("UK", _uk)):
        registros, fecha = lector()
        todos += registros
        meta[clave] = {"nombre": NOMBRES_LISTA[clave], "fecha": fecha, "designados": len(registros)}
        print(f"  {clave:5} {len(registros):6} designados, lista del {fecha}")

    BASE.mkdir(parents=True, exist_ok=True)
    with gzip.open(DATOS, "wt", encoding="utf-8") as f:
        json.dump({"listas": meta, "designados": [asdict(d) for d in todos]}, f, ensure_ascii=False)
    print(f"  total {len(todos)} designados -> {DATOS.name} ({DATOS.stat().st_size / 1e6:.1f} MB)")
    return meta


# -------------------------------------------------------------------- búsqueda


@dataclass
class Coincidencia:
    lista: str
    lista_nombre: str
    id: str
    nombre: str
    nombre_coincidente: str
    score: float
    tipo: str
    programa: str
    paises: list[str]
    identificadores: list[str]
    fecha_designacion: str


class Cotejo:
    """El índice en memoria. Se carga una vez: son decenas de miles de nombres."""

    def __init__(self) -> None:
        if not DATOS.exists():
            raise FileNotFoundError(
                "No hay listas descargadas. Ejecuta: python -m registros.listas --actualizar"
            )
        with gzip.open(DATOS, "rt", encoding="utf-8") as f:
            datos = json.load(f)
        self.listas: dict[str, dict] = datos["listas"]
        self.designados = [Designado(**d) for d in datos["designados"]]
        # Un nombre normalizado por fila, apuntando a su designado. Los alias
        # cuentan igual que el nombre principal: es en los alias donde suelen
        # estar las transliteraciones.
        self._nombres: list[str] = []
        self._dueño: list[int] = []
        for i, d in enumerate(self.designados):
            for n in [d.nombre, *d.alias]:
                norm = normalizar(n)
                if len(norm) >= 4:
                    self._nombres.append(norm)
                    self._dueño.append(i)

    def vigencia(self, hoy: date | None = None) -> list[str]:
        """Avisos de listas viejas. Un "no aparece" contra una lista de hace un
        mes no dice nada."""
        hoy = hoy or date.today()
        avisos = []
        for clave, m in self.listas.items():
            try:
                dias = (hoy - date.fromisoformat(m["fecha"])).days
            except (ValueError, TypeError):
                avisos.append(f"{clave}: no se pudo leer la fecha de la lista.")
                continue
            if dias > DIAS_VIGENCIA:
                avisos.append(f"{clave}: la lista es del {m['fecha']}, hace {dias} días. Actualízala antes de fiarte del resultado.")
        return avisos

    def buscar(self, nombre: str, tipo: str | None = None, umbral: float = UMBRAL, limite: int = 10) -> list[Coincidencia]:
        consulta = normalizar(nombre)
        if len(consulta) < 4:
            return []
        # token_sort_ratio y no token_set_ratio: el segundo da 100 cuando un
        # nombre está contenido en otro, y "JUAN PEREZ" saldría idéntico a
        # "JUAN PEREZ ALIAS EL CARNICERO". Con muchos homónimos, eso es ruido.
        crudos = process.extract(
            consulta, self._nombres, scorer=fuzz.token_sort_ratio,
            score_cutoff=umbral, limit=limite * 4,
        )
        vistos: dict[tuple[str, str], Coincidencia] = {}
        for texto, score, idx in crudos:
            d = self.designados[self._dueño[idx]]
            if tipo and d.tipo != tipo:
                continue
            clave = (d.lista, d.id)
            if clave in vistos and vistos[clave].score >= score:
                continue
            vistos[clave] = Coincidencia(
                lista=d.lista, lista_nombre=NOMBRES_LISTA[d.lista], id=d.id,
                nombre=d.nombre, nombre_coincidente=texto, score=round(score, 1),
                tipo=d.tipo, programa=d.programa, paises=d.paises[:5],
                identificadores=d.identificadores[:5], fecha_designacion=d.fecha_designacion,
            )
        return sorted(vistos.values(), key=lambda c: -c.score)[:limite]


def main() -> int:
    if "--actualizar" in sys.argv:
        print("Descargando:")
        descargar()
        print("Construyendo:")
        construir()
        return 0
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cotejo = Cotejo()
    nombre = " ".join(a for a in sys.argv[1:] if not a.startswith("--"))
    for aviso in cotejo.vigencia():
        print("AVISO:", aviso)
    resultados = cotejo.buscar(nombre)
    listas = ", ".join(f"{k} ({m['fecha']})" for k, m in cotejo.listas.items())
    if not resultados:
        print(f"Sin coincidencias sobre {UMBRAL} para {nombre!r} en: {listas}")
        return 0
    print(f"Coincidencias POTENCIALES para {nombre!r} — requieren revisión humana:\n")
    for c in resultados:
        print(f"  {c.score:5.1f}  {c.lista:4} {c.id:12} {c.nombre[:50]}")
        print(f"         {c.tipo} · {c.programa[:60]} · {', '.join(c.paises[:3])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
