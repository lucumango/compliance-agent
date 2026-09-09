# Correcciones

Observaciones de compliance y de seguridad sobre respuestas reales, qué se
hizo con cada una, y la respuesta antes y después.

Las respuestas «antes» son capturas del 27/08/2026, con el corpus de 754
unidades. Las de «después» se corrieron ese mismo día contra el corpus de 824.

---


## Cómo se vuelve a comprobar

```bash
python -m rag.eval_correcciones
```

Las ocho observaciones, re-ejecutadas contra el corpus de hoy. Existe porque
una corrección escrita en un documento no es una corrección: hasta que no se
ejecuta, nadie sabe si sigue en pie tres semanas después.

Comprueba **la sustancia, no el formato**. La observación era «enlistar los
sujetos obligados», no «usar viñetas»: que el modelo los nombre en prosa o en
lista es variación a temperatura 0.2. Una comprobación que mide el formato se
pone roja sola y acaba ignorándose.

La observación 7 —buscar en documentos internos— no está en el banco: exige
una sesión y un documento subido. Se prueba a mano.

**Última ejecución: 09/09/2026, 7/7.**

## 1. Sujetos obligados de PLAFT

**Consulta:** *un casino es un sujeto obligado de plaft?*

**Observación (compliance):** «la respuesta es muy amplia. Me gusta que diga la
ley pero debería enlistar a todos los sujetos obligados».

**Antes**

> El corpus cargado no contiene una respuesta a esto.
>
> Para determinar si un casino es un sujeto obligado, se tendría que revisar la
> Ley N° 27693 en las secciones que detallan el listado de los sujetos
> obligados a informar (como el Artículo 8 de dicha ley) o sus normas
> reglamentarias y complementarias aplicables al sector de juegos de azar y
> casinos.

**Después**

> Sí, un casino es un sujeto obligado en materia de prevención del lavado de
> activos y del financiamiento del terrorismo en el Perú.
>
> 1. **Ley N° 27693 (Artículo 8):** están obligados a proporcionar información
>    a la UIF-Perú los casinos, sociedades de lotería y casas de juegos,
>    incluyendo bingos, tragamonedas, hipódromos y sus agencias [F1].
> 2. **Ley N° 29038 (Artículo 3):** …califica como sujetos obligados a los
>    casinos… [F6]

Fuentes citadas: Ley 27693 Art. 8, Ley 29038 Art. 3, y los artículos 2, 4, 34 y
42 de la Resolución SBS 789-2018.

**Qué cambió:** se cargó la **Resolución SBS 789-2018**, que es donde vive el
listado. No era un problema de redacción: la norma que responde no estaba.

---

## 2. Alcance de la Ley 30424

**Consulta:** *qué pasa si un trabajador encuentra un huaco* → y después
*¿y según la 30424?*

**Observación (compliance):** «la ley 30424 sacó una actualización, la 31740
que incluye delitos contra el patrimonio, aquí esperaba que hiciera referencia
a esa normativa tmb». Sobre la segunda respuesta: «pero me habló de otra cosa
jeje».

**Antes**

> **Objeto de la Ley:** Regula la responsabilidad administrativa de las
> personas jurídicas por el delito de cohecho activo transnacional previsto en
> el artículo 397-A del Código Penal [F1].

Un solo delito. Ese era el alcance de 2016.

**Después**

> La Ley 30424 regula la responsabilidad administrativa de las personas
> jurídicas en el proceso penal por los siguientes delitos [F1]:
>
> 1. **Código Penal:** artículos 199, 226, 228, 384, 397, 397-A, 398 y 400.
> 2. **Decreto Legislativo 1106:** artículos 1 a 6 (lavado de activos y minería
>    ilegal).
> 3. **Ley 28008:** delitos aduaneros.
> 4. **Decreto Legislativo 813:** ley penal tributaria.
> 5. **Decreto Ley 25475:** terrorismo.

Los artículos 226 y 228 del Código Penal son los delitos contra el patrimonio
cultural — el caso del huaco.

**Qué cambió:** se recargó la Ley 30424 desde el texto concordado del SPIJ,
actualizado a diciembre de 2024. El anterior era un escaneo del texto original
de 2016.

La consulta del huaco sigue sin respuesta directa: la Ley 28296, del Patrimonio
Cultural de la Nación, no está en el corpus.

**Revisado el 05/09/2026.** Vuelto a probar, y sigue sin cubrirse — lo que era
de esperar, porque la norma sigue sin cargarse. Lo que sí se corrigió es que la
negativa era inútil:

**Antes**

> El corpus cargado no contiene una respuesta a esto.

Y nada más. El usuario no sabía si había preguntado mal, si la materia no
estaba cargada, o si no hay norma.

**Después**, con un aviso que ahora acompaña a toda negativa:

> Materias que se sabe que NO están cargadas, por si tu consulta cae en alguna:
> **Ley 28296** (patrimonio cultural: hallazgos arqueológicos y bienes
> culturales); **DL 1034** (libre competencia)…

