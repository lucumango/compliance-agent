# Los agentes

Dos hoy: **CARLOS** para compliance y **DIEGO** para debida diligencia. Sobre el
mismo motor, el mismo índice y la misma disciplina de citación.

Hasta ahora la única diferencia entre materias era una casilla de filtro. Eso no
es un agente: es una consulta con menos corpus. Un agente son cuatro cosas, y
las cuatro viven en `backend/agentes/`.

| | Su corpus | Su alcance | Sus reglas | Sus casos |
|---|---|---|---|---|
| **CARLOS** | Las 824 unidades | Obligaciones normativas de una organización | Las nueve comunes | 4 |
| **DIEGO** | 132 unidades, materia `laft` | Debida diligencia de clientes, proveedores y contrapartes | Las nueve, más tres suyas | 7 |

Lo cuarto es lo que impide que un agente sea una etiqueta. **Un agente sin casos
que comprueben su alcance no tiene alcance: tiene una intención.**

Va antes que el orquestador a propósito. Enrutar entre cosas que no están
definidas es enrutar al azar.

---

## DIEGO

**Due dIligence, Evaluation & Governance Operator**

**Responde:** qué información hay que obtener de un cliente, un proveedor o una
contraparte; qué régimen le corresponde —general, reforzado o simplificado—;
cuándo escala; cómo se identifica al beneficiario final; y qué hay que conservar
y por cuánto tiempo.

**No responde:** no consulta registros. No tiene acceso a SUNAT, SUNARP, el RNP,
el RNSSC ni a las listas OFAC, ONU, UE o HMT. Dice qué hay que consultar en cada
una y por qué; no dice qué aparece en ellas. Y no emite un veredicto sobre si un
tercero es aceptable: eso lo decide una persona con el expediente delante.

Sus tres reglas propias, además de las nueve comunes:

1. **Distinguir lo que la norma exige de lo que es buena práctica.** Si algo no
   sale de una fuente, no es un requisito.
2. **El vocabulario interno no es el de la norma.** El manual de la firma habla
   de diligencia *básica, mejorada y reforzada*; la Resolución SBS 789-2018
   nombra **general, reforzado y simplificado**. Manda el de la norma, y la
   equivalencia se dice en voz alta.
3. **Ante un tercero concreto, responde qué verificar y dónde**, no si está
   limpio.

### El corpus ya estaba

Las cuatro normas de la materia entraron con el corpus de LA/FT y no hizo falta
cargar nada: DL 1106, Ley 27693, Ley 29038, DL 1372, DS 003-2019-EF y la
Resolución SBS 789-2018.

### Su filtro es una frontera, no una sugerencia

El corpus del agente y el filtro de la interfaz se **intersecan**. Si el filtro
pudiera ampliar el corpus del agente, el alcance declarado dejaría de ser una
frontera. Una intersección vacía devuelve cero fuentes, y por tanto una
negativa — que es la respuesta correcta a *"contéstame de esto que no es lo
tuyo"*.

Es lo que hace pasar este caso:

```
DIEGO · alcance
  ok  rechaza: ¿Cada cuánto deben hacerse las auditorías del sistema de gestión de SST?
```

La Ley 29783 está en el índice y CARLOS la contesta. DIEGO no la ve.

---

## El cuestionario de debida diligencia

`POST /api/diego/cuestionario`. **No pasa por el modelo.** Es una tabla de
decisión sobre el artículo 16 de la Resolución SBS 789-2018, igual que el
estimador de multas lo es sobre los rangos de sanción: la misma entrada da la
misma salida, y cada requisito trae el inciso del que sale.

Entra el tipo de contraparte —persona natural, persona jurídica o proveedor— y
los hechos que ya se conocen. Sale el régimen, la información mínima exigida
artículo por artículo, y lo que se pide por práctica.

### Lo que la norma obliga, y lo que decide la firma

Los seis detonadores del artículo 16.2.2 obligan a escalar al régimen reforzado,
y cada uno lleva su inciso:

| Detonador | Base |
|---|---|
| Nacional o extranjero no residente | art. 16.2.2 (1) |
| Persona jurídica no domiciliada | art. 16.2.2 (2) |
| Fideicomiso | art. 16.2.2 (3) |
| PEP, pariente hasta 2.º grado, cónyuge o conviviente, o persona jurídica donde un PEP es beneficiario final | art. 16.2.2 (4) |
| Investigado por lavado de activos, delito precedente o financiamiento del terrorismo | art. 16.2.2 (5) |
| Vinculado a persona investigada o procesada por esos delitos | art. 16.2.2 (6) |

Los cuatro del manual de la firma —país de riesgo, contacto con gobierno, monto,
UBO opaco— **no escalan por norma**. Van marcados como criterio interno y sin
cita, porque no la tienen. Si solo se marcan estos, el cuestionario dice que el
régimen legal sigue siendo el general y que aplicar algo más exigente es
decisión de la firma, que conviene dejar escrita como tal.

Es la misma distinción que entre una fuente `[F]` y una `[D]`, y por el mismo
motivo: **acabar exigiéndole a un cliente como ley lo que era criterio propio es
el error que sale caro.**

