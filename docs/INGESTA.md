# Cargar documentos nuevos

Paso a paso para meter un PDF normativo en el corpus. Pensado para ejecutarse
desde cualquier máquina con acceso al repo.

> **Antes de empezar, lee [Trabajar entre dos personas](#trabajar-entre-dos-personas).**
> El índice vectorial es un binario y no se puede fusionar; si dos personas lo
> reconstruyen a la vez, uno de los dos pierde el trabajo.

## 0. Preparar la máquina (una sola vez)

```bash
git clone <url-del-repo> && cd <repo>/backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-ingesta.txt      # incluye los de runtime
```

`requirements-ingesta.txt` trae PyMuPDF, OpenCV y pytesseract, que solo hacen
falta para procesar PDFs. El servidor de producción no los instala.

Si vas a ingerir **escaneos**, hace falta además el binario de Tesseract con
español:

```bash
brew install tesseract tesseract-lang       # macOS
sudo apt install tesseract-ocr tesseract-ocr-spa   # Debian/Ubuntu
```

Comprueba que está: `tesseract --list-langs | grep spa`

Por último, la clave del modelo:

```bash
cp .env.example .env      # y pon tu GOOGLE_API_KEY de Google AI Studio
```

`.env` está en `.gitignore`. **Nunca lo commitees.** Cada persona usa su propia
clave; las cuotas del plan gratuito son por cuenta.

## 1. Colocar el PDF

```bash
cp ~/Downloads/mi_norma.pdf backend/data/raw/normativas/ley_31740.pdf
```

**El nombre del archivo importa.** Usa el mismo patrón que el `norma_id`:

| Tipo | Patrón | Ejemplo |
|---|---|---|
| Ley | `ley_<numero>.pdf` | `ley_31740.pdf` |
| Decreto Supremo | `ds_<numero>_<anio>_<sector>.pdf` | `ds_002_2019_jus.pdf` |
| Resolución SBS | `rsbs_<numero>_<anio>.pdf` | `rsbs_02660_2015.pdf` |
| Norma técnica | `iso_<numero>.pdf` | `iso_37301.pdf` |

Prefiere el **texto consolidado** al original siempre que exista. Si solo
consigues el original, se puede cargar, pero anótalo en `notas` (ver paso 2) —
es exactamente el caso de la Ley 30424.

## 2. Registrar la norma

Añade una entrada a `REGISTRY` en `backend/ingestion/registry.py`. Es el único
sitio donde se declara una fuente:

```python
NormaMeta(
    norma_id="ley_31740",
    archivo="ley_31740.pdf",
    tipo="ley",                          # "ley" | "norma_tecnica"
    numero="31740",
    nombre="Ley que modifica la Ley 30424",   # como aparece en la fuente
    materia="anticorrupcion",            # reutiliza una materia si encaja
    entidad_reguladora=["MINJUSDH"],
    parser="ley",                        # "ley" | "iso"
    fecha_publicacion=None,              # SOLO si la lees en el documento
    url_fuente=None,                     # idem
    metadata_verificada=False,
    notas=(
        "Texto consolidado descargado de SPIJ el 12/08/2026. "
        "Incluye las modificatorias hasta esa fecha."
    ),
),
```

Tres campos que se hacen mal con facilidad:

- **`fecha_publicacion` y `url_fuente`:** déjalos en `None` salvo que el dato
  esté impreso en el PDF. No los rellenes de memoria ni de una búsqueda rápida.
- **`notas`:** lo lee el usuario final al pie de las respuestas, no es un
  comentario interno. Si el texto es original, está incompleto o viene de un
  escaneo dudoso, dilo aquí. Si contiene la palabra *"original"*, el sistema lo
  emite automáticamente como advertencia.
- **`materia`:** si inventas una nueva, aparecerá sola en el filtro de la
  interfaz. No hay que tocar el frontend.

## 3. Ingerir y validar

```bash
cd backend && source .venv/bin/activate

python -m ingestion.ingest      # PDFs -> data/parsed/*.json
python -m ingestion.validate    # controles de calidad
```

`validate` tiene que salir **0 problemas** antes de seguir. Comprueba:

- numeración de artículos sin huecos ni duplicados,
- que no se coló texto de cabecera/pie de página,
- unidades sospechosamente cortas,
- que ninguna unidad se quedó sin cita.

Si sale con problemas, ve a [Cuando el parser falla](#cuando-el-parser-falla).

Revisa también a ojo el JSON generado, sobre todo el primer y último artículo:

```bash
python3 -c "
import json; d=json.load(open('data/parsed/ley_31740.json'))
print(d['nombre'], '|', len(d['unidades']), 'unidades')
print('OCR:', d['extraccion']['paginas_ocr'], 'de', d['extraccion']['paginas'], 'páginas')
for u in d['unidades'][:2] + d['unidades'][-2:]:
    print(' ', u['cita'], '->', u['texto'][:90].replace(chr(10),' '))
"
```

## 4. Reconstruir el índice

```bash
python -m rag.index
```

⚠ **Esto revectoriza el corpus entero, no solo lo nuevo.** Hoy son ~6 minutos y
701 unidades; el tiempo crece de forma lineal con el corpus y está limitado por
la cuota de embeddings, no por la CPU. Con 3.000 unidades cuenta con media hora
larga y con toparte con 429 del plan gratuito (el cliente reintenta solo, con
espera exponencial).

Reconstruye **una sola vez**, al final, cuando hayas cargado todos los PDFs de
la tanda. No una vez por documento.

## 5. Comprobar que la recuperación no empeoró

```bash
python -m rag.eval
```

Los 8 casos de referencia deben seguir en **8/8**. Es la red de seguridad: un
corpus más grande puede desplazar de los primeros puestos a un artículo que
antes se recuperaba bien.

Si tu norma nueva es importante, **añádele un caso** en `rag/eval.py`: una
consulta realista y el ID de la unidad que debería recuperar.

```python
(
    "¿Qué modificó la Ley 31740 en el régimen de personas jurídicas?",
    "ley_31740::ley::art_1",
    5,
),
```

Y una prueba manual, que ve cosas que la evaluación no:

```bash
python -m rag.cli "tu consulta sobre la norma nueva"
```

## 6. Commitear

```bash
git add data/raw/normativas/ley_31740.pdf \
        data/parsed/ley_31740.json \
        data/index/ \
        ingestion/registry.py rag/eval.py
git commit -m "Cargar Ley 31740 al corpus"
```

Commitea el PDF de origen: es lo que permite reconstruir el corpus desde cero y
auditar de dónde salió cada cita.

Actualiza también la tabla de [FUENTES.md](FUENTES.md) — si no, en tres meses
nadie sabrá qué hay cargado sin abrir el código.

## Trabajar entre dos personas

`data/index/vectors.npy` es un binario de ~9 MB (crecerá). **Git no lo puede
fusionar.** Si dos personas reconstruyen el índice en paralelo, el segundo
`merge` da conflicto y la única salida es descartar un lado y reconstruir.

Reglas para que no duela:

1. **Avisad antes de reconstruir el índice.** Es la operación que colisiona; el
   resto (registrar, parsear, validar) no.
2. **Una tanda, una reconstrucción.** Agrupad los PDFs y reindexad al final.
3. **Al resolver un conflicto en `vectors.npy` o `unidades.json`: no elijáis un
   lado.** Quedaos con los `registry.py` y `data/parsed/` de ambos, y
   reconstruid el índice desde cero:
   ```bash
   git checkout --theirs data/index/ && python -m ingestion.ingest && python -m rag.index
   ```
   El índice es *derivado*: siempre se puede regenerar desde `data/parsed/`. Lo
   que nunca debe perderse es el PDF, el `registry.py` y el JSON parseado.
4. **Cada persona con su propia `GOOGLE_API_KEY`**, en su `.env` local.

Si esto se vuelve incómodo, la salida es sacar el índice de git y publicarlo
como artefacto (release, o un bucket), dejando en el repo solo el corpus
parseado. Merece la pena cuando el índice pase de ~50 MB.

## Cuando el parser falla

`ingestion/parser.py` asume la estructura de una ley peruana publicada en El
Peruano: `Título` → `Capítulo`/`Sección` → `Artículo N.-`, más los bloques de
disposiciones complementarias. `ingestion/iso_parser.py` asume cláusulas
decimales (`7.2.1`) más Anexo A.

Un documento con otra estructura —una Resolución SBS, una directiva— **no va a
parsear bien**, y `validate` lo va a delatar con unidades cortas o huecos en la
numeración. Es trabajo de parser, no de configuración.

Fallos frecuentes y qué significan:

| Síntoma en `validate` | Causa probable |
|---|---|
| `artículos faltantes [12, 13]` | El encabezado no casó: numeral mal reconocido por OCR, o formato distinto (`Artículo Décimo`) |
| `texto sospechosamente corto` | El artículo se partió, o es un encabezado de agrupación sin cuerpo propio |
| `termina con el encabezado del artículo siguiente` | El límite entre artículos se calculó mal |
| `contiene texto de página repetido` | Cabecera o pie de El Peruano colándose; hay que añadir el patrón a `_FURNITURE_SIGNS` |

Para escaneos, `extract.py` ya borra por *inpainting* las líneas horizontales
de subrayado antes del OCR: sin eso, `Artículo 3º.-` se leía `lo 39.-` y se
perdía el límite del artículo. Si aparece un escaneo con otro tipo de ruido
(sellos, marcas de agua), es ahí donde se ataja.

## Resumen

```bash
# 1. copiar el PDF a backend/data/raw/normativas/
# 2. añadir el NormaMeta a ingestion/registry.py
cd backend && source .venv/bin/activate
python -m ingestion.ingest        # 3.
python -m ingestion.validate      #    -> 0 problemas
python -m rag.index               # 4.  (una vez por tanda, ~6+ min)
python -m rag.eval                # 5.  -> 8/8
# 6. commit del PDF + JSON + índice + registry, y actualizar FUENTES.md
```