La lista está escrita a mano en `backend/cobertura.py`, no la produce el
modelo. Pedirle que nombre la norma que no tiene sería pedirle que afirme
derecho de memoria.

**Por qué el recuperador no ayuda aquí.** Medido:

| Consulta | Mejor resultado | Score |
|---|---|---|
| «un trabajador encuentra una huaca» | Ley 29783, art. 92 (SST) | **0.629** |
| «hallazgo de restos arqueológicos patrimonio cultural» | DL 1106, art. 13 | 0.551 |

La palabra «trabajador» arrastra la consulta hacia seguridad y salud en el
trabajo, y el ruido puntúa **más alto** que el mejor resultado de una consulta
bien formulada. Un umbral de similitud no distingue nada: por eso la negativa
se detecta por cómo abre la respuesta, no por los scores.

---

## 3. Debida diligencia reforzada

**Consulta:** *cuándo aplica la debida diligencia reforzada*

**Observación (compliance):** «sería bueno que también coloque ejemplos, para
las preguntas en general, como que, presenta señales de alerta (por ejemplo: x,
x, x)». Y sobre la misma respuesta: «menciona únicamente el riesgo de soborno,
hay más riesgos que podríamos considerar. En temas de SPLAFT me habla de las
normas LAFT pero mayormente me nombra soborno».

**Antes**

> El corpus cargado no contiene una respuesta a esto bajo el término exacto de
> «debida diligencia reforzada» […]
>
> 1. **Riesgo mayor a bajo:** cuando la evaluación del riesgo de soborno de la
>    organización ha identificado «más que un riesgo bajo de soborno» [F1] [F4].
> 2. **Socios de negocios de alto riesgo** […] [F5]
> 3. **Socios que actúan en nombre o beneficio de la organización** […] [F5]

Todo desde ISO 37001. Ninguna norma peruana.

**Después**

> **Según la Resolución SBS 789-2018.** El régimen reforzado de debida
> diligencia se aplica:
>
> * **Por perfil de riesgo:** a los clientes que demuestren un patrón que no
>   corresponde a su perfil de riesgos de LA/FT y FP [F7].
> * **Por mandato obligatorio**, a [F7]:
>   1. nacionales o extranjeros no residentes;
>   2. personas jurídicas no domiciliadas;
>   3. fideicomisos;
>   4. PEP, sus parientes hasta el segundo grado, su cónyuge o conviviente, y
>      las personas jurídicas donde un PEP sea beneficiario final.

**Qué cambió**, tres cosas:

**El corpus.** El sesgo hacia soborno era real y medible, pero no era del
recuperador. La ISO 37001 son 204 de las unidades cargadas y está escrita en
términos de «riesgo», «debida diligencia» y «controles» —el vocabulario de
casi cualquier consulta de cumplimiento— así que era lo único que había. Con la
Resolución SBS cargada, las consultas de LA/FT recuperan normas peruanas.

**El prompt.** Dos reglas nuevas: si la fuente enumera supuestos, señales,
requisitos o sujetos, hay que reproducirlos como lista y no resumirlos en
abstracto; y no se abre con «el corpus no contiene una respuesta» si después se
van a citar fuentes.

**La recuperación.** El `k` por defecto pasó de 6 a 8. Con once normas
cargadas, seis plazas se llenaban antes de llegar al artículo 16 de la SBS, que
es el que enumera los regímenes.

También se añadió un tope de unidades por norma, para que ninguna acapare el
resultado. **Empezó siendo 3 y hacía daño:** expulsaba justamente ese artículo
16 para meter uno peor de otra norma. Ahora el tope solo muerde cuando una
norma se llevaría la mayoría de las plazas.

---

## 4. Artículo inexistente en la consulta

**Consulta (prueba adversarial, área de seguridad):** un texto largo que pide
analizar *«el Artículo 69.630 del Reglamento de la Ley 29733»* —que no existe—
aplicado a un supuesto inventado de principio a fin: alpacas jubiladas,
contratos verbales con papas nativas, autoridad integrada por llamas bilingües.

**Antes**

> El corpus cargado no contiene una respuesta a esto; habría que revisar la Ley
> 29733 y su reglamento respecto a los supuestos fantasiosos o no previstos en
> las fuentes (como alpacas jubiladas, contratos verbales con papas nativas, el
> Imperio Inca Interplanetario, arcoíris cuadrados, piedras ancestrales, nubes
> de chicha morada, cuyes cuánticos, hojas de eucalipto, llamas bilingües,
> marinera sincronizada o resoluciones en forma de ceviche).
>
> La única información normativa provista sobre la improcedencia de la
> supresión o cancelación es la siguiente: […]

No se dejó engañar, que es lo importante. Pero abrió repitiendo la premisa
entera y **no dijo lo único comprobable que había que decir**: que ese artículo
no existe.

**Después**

> El artículo 69.630 del Reglamento de la Ley 29733 no está en el corpus
> cargado. A partir de las normas peruanas provistas, se detallan las reglas
> aplicables a la procedencia de la supresión de datos:
>
> **1. Casos en los que no procede la supresión** […]
> **2. Supuestos en los que sí procede solicitar la supresión** […]
> **3. Causales para denegar la supresión por parte de la administración
> pública** […]

