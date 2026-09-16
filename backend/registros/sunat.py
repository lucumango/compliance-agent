"""Padrón reducido de RUC de SUNAT: estado y condición de domicilio.

    python -m registros.sunat --actualizar    # descarga (392 MB) y reconstruye
    python -m registros.sunat 20100047218     # consulta un RUC

Es la primera comprobación de debida diligencia, y la más barata. Un proveedor
con facturación alta, sin planilla y con domicilio fiscal NO HABIDO es el
patrón clásico de empresa de fachada, y la condición de domicilio se lee aquí
sin pedirle nada al tercero.

**Por RUC es un hecho; por nombre es una pista.** El padrón dice lo que SUNAT
tiene registrado a la fecha del fichero. Un RUC con estado BAJA DE OFICIO es un
dato. En cambio, buscar por razón social devuelve candidatos, y el RUC correcto
lo confirma una persona.

**Las personas naturales solo por RUC.** El padrón incluye a millones de
personas naturales con negocio (RUC que empieza por 10), con nombre completo.
Consultar el estado del RUC de un proveedor que ya te dio su número es debida
diligencia; buscar a una persona por su nombre entre quince millones de
registros es otra cosa, y no hace falta para lo que DIEGO hace. La búsqueda
por nombre se limita a personas jurídicas.

El fichero NO se versiona ni va en la imagen: pesa 1,5 GB descomprimido. Vive
en `data/registros/`, que está en .gitignore.
"""

from __future__ import annotations

import io
import sqlite3
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .normalizar import normalizar

BASE = Path(__file__).resolve().parent.parent / "data" / "registros"
ZIP = BASE / "crudo" / "padron_reducido_ruc.zip"
DB = BASE / "sunat.sqlite"
URL = "https://www2.sunat.gob.pe/padron_reducido_ruc.zip"

# Prefijos de RUC de personas jurídicas y entes: 20 sociedades, 15/16/17 otros
# entes y no domiciliados. El 10 son personas naturales.
_JURIDICAS = ("20", "15", "16", "17")

# Estados y condiciones que merecen aviso. Se listan los que SÍ son normales,
# para que un valor nuevo que SUNAT invente salga como alerta y no como bueno.
_ESTADO_NORMAL = {"ACTIVO"}
_CONDICION_NORMAL = {"HABIDO"}


def descargar() -> None:
    ZIP.parent.mkdir(parents=True, exist_ok=True)
    print(f"  descargando {URL} ...", flush=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "CARLOS-DIEGO/1.0"})
    with urllib.request.urlopen(req, timeout=3600) as resp, open(ZIP, "wb") as f:
        while bloque := resp.read(1 << 20):
            f.write(bloque)
    print(f"  {ZIP.stat().st_size / 1e6:.0f} MB")


def construir() -> int:
    if not ZIP.exists():
        raise FileNotFoundError(f"Falta {ZIP}. Ejecuta con --actualizar.")
    temporal = DB.with_suffix(".tmp")
    temporal.unlink(missing_ok=True)
    con = sqlite3.connect(temporal)
    con.executescript(
        """
        PRAGMA journal_mode = OFF;
        PRAGMA synchronous = OFF;
        CREATE TABLE contribuyente (
          ruc TEXT PRIMARY KEY, nombre TEXT, estado TEXT, condicion TEXT, ubigeo TEXT
        ) WITHOUT ROWID;
        CREATE TABLE nombre_juridica (nombre TEXT, ruc TEXT);
        CREATE TABLE meta (clave TEXT PRIMARY KEY, valor TEXT);
        """
    )
    with zipfile.ZipFile(ZIP) as z:
        info = z.infolist()[0]
        fecha = datetime(*info.date_time).date().isoformat()
        filas, juridicas, total = [], [], 0
        with z.open(info) as crudo:
            texto = io.TextIOWrapper(crudo, encoding="latin-1", newline="")
            next(texto)  # cabecera
            for linea in texto:
                c = linea.split("|")
                if len(c) < 5 or not c[0].isdigit():
                    continue
                ruc = c[0]
                filas.append((ruc, c[1].strip(), c[2].strip(), c[3].strip(), c[4].strip()))
                if ruc.startswith(_JURIDICAS):
                    juridicas.append((normalizar(c[1]), ruc))
                if len(filas) >= 200_000:
                    con.executemany("INSERT OR REPLACE INTO contribuyente VALUES (?,?,?,?,?)", filas)
                    con.executemany("INSERT INTO nombre_juridica VALUES (?,?)", juridicas)
                    total += len(filas)
                    filas, juridicas = [], []
                    print(f"\r  {total:>11,} contribuyentes", end="", flush=True)
        con.executemany("INSERT OR REPLACE INTO contribuyente VALUES (?,?,?,?,?)", filas)
        con.executemany("INSERT INTO nombre_juridica VALUES (?,?)", juridicas)
        total += len(filas)
    print(f"\r  {total:>11,} contribuyentes. Indexando nombres...", flush=True)
    con.execute("CREATE INDEX idx_nombre ON nombre_juridica(nombre)")
    con.executemany("INSERT INTO meta VALUES (?,?)", [("fecha", fecha), ("total", str(total))])
    con.commit()
    con.close()
    temporal.replace(DB)
    print(f"  {DB.name}: {DB.stat().st_size / 1e6:.0f} MB, padrón del {fecha}")
    return total


