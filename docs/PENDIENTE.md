# Pendiente

Lo que falta, con el contexto necesario para retomarlo sin releer el código.
Ordenado por lo que yo atacaría primero.

---

## 1. Texto consolidado de la Ley 30424

**Por qué importa más que el resto.** Es el único punto en el que el sistema
puede responder algo **desactualizado sin saberlo**. Los demás son mejoras;
este es una corrección.

El PDF cargado es el original del 21/04/2016, anterior a la Ley 30835 (2018) y
la Ley 31740 (2023). Se nota en el nombre que arrastra: *"…por el delito de
cohecho activo transnacional"*, que era el alcance de 2016. El vigente cubre
bastante más, así que una consulta sobre el ámbito de aplicación se queda corta.

El sistema avisa —la nota viaja en `advertencias` con cada respuesta que lo
cite— pero el aviso no corrige el contenido.

**Qué hace falta:** el texto consolidado en PDF, de SPIJ o El Peruano. No se
puede reconstruir a partir de lo que hay: habría que redactar articulado, y
eso es justo lo que este proyecto no hace en ningún sitio.

**Cuando lo tengas:** déjalo en `backend/data/raw/normativas/ley_30424.pdf`
(sustituyendo el actual), actualiza en `registry.py` el `nombre`, pon
`estado_texto="consolidado"` con su `consolidado_a`, cambia las relaciones
`modificada_por` a `en_corpus=True` si las cargas también, y sigue
[INGESTA.md](INGESTA.md). Esta sí requiere reindexar: cambia el texto.

---

## 2. Los 211 títulos truncados

`unidad.titulo` está cortado a media frase en 211 de las 701 unidades:

```
Ley 29783, Artículo 4    -> 'Objeto de la Política Nacional de'
Ley 30424, Artículo 3    -> 'Responsabilidad administrativa de las'
Reglamento 29783, Art 1  -> ''
```

**Causa:** `ingestion/parser.py:357` hace `body.split("\n", 1)[0]`, pero la capa
de texto del PDF conserva los saltos de línea **visuales** de la columna, no los
semánticos. La primera "línea" es media sumilla.

**Impacto hoy:** latente. El frontend no muestra `titulo` en ningún sitio. Pero
está en el contrato de la API (`FuenteOut.titulo`) y en ISO sí entra al
`texto_para_embedding` (`ingest.py:144`), donde degrada un poco la recuperación.

**Arreglo:** unir líneas hasta el primer corte semántico (punto, o el salto
doble que separa la sumilla del cuerpo) en vez de cortar por la primera línea
física. Ojo con las leyes que directamente no tienen sumilla —los reglamentos
de la 29733 y la 29783 son el caso— donde lo correcto es dejar `titulo` vacío,
no inventar uno.

**Y de paso:** `ingestion/validate.py` no comprueba `titulo` en absoluto. Por
eso el corpus da "0 problemas" con 211 títulos rotos. Añadir el chequeo es
tan importante como el arreglo, porque si no volverá a pasar.

---

## 3. Revisar la generación de multas

**El fallo de diseño:** `rag/multas.py:62` tiene `REGIMENES` escrito a mano en
el código, con un único régimen (protección de datos), mientras el resto del
proyecto saca todo del corpus. Los rangos deberían salir del artículo que los
fija, igual que ya se hace con la UIT, que vive en `data/uit.json` con la norma
que la establece.

Tres cosas concretas:

1. **Derivar los rangos del corpus.** Cada régimen debería apuntar a la unidad
   de la que sale su escala, no repetirla. Hoy `articulo_cita` es una cadena
   suelta —`"Ley 29733, Artículo 39"`— que nadie valida contra el corpus: si el
   artículo cambia de numeración al reingerir, la cita queda mintiendo.

2. **Falta la graduación.** La estimación devuelve el rango entero (leve = 0,5
   a 5 UIT). Lo que determina el monto dentro del rango son los criterios del
   art. 230 de la Ley 27444 —reincidencia, beneficio obtenido, intencionalidad—
   que hoy solo se mencionan en el texto de la advertencia. Es la diferencia
   entre "entre 2.750 y 27.500 soles" y una estimación útil.

3. **Solo hay un régimen.** Faltan SST y LA/FT, y no por olvido: sus escalas
   están en normas que no se han cargado (el reglamento de la Ley 29783 para
   SST, las resoluciones SBS para LA/FT). Depende de la ingesta, no del código.

**Decisión previa:** si los rangos salen del corpus, hay que decidir cómo se
localiza la unidad que los contiene. Referencia explícita por `unidad.id` en el
registro del régimen es lo más simple y lo más robusto; buscarla por embedding
sería frágil para algo que tiene que ser exacto.

---

## 4. Cotejo contra SPIJ

**Qué es.** SPIJ (Sistema Peruano de Información Jurídica, del MINJUSDH) es el
repositorio oficial de normas del Estado. "Cotejar" es comparar lo que tenemos
cargado contra esa versión oficial para confirmar tres cosas:

- que el **texto** del artículo coincide, palabra por palabra;
- que la **fecha de publicación** es la que decimos;
- que la versión es la **vigente**, y no una anterior a alguna modificatoria.

**Por qué está pendiente.** Las 5 normas tienen hoy
`metadata_verificada: false`, y `fecha_publicacion` / `url_fuente` están en
`null` salvo donde se leyeron del propio documento. Es deliberado: el registro
no afirma nada que no se haya leído de la fuente. Pero significa que **nadie ha
confirmado todavía** que el corpus refleje el derecho vigente.

Las dos urgentes son `ley_27693` y `ley_30424`: vienen de escaneo con OCR, y ahí
un error de reconocimiento puede cambiar un plazo o un monto sin que se note.

**Es trabajo manual, no de código.** Abrir SPIJ, comparar, y poner
`metadata_verificada=True` con la `url_fuente` y la `fecha_publicacion` reales
en `registry.py`. Después basta `python -m rag.index --solo-metadatos`: no
cambia ningún texto vectorizado.

---

## 5. Sin pruebas unitarias

No hay ni una en el proyecto. La verificación son `ingestion.validate` (calidad
del corpus) y `rag.eval` (recuperación), que cubren bien lo suyo pero dejan
fuera:

- los **prompts** (`answer.py:_SISTEMA`, `diagrama.py:_PROMPT`) — nada comprueba
  que el modelo siga negándose a responder fuera del corpus;
- la **anonimización** — es la pieza con más casos borde y cero cobertura;
- las **multas** — aritmética pura, trivial de probar;
- el **parser** — donde más regresiones caben.

Empezaría por anonimización y multas: son deterministas, rápidas, y no
necesitan llamar a ningún modelo.

---

## 6. El bundle del frontend

Mermaid arrastra ~1,5 MB en chunks (cytoscape, katex, todos los tipos de
diagrama). Se carga aunque el usuario nunca vea un diagrama. Un `import()`
diferido en `Mermaid.jsx` y `GrafoNormas.jsx` lo saca del arranque.

No es urgente: es una herramienta interna, no una landing.
