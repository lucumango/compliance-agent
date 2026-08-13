# Guía de uso

Para quien va a usar CARLOS en su trabajo, sin necesidad de saber cómo está
construido por dentro. Explica qué puede responder, cómo leer lo que responde y
—sobre todo— **cuándo no fiarse**.

## Qué es, en una frase

Un asistente que responde preguntas sobre normativa peruana **citando el
artículo exacto** del que sale cada afirmación, a partir de un conjunto cerrado
de normas cargadas. Si la pregunta cae fuera de esas normas, lo dice.

No es un buscador ni un chatbot general. Solo sabe lo que se le ha cargado.

## Sobre qué puedes preguntarle

| Si tu pregunta va de… | Tiene cargado | Nivel de detalle |
|---|---|---|
| **Protección de datos personales** | Ley 29733 y su reglamento | Alto — 194 artículos: consentimiento, derechos del titular, bancos de datos, multas |
| **Seguridad y salud en el trabajo** | Ley 29783 y su reglamento | Alto — 252 artículos: comité de SST, accidentes, auditorías, obligaciones del empleador |
| **Prevención de lavado de activos** | Ley de la UIF, ley de lavado, beneficiario final | Medio — 74 artículos: a quién se reporta, qué es delito, quién declara |
| **Responsabilidad de la empresa por corrupción** | Ley 30424 | ⚠️ Bajo y desactualizado — leer el aviso de abajo |
| **Sistemas de gestión antisoborno** | ISO 37001:2016 completa | Alto — 204 cláusulas, incluido el Anexo A |

En total, **754 artículos, disposiciones y cláusulas** de 8 normas.

## Cómo leer una respuesta

**Las etiquetas amarillas son las fuentes.** Cada `F1`, `F2`… que aparece en el
texto es un artículo concreto. Pasa el ratón por encima para ver cuál es, o
púlsala para abrir su texto completo abajo.

Si una afirmación no lleva etiqueta, **no está respaldada por el corpus**. Esa
es la señal más importante de toda la interfaz.

**Los avisos naranjas importan.** Cuando una respuesta se apoya en un texto
problemático —escaneado, o desactualizado— aparece un aviso arriba. No es
decorativo: te está diciendo que verifiques esa cita antes de usarla.

**"El corpus cargado no contiene una respuesta a esto"** es una respuesta
correcta, no un fallo. Significa que la norma que resolvería tu duda no está
cargada. Es preferible a que se lo invente: si le preguntas por un plazo que no
tiene, el sistema está diseñado para callarse en vez de copiar el de otro país.

## Cuándo no fiarte

Tres casos concretos, por orden de importancia.

### 1. Preguntas sobre responsabilidad de la empresa (Ley 30424)

El texto cargado es el **original de 2016**. Desde entonces la ley se modificó
dos veces y su alcance se amplió bastante.

Si preguntas *"¿por qué delitos responde una persona jurídica?"*, la respuesta
te dará el alcance de 2016 —solo cohecho transnacional— cuando hoy es mucho más
amplio. **El sistema avisa de que el texto es el original, pero no puede
decirte qué falta.**

Para cualquier consulta sobre esta ley: contrasta con la versión vigente.

### 2. Cuando el aviso dice "texto escaneado"

Ese texto se leyó de una imagen mediante reconocimiento óptico. La numeración
se comprueba automáticamente y está bien, pero puede haber errores dentro del
párrafo — y en una norma, un dígito mal leído cambia un plazo o un monto.

Hoy afecta solo a la Ley 30424.

### 3. Cuando la respuesta toca algo que no está cargado

Falta, entre otras cosas, el **reglamento de la Ley 30424**, las
**resoluciones de la SBS** sobre gestión de riesgos, y todo lo tributario,
societario, ambiental o sectorial.

El sistema no puede saber lo que no tiene. Si tu consulta cruza materias, es
posible que responda bien la parte que conoce y **no mencione que la otra mitad
existe**.

## Lo que no hace

- **No es asesoría legal.** Ninguna respuesta sustituye el criterio de un
  abogado. El valor está en llegar al artículo correcto en segundos, no en
  decidir por ti.
- **No conoce tu caso.** No sabe qué tipo de empresa eres, qué contratos tienes
  ni qué te ha pasado antes. Responde sobre la norma, no sobre tu situación.
- **No busca en internet.** Solo lee las normas cargadas.
- **No sabe si algo se derogó ayer.** El corpus se actualiza a mano, cuando
  alguien carga la norma nueva.

## Un detalle sobre datos personales

Puedes escribir consultas con datos reales del caso. Antes de enviar la
consulta al modelo, el sistema **enmascara automáticamente** los DNI, RUC,
correos, teléfonos, montos y tarjetas que detecte, y los restituye en la
respuesta.

**Pero no reconoce nombres de personas.** Si escribes "el trabajador Juan
Pérez", ese nombre sí sale del entorno. Cuando el nombre no aporte nada a la
pregunta normativa, mejor no ponerlo.

## El estimador de multas

El panel lateral calcula rangos de multa por gravedad, en soles, usando la UIT
del año en curso.

Es una **estimación de impacto, no una sanción**. Devuelve el rango que fija la
ley; el monto concreto lo gradúa la autoridad según criterios propios
(reincidencia, beneficio obtenido, intencionalidad). Hoy solo cubre protección
de datos.

## El mapa de normas

Debajo del filtro por materia hay un diagrama que muestra qué norma modifica o
reglamenta a cuál.

Lo más útil es lo que aparece **con línea discontinua**: normas que sabemos que
afectan a las cargadas pero cuyo texto no tenemos. Es el mapa de lo que le
falta al sistema, a la vista y no escondido en un documento técnico.

---

¿Echas en falta una norma? Se puede cargar: el procedimiento está en
[Cargar documentos](INGESTA.md), y el estado de cada fuente en
[Fuentes del corpus](FUENTES.md).
