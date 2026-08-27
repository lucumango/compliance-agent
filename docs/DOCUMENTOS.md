# Documentos del usuario

Qué pasa cuando alguien arrastra un PDF o un DOCX a la ventana, y por qué está
resuelto así.

## En una frase

El archivo se extrae, se trocea, se vectoriza y sus fragmentos quedan en
Postgres con dueño. A partir de ahí una consulta busca **en dos sitios a la
vez** —el corpus normativo y los documentos de quien pregunta— y la respuesta
puede citar los dos, marcándolos distinto.

## El recorrido

```
Usuario suelta Politica_Compras.pdf
   │
   ├─ 1. extraer.py       PDF -> bloques con su número de página
   │                      DOCX -> un bloque, párrafos y tablas, sin página
   │
   ├─ 2. trocear.py       bloques -> fragmentos de ~1200 caracteres
   │                      cortando por párrafo, con 150 de solape
   │
   ├─ 3. gemini.py        embed_batch(fragmentos) -> vectores de 3072 dims
   │
   └─ 4. nube.py          INSERT en documento_fragmentos, con el token del
                          usuario: row level security decide, no el servidor
```

Y en cada consulta:

```
consulta
   │
   ├─ embed_query(consulta)  ->  UN vector
   │        │
   │        ├─ retrieval.py    producto punto contra el corpus     -> 6 [F]
   │        └─ documentos.py   RPC buscar_fragmentos en Postgres   -> 4 [D]
   │
   └─ answer.py    ambas listas al prompt, con etiquetas separadas
```

## Las cuatro decisiones que no son obvias

### 1. Cuotas separadas, no un ranking único

Corpus y documentos **no compiten por las mismas plazas**. Se piden 6 del uno y
4 del otro, y cada cual trae los suyos.

Un ranking común ordenaría ambos por el mismo score, y ahí los fragmentos del
usuario salen ganando por construcción: son más largos que un artículo, están
escritos en lenguaje de empresa —que es el lenguaje en el que la gente
pregunta— y no en lenguaje legislativo. El resultado sería que la política
interna desplaza al artículo de la ley justo en las consultas donde la ley es
lo que hace falta.

La cuota fija cuesta algo de precisión en las consultas que solo tocan un lado.
Compra que la respuesta nunca se quede sin la norma.

### 2. Etiquetas distintas, y un umbral

`[F1]` es una norma. `[D1]` es un documento del usuario. La regla 2 del prompt
—en `rag/answer.py`— obliga al modelo a no presentar una como la otra, y si
ambas hablan de lo mismo y difieren, a decirlo.

Además los fragmentos del usuario llevan un **umbral de similitud** que el
corpus no lleva. Sin él, alguien con un solo documento recibe siempre sus
cuatro fragmentos menos malos aunque la consulta no tenga nada que ver, y el
modelo los cita porque están ahí.

### 3. En Postgres, no en el índice numpy

El corpus vive en un `numpy.ndarray` en memoria y funciona muy bien: es común a
todos y se reconstruye entero cuando cambia.

Los documentos del usuario tienen dueño. Meterlos en ese mismo array obligaría
a filtrar por usuario en cada búsqueda, y **un filtro que se olvida una vez
filtra los documentos de un cliente a otro**. En Postgres el aislamiento es una
política de row level security que no depende de que nadie se acuerde.

### 4. Sin índice ANN, a propósito

La columna es `vector(3072)`, las dimensiones de `gemini-embedding-2`, para que
el vector de la consulta sirva igual contra el corpus y contra los fragmentos.

`ivfflat` y `hnsw` admiten hasta 2000 dimensiones, así que esa tabla **no lleva
índice** y se barre entera. A esta escala —decenas de documentos por usuario—
son milisegundos. Reducir la dimensión para poder indexar haría incomparables
los scores con los del corpus, que es peor que barrer.

Si algún día un usuario llega a cientos de miles de fragmentos, hay que reducir
dimensión **en los dos lados a la vez**, no solo aquí.

## Límites que conviene conocer

- **No hay OCR.** Un escaneo sin capa de texto se rechaza con un mensaje que lo
  dice. Tesseract es un binario del sistema y triplicaría el tamaño de la
  imagen de despliegue para un caso que el usuario puede resolver antes de
  subir.
- **Solo PDF y DOCX.** Un XLSX no se admite, y no por falta de tiempo: una
  tabla de miles de filas vectorizada recupera filas parecidas a la pregunta,
  que es justo lo que no sirve. Para contar hace falta consultar, no recuperar.
- **La subida es síncrona.** Un documento grande puede tener a la petición
  varios segundos. Un trabajo en segundo plano necesitaría una cola y un sitio
  donde dejar el archivo mientras espera.
- **El original no se guarda.** Se conserva el texto troceado, no el archivo.
  Volver a necesitarlo significa volver a subirlo.
- **Tope de 1000 fragmentos por documento**, y 20 MB por archivo.
- **La anonimización no cubre lo que se sube.** `anonimizar.py` enmascara la
  consulta antes de llamar al modelo; el contenido del documento va tal cual.
  Un documento con datos personales los manda a Gemini al ser vectorizado.
