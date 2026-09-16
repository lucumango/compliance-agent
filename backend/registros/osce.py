"""Proveedores sancionados por el Tribunal de Contrataciones del Estado.

    python -m registros.osce --actualizar
    python -m registros.osce 20600147464

Inhabilitados para contratar con el Estado, temporal o definitivamente. Es la
parte descargable del RNP: la manual-casos lo pide en debida diligencia, y un
proveedor inhabilitado que le vende al cliente para una obra pública es un
problema del cliente.

**Por RUC es un hecho; por nombre, una pista.** Igual que el padrón de SUNAT.

**El dataset NO está al día, y eso se dice.** La Plataforma Nacional de Datos
Abiertos lo publicó por última vez el 17/12/2025 (verificado el 16/09/2026):
las inhabilitaciones posteriores no están, y algunas temporales ya vencieron.
Por eso cada resultado lleva la fecha del fichero y se calcula si la sanción
sigue vigente HOY con su fecha de fin, no con lo que diga la columna.

Lo que no está, y conviene saberlo antes de buscarlo:

  * **El RNSSC** (sanciones a servidores civiles) SÍ está en datos abiertos,
    pero anonimizado: nombre "****** ****** ******" y documento "********" en
    las 10.014 filas de los tres ficheros publicados. Sirve para estadística;
    para comprobar a una persona hay que ir al portal de SERVIR con su DNI.
  * **SUNARP** no publica nada descargable.
"""

from __future__ import annotations

import csv
import gzip
import json
import sys
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date
from email.utils import parsedate_to_datetime
from pathlib import Path

from rapidfuzz import fuzz, process

from .normalizar import normalizar

BASE = Path(__file__).resolve().parent.parent / "data" / "registros"
CRUDO = BASE / "crudo" / "osce_sancionados.csv"
DATOS = BASE / "osce.json.gz"
URL = (
    "https://www.datosabiertos.gob.pe/sites/default/files/"
    "Relaci%C3%B3n%20de%20proveedores%20sancionados%20por%20el%20Tribunal%20de%20"
    "Contrataciones%20P%C3%BAblicas%20con%20sanci%C3%B3n%20vigente.csv"
)
UMBRAL = 88


@dataclass
class Sancion:
    ruc: str
    razon_social: str
    tipo: str  # Definitivo | Temporal
    resolucion: str
    desde: str
    hasta: str
    infraccion: str


def descargar() -> str:
    CRUDO.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0 CARLOS-DIEGO"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        CRUDO.write_bytes(resp.read())
        modificado = resp.headers.get("Last-Modified")
    # La fecha que importa es la de publicación del dataset, no la de hoy.
    return parsedate_to_datetime(modificado).date().isoformat() if modificado else ""


def _iso(aaaammdd: str) -> str:
    s = aaaammdd.strip()
    return f"{s[:4]}-{s[4:6]}-{s[6:8]}" if len(s) == 8 and s.isdigit() else ""


def construir(fecha_dataset: str = "") -> int:
    sanciones = []
    with open(CRUDO, encoding="latin-1", newline="") as f:
        for fila in csv.DictReader(f, delimiter=";"):
            ruc = (fila.get("RUC") or "").strip()
            # 478 filas del fichero de 12/2025 vienen enteras en blanco.
            if not ruc:
                continue
            sanciones.append(
                Sancion(
                    ruc=ruc,
                    razon_social=(fila.get("RAZON_SOCIAL") or "").strip(),
                    tipo=(fila.get("INH") or "").strip(),
                    resolucion=" ".join((fila.get("RESOLUCION") or "").split()),
                    desde=_iso(fila.get("DESDE") or ""),
                    hasta=_iso(fila.get("HASTA") or ""),
                    infraccion=" ".join((fila.get("INFRACCION") or "").split())[:600],
                )
            )
    BASE.mkdir(parents=True, exist_ok=True)
    with gzip.open(DATOS, "wt", encoding="utf-8") as f:
        json.dump({"fecha": fecha_dataset, "sanciones": [asdict(s) for s in sanciones]}, f, ensure_ascii=False)
    print(f"  {len(sanciones)} sanciones, dataset del {fecha_dataset or 'fecha desconocida'}")
    return len(sanciones)


def vigente(s: Sancion, hoy: date | None = None) -> bool:
    """Definitiva = siempre. Temporal = hasta su fecha de fin, inclusive."""
    if s.tipo.lower().startswith("defin") or not s.hasta:
        return True
    return date.fromisoformat(s.hasta) >= (hoy or date.today())


class Inhabilitados:
    def __init__(self) -> None:
        if not DATOS.exists():
            raise FileNotFoundError(
                "No hay sanciones del OSCE. Ejecuta: python -m registros.osce --actualizar"
            )
        with gzip.open(DATOS, "rt", encoding="utf-8") as f:
            datos = json.load(f)
        self.fecha: str = datos["fecha"]
        self.sanciones = [Sancion(**s) for s in datos["sanciones"]]
        self._por_ruc: dict[str, list[Sancion]] = {}
        for s in self.sanciones:
            self._por_ruc.setdefault(s.ruc, []).append(s)
        self._nombres = [normalizar(s.razon_social) for s in self.sanciones]

    def antiguedad_dias(self, hoy: date | None = None) -> int | None:
        try:
            return ((hoy or date.today()) - date.fromisoformat(self.fecha)).days
        except ValueError:
            return None

    def por_ruc(self, ruc: str) -> list[dict]:
        ruc = "".join(ch for ch in ruc if ch.isdigit())
        return [asdict(s) | {"vigente_hoy": vigente(s)} for s in self._por_ruc.get(ruc, [])]

    def por_nombre(self, nombre: str, limite: int = 5) -> list[dict]:
        consulta = normalizar(nombre)
        if len(consulta) < 4:
            return []
        crudos = process.extract(consulta, self._nombres, scorer=fuzz.token_sort_ratio,
                                 score_cutoff=UMBRAL, limit=limite)
        return [
            asdict(self.sanciones[i]) | {"vigente_hoy": vigente(self.sanciones[i]), "score": round(sc, 1)}
            for _, sc, i in crudos
        ]


def main() -> int:
    if "--actualizar" in sys.argv:
        fecha = descargar()
        construir(fecha)
        return 0
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    ins = Inhabilitados()
    arg = " ".join(sys.argv[1:])
    res = ins.por_ruc(arg) if arg.strip().isdigit() else ins.por_nombre(arg)
    print(f"Dataset del {ins.fecha} ({ins.antiguedad_dias()} días).")
    for r in res or []:
        estado = "VIGENTE" if r["vigente_hoy"] else "vencida"
        print(f"  {estado:8} {r['ruc']} {r['razon_social'][:45]} {r['tipo']} {r['desde']}→{r['hasta'] or '—'}")
    if not res:
        print("  Sin sanciones en este dataset.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
