# Pendiente

Lo que falta, con el contexto para retomarlo sin releer el código. Ordenado por
lo que yo atacaría primero.

Estado al 27/08/2026: 824 unidades, 11 normas, `validate` sin problemas,
`rag.eval` 12/12.

---

## 1. Cotejo contra SPIJ

**Ninguna de las once normas está cotejada.** `metadata_verificada` es `false`
en todas, y `fecha_publicacion` y `url_fuente` están en `null` salvo donde se
leyeron del propio documento.

Es deliberado —el registro no afirma nada que no se haya leído de la fuente—
pero significa que nadie ha confirmado que el corpus refleje el derecho
vigente.

Cotejar es comparar contra la versión oficial de SPIJ y confirmar tres cosas:

- que el **texto** del artículo coincide palabra por palabra;
- que la **fecha de publicación** es la que decimos;
- que la versión es la **vigente**.

Las tres que entraron el 27/08 no las ha mirado nadie: DS 016-2024-JUS, DS
003-2019-EF y Resolución SBS 789-2018.

**Es trabajo manual, no de código.** Abrir SPIJ, comparar, y poner
`metadata_verificada=True` con la `url_fuente` y la `fecha_publicacion` reales
en `registry.py`. Después basta `python -m rag.index --solo-metadatos`: no
cambia ningún texto vectorizado.

---

## 2. El orquestador

**Hecho el 04/09/2026: cada agente es ya una entidad propia.** CARLOS y DIEGO
tienen corpus, alcance declarado, reglas y casos de evaluación en
`backend/agentes/`, y `python -m agentes.evaluar --alcance` comprueba que cada
uno responde lo suyo y rechaza lo ajeno. Ver [AGENTES.md](AGENTES.md).

Lo que falta es el paso siguiente: que el usuario mande un caso sin elegir
agente y el motor decida a quién va —a uno, a los dos, o a ninguno— y sepa
componer una respuesta de varios diciendo qué parte vino de quién.

Ahora sí se puede: hay dos alcances declarados contra los que enrutar, y casos
que dicen qué debe rechazar cada uno. Enrutar entre cosas definidas ya no es
enrutar al azar.

IVÁN y ELENA siguen sin corpus, y sin corpus no hay agente.

---

## 3. Los títulos truncados, y el control que no los detecta

`unidad.titulo` está cortado a media frase en buena parte del corpus:

```
Ley 29783, Artículo 4    -> 'Objeto de la Política Nacional de'
Reglamento 29783, Art 1  -> ''
```

**Causa:** `ingestion/parser.py` hace `body.split("\n", 1)[0]`, pero la capa de
texto del PDF conserva los saltos de línea **visuales** de la columna, no los
semánticos. La primera "línea" es media sumilla.

**Impacto:** latente. El frontend no muestra `titulo`. Pero está en el contrato
de la API (`FuenteOut.titulo`) y en ISO sí entra al `texto_para_embedding`,
donde degrada la recuperación.

**Arreglo:** unir líneas hasta el primer corte semántico en vez de cortar por
la primera línea física. Ojo con las normas que no tienen sumilla —los
reglamentos de la 29733 y la 29783— donde lo correcto es dejar `titulo` vacío.

**Y de paso:** `ingestion/validate.py` no comprueba `titulo` en absoluto. Por
eso el corpus da "0 problemas" con los títulos rotos. Añadir el chequeo importa
tanto como el arreglo.

---

## 4. El estimador de multas

**El fallo de diseño:** `rag/multas.py` tiene `REGIMENES` escrito a mano en el
código mientras el resto del proyecto saca todo del corpus.

Tres cosas:

1. **Derivar los rangos del corpus.** Hoy `articulo_cita` es una cadena suelta
   —`"Ley 29733, Artículo 39"`— que nadie valida: si el artículo cambia de
   numeración al reingerir, la cita queda mintiendo. Referencia explícita por
   `unidad.id` es lo más simple y lo más robusto.
2. **Falta la graduación.** Devuelve el rango entero. Lo que determina el monto
   son los criterios del art. 230 del TUO de la Ley 27444, que no está cargado.
3. **Solo hay un régimen de tres.** Falta SST, y falta LA/FT — este último ya
   se puede intentar, con la Resolución SBS cargada.

---

## 5. Sin pruebas unitarias

No hay ninguna. `ingestion.validate` cubre la calidad del corpus, `rag.eval` la
recuperación y `rag.eval_prompt` seis de las ocho reglas del prompt. Queda
fuera:

- las **reglas 2 y 6 del prompt** — no confundir norma con política interna, y
  no dar asesoría. Son de matiz: una comprobación que dependa de otro modelo
  para juzgar convierte un fallo en una discusión, así que se leen a mano;
- la **anonimización** — la pieza con más casos borde y cero cobertura;
- las **multas** — aritmética pura, trivial de probar;
- el **parser** — donde más regresiones caben, y donde más se ha tocado.

Empezaría por anonimización y multas: deterministas, rápidas, sin llamar a
ningún modelo.

---

## 6. Corpus que falta

- **Reglamento de la Ley 30424** (DS 002-2019-JUS y DS 002-2025-JUS).
- **ISO 37002** y el **régimen laboral de hostilidad** — lo mínimo para el
  agente de línea ética.
- **DL 1034** — libre competencia.
- **TUO de la Ley 27444** — lo necesita el estimador de multas.
- **Normativa sectorial** — la rama `05_Sectorial/` existe y está vacía. Se
  carga por encargo.

**El Código Penal y el Procesal Penal quedan fuera** (03/09/2026). CARLOS
responde sobre obligaciones administrativas, no tipifica delitos. Los tipos que
importan ya están en el artículo 1 de la Ley 30424, que sí está cargado. Ver
[FUENTES.md](FUENTES.md).

---

## 7. El bundle del frontend

Mermaid arrastra ~1,5 MB en chunks y se carga aunque el usuario nunca vea un
diagrama. Un `import()` diferido en `Mermaid.jsx` y `GrafoNormas.jsx` lo saca
del arranque.

No es urgente: es una herramienta interna, no una landing.