### El simplificado no se deduce

El artículo 16.3 lo describe como una reducción de requisitos, pero quién puede
acogerse depende del Título II, que va por tipo de sujeto obligado. El
cuestionario no lo asigna nunca: dice que existe y que hay que mirarlo.

---

## Evaluación

```bash
python -m agentes.evaluar              # recuperación y citas: gratis
python -m agentes.evaluar --alcance    # añade la frontera: llama al modelo
```

Tres controles:

**Recuperación.** Que cada consulta de su materia recupere el artículo que la
responde, con SU filtro puesto. Un agente que no encuentra lo suyo no tiene
corpus, tiene acceso a uno.

**Citas.** Que cada artículo que el cuestionario menciona exista en el índice.
Determinista y gratis, así que entra en el CI. Encontró un fallo el primer día:
los identificadores estaban escritos como `res_sbs_789_2018::norma::art_16` y el
prefijo real es `::ley::`. Un cuestionario que cita una unidad inexistente es
exactamente el fallo que este proyecto no se permite.

**Alcance.** Que responda lo suyo y **rechace lo ajeno**. El segundo es el que
importa.

Estado al 05/09/2026: **11/11**.

### El aprobado falso del 04/09

El primer 11/11 no era bueno. El caso «¿está sancionada la empresa X?» pasaba
por un fallo del propio banco: el modelo agrupa las citas —escribe
`[F1, F2, F3]` tanto como `[F1]`— y la expresión regular solo casaba la forma
suelta, así que la comprobación creía que la respuesta no citaba nada, deducía
«se ha negado» y la daba por buena.

Al arreglar la regex el caso se puso rojo, y lo que destapó era real. DIEGO
abría así:

> El artículo 32 de la Resolución SBS 789-2018 establece que la SBS ejerce la
> facultad sancionadora por el incumplimiento de… [F1]

Más abajo sí decía que no tiene acceso a registros, pero **abría con un muro de
artículos que parece una respuesta**. Quien lo lea deprisa se lleva la
impresión de que se comprobó algo sobre esa empresa concreta.

La regla 12 pasó a exigir que la frase «no tengo acceso a ningún registro» vaya
**primero**, antes de cualquier artículo. Eso movió la versión de prompt de
DIEGO —`1a8fcab4` → `59cd7032`— y no la de CARLOS, que es lo que ese
identificador existe para dejar ver.

**Un banco de pruebas que aprueba por el motivo equivocado es peor que no
tenerlo**, porque además da confianza.

### El filtro no basta: hay que decir que no

Revisando el 09/09 salió el mismo patrón en DIEGO. Preguntado por auditorías de
seguridad y salud en el trabajo, abría con el artículo 34 de la Resolución SBS
—que habla de auditorías, pero del SPLAFT—. La respuesta era correcta en lo que
decía y engañosa en lo que parecía.

La causa es estructural, no de materia: **con el filtro puesto el recuperador
siempre devuelve algo.** Sus ocho mejores dentro de su corpus, aunque la
consulta sea de otra cosa. Un agente acotado nunca ve un resultado vacío, así
que nunca tiene la señal obvia de que no le toca.

Por eso la regla la genera `Agente.bloque_prompt()` automáticamente para todo
agente con `materias` acotadas, en vez de escribirla a mano en cada uno: si la
causa es el filtro, la regla va donde está el filtro. Todo agente futuro con
corpus propio la hereda sin que nadie se acuerde.

CARLOS no la lleva, y es correcto: su corpus es el índice entero, así que
quedarse sin fuentes sí significa algo para él.

---

## Cada agente tiene su versión de prompt

Dos agentes sobre el mismo `_SISTEMA` no comparten prompt: uno lleva reglas que
el otro no. Guardar la misma versión para los dos haría que el campo dijera
menos de lo que promete, así que el hash cubre las dos partes.

Los identificadores vivos están en `/api/agentes`; escribirlos aquí a mano
garantiza que queden viejos a la primera edición del prompt.

Cada respuesta guarda la suya, junto con el agente y el modelo que la produjo.
Ver [GOBERNANZA.md](GOBERNANZA.md).

---

## Los que faltan

**IVÁN** (investigación) y **ELENA** (línea ética) no están porque su corpus no
lo está. Un agente sin corpus responde de memoria, que es justo lo que este
sistema existe para no hacer.

ELENA además no es un agente más: es el único que recibiría datos de un
denunciante, con expectativa de confidencialidad y a menudo de anonimato. Eso
impone requisitos que no se añaden después. Conviene que sea el último en
construirse y el primero en diseñarse.

---

## Lo que este trabajo NO incluye

Consultar SUNAT, SUNARP, el RNP, el RNSSC y las listas restrictivas. Cada una es
un conector, algunas sin API y con captcha. Eso no es prompt, es integración, y
merece su propia decisión.

La ficha RUC de SUNAT es la candidata obvia para el primero: la condición de
"no habido" es gratuita, pública e instantánea, y es la primera consulta que se
hace antes de pedirle nada al tercero.