@dataclass
class Contribuyente:
    ruc: str
    nombre: str
    estado: str
    condicion: str
    ubigeo: str
    alertas: list[str]


def _alertas(estado: str, condicion: str) -> list[str]:
    alertas = []
    if estado not in _ESTADO_NORMAL:
        alertas.append(f"Estado del contribuyente: {estado or 'sin estado registrado'}")
    # SUNAT escribe "-" cuando no hay condición registrada: 86.940 personas
    # jurídicas en el padrón del 16/09/2026. No es HABIDO, así que se avisa,
    # pero diciéndolo con palabras: "Condición de domicilio: -" no lo entiende
    # nadie.
    if condicion not in _CONDICION_NORMAL:
        texto = "sin condición registrada" if condicion in ("", "-") else condicion
        alertas.append(f"Condición de domicilio: {texto}")
    return alertas


class Padron:
    def __init__(self) -> None:
        if not DB.exists():
            raise FileNotFoundError(
                "No hay padrón de SUNAT. Ejecuta: python -m registros.sunat --actualizar"
            )
        # check_same_thread=False: FastAPI atiende en hilos, y la conexión es de
        # solo lectura.
        self._con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)
        self.fecha = self._con.execute("SELECT valor FROM meta WHERE clave='fecha'").fetchone()[0]

    def por_ruc(self, ruc: str) -> Contribuyente | None:
        ruc = "".join(ch for ch in ruc if ch.isdigit())
        if len(ruc) != 11:
            return None
        fila = self._con.execute(
            "SELECT ruc, nombre, estado, condicion, ubigeo FROM contribuyente WHERE ruc=?", (ruc,)
        ).fetchone()
        if not fila:
            return None
        return Contribuyente(*fila, alertas=_alertas(fila[2], fila[3]))

    def por_nombre(self, nombre: str, limite: int = 10) -> list[Contribuyente]:
        """Candidatos entre personas jurídicas. Prefijo de la razón social
        normalizada: "CONSTRUCTORA ANDINA" encuentra "CONSTRUCTORA ANDINA DEL SUR"."""
        norm = normalizar(nombre)
        if len(norm) < 4:
            return []
        rucs = [
            r for (r,) in self._con.execute(
                "SELECT ruc FROM nombre_juridica WHERE nombre >= ? AND nombre < ? LIMIT ?",
                (norm, norm + "￿", limite),
            )
        ]
        return [c for r in rucs if (c := self.por_ruc(r))]


def main() -> int:
    if "--actualizar" in sys.argv:
        if "--sin-descargar" not in sys.argv:
            descargar()
        construir()
        return 0
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    p = Padron()
    arg = " ".join(sys.argv[1:])
    resultados = [c for c in [p.por_ruc(arg)] if c] if arg.strip().isdigit() else p.por_nombre(arg)
    if not resultados:
        print(f"Sin resultados en el padrón del {p.fecha}.")
        return 0
    for c in resultados:
        marca = "ALERTA" if c.alertas else "ok    "
        print(f"{marca} {c.ruc}  {c.nombre[:50]:50} {c.estado} / {c.condicion}")
    print(f"\nPadrón reducido de RUC de SUNAT, fichero del {p.fecha}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