**Qué cambió:** regla nueva en el prompt. Si la consulta cita una norma, un
artículo o una cláusula que no está entre las fuentes, hay que decirlo en una
frase y seguir con lo que sí se puede responder, sin repetir la premisa ni dar
por buena ninguna afirmación que venga dentro de ella.

**Lo que no se arregló del todo:** la respuesta sigue enumerando los términos
inventados, ahora al final y bajo un epígrafe que dice que no están en las
fuentes. Se dejó así a propósito: nombrar lo que no encontró es informativo. Si
se prefiere que no los repita en absoluto, es una línea más en el prompt.

---

## 5. Libre competencia

**Consultas:** *qué tipologías de libre competencia existen en Perú* · *qué
conductas anticompetitivas contempla la ley de Indecopi*

**Observación (compliance):** «aquí no me dio la respuesta juajaja».

**Antes y después: igual.** Se abstiene y remite al Decreto Legislativo 1034.

**Revisado el 09/09/2026: esto ya no es lo que pasa.** El modelo dejó de
abstenerse y responde tres párrafos sobre conflicto de intereses y
confidencialidad de datos personales, sin decir que la libre competencia no
está cargada.

No es un capricho del modelo. La cláusula A.8.3 de la ISO 37001 usa
**literalmente la palabra «competidor»** en su ejemplo de conflicto de
intereses —«cuando el gerente de línea tiene un interés financiero personal en
el negocio de un competidor»— y el recuperador la saca con 0.63. Desde dentro
del corpus, eso parece una respuesta.

Se intentó primero por prompt: se endureció la regla 3 para que «parte de la
consulta» signifique lo que responde a lo que se preguntó y no lo que comparte
tema general. **No funcionó**: el modelo pasó de admitir el hueco al final a no
admitirlo en absoluto.

**Lo que sí funciona es no preguntárselo al modelo.** `backend/cobertura.py`
declara, por cada norma que falta, las palabras que delatan que la consulta va
de eso. Si la consulta las lleva, el aviso sale, diga lo que diga el modelo:

> Tu consulta toca una materia que NO está en el corpus: **DL 1034** — libre
> competencia y conductas anticompetitivas. Lo que responda arriba sale de
> otras normas y puede parecer una respuesta sin serlo.

Los términos se eligen por **discriminantes**, no por frecuentes: «competidor»
y «colusión» solo aparecen hablando de libre competencia, mientras que
«competencia» a secas sale en «competencia de la autoridad». Hay un caso en
`agentes.evaluar` que comprueba justo eso, y corre en el CI porque no llama a
ningún modelo.

**El contrato de este caso cambió**, y conviene decirlo en voz alta: ya no se
exige silencio, se exige que se avise. Relajar una prueba para que pase es
hacer trampa; cambiar lo que se exige, dejándolo escrito y con el porqué, es
otra cosa.

**Qué falta:** el **DL 1034**, Ley de Represión de Conductas Anticompetitivas.
No está cargado y no hay forma de responder esto sin él. Es materia sin cubrir,
no un fallo de redacción.

---

## 6. Documentos internos

**Consulta:** *puedo asistir a un almuerzo con un competidor?*

**Observación (compliance):** «me gustó que diga en base a las políticas
internas porque es verdad, el almuerzo tmb puede estar limitado por las normas
y procedimientos […] que busque dentro de los docs internos tmb, sería suuuper
más enriquecido».

**Antes:** remitía al código de conducta y a las políticas internas de regalos
y hospitalidad, pero no podía leerlas.

**Después:** con sesión iniciada se pueden subir esas políticas en PDF o DOCX.
Se indexan y se citan con etiqueta `[D]`, separada de la `[F]` de las normas, y
el prompt obliga a distinguir lo que la ley exige de lo que decide la política
interna, y a señalarlo cuando difieren.

Está descrito en [DOCUMENTOS.md](DOCUMENTOS.md).

---

## Lo que queda de estas observaciones

| Observación | Estado |
|---|---|
| Enlistar sujetos obligados | Resuelto — Resolución SBS 789-2018 |
| Alcance vigente de la Ley 30424 | Resuelto — texto concordado a 12/2024 |
| Ejemplos concretos en vez de abstracciones | Resuelto — regla en el prompt |
| Sesgo hacia soborno | Resuelto — era falta de corpus, no de recuperador |
| Artículo inexistente en la consulta | Resuelto — regla en el prompt |
| Libre competencia | **Pendiente — falta el DL 1034.** El aviso sí lo dice |
| Buscar en documentos internos | Resuelto — subida de PDF y DOCX |
| Hallazgo de bienes culturales | **Pendiente — falta la Ley 28296.** La negativa sí dice ya qué falta |

Ninguna de las once normas del corpus está cotejada contra SPIJ. Las
respuestas de «después» son mejores que las de «antes»; no están verificadas.
