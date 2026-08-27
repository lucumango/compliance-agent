# Guía de uso

Para quien va a usar CARLOS, sin necesidad de saber cómo está
construido por dentro. Explica qué puede responder, cómo leer lo que responde y
cuándo no fiarse.

## Qué es

Responde preguntas sobre normativa peruana **citando el artículo exacto** del
que sale cada afirmación. Solo lee las normas que tiene cargadas. Si la
pregunta cae fuera, lo dice.

Con cuenta iniciada, además: guarda tus conversaciones, y puedes subir tus
propios documentos —políticas, contratos, manuales— para que los contraste con
la norma.

## Sobre qué puedes preguntarle

| Si tu pregunta va de… | Tiene cargado | Detalle |
|---|---|---|
| **Protección de datos personales** | Ley 29733 y su reglamento vigente (DS 016-2024-JUS) | 203 unidades: consentimiento, derechos del titular, bancos de datos, notificación de brechas, multas |
| **Seguridad y salud en el trabajo** | Ley 29783 y su reglamento | 252 unidades: comité de SST, accidentes, auditorías, obligaciones del empleador |
| **Prevención de lavado de activos** | Ley de la UIF, ley de lavado, beneficiario final y su reglamento, norma SBS de sujetos obligados | 132 unidades: a quién aplica el régimen, qué se reporta, quién declara el beneficiario final |
| **Responsabilidad de la empresa por corrupción** | Ley 30424 concordada a diciembre de 2024 | 33 unidades: alcance, modelo de prevención, sanciones |
| **Sistemas de gestión antisoborno** | ISO 37001:2016 completa | 204 cláusulas, incluido el Anexo A |

En total, **824 artículos, disposiciones y cláusulas** de 11 normas.

## Cómo leer una respuesta

**Las etiquetas amarillas son las fuentes.** Cada `F1`, `F2`… que aparece en el
texto es un artículo concreto. Pasa el ratón por encima para ver cuál es, o
púlsala para abrir su texto completo abajo.

Si una afirmación no lleva etiqueta, **no está respaldada por el corpus**. Esa
es la señal más importante de toda la interfaz.

**Las etiquetas grises son tus documentos.** Los `D1`, `D2`… salen de lo que tú
subiste, no de la ley. La respuesta lo separa: qué exige la norma y qué dice tu
política. Si las dos hablan de lo mismo y difieren, lo señala.

Una política interna no obliga a nadie más que a tu organización. El sistema
no la presenta como norma, y tú tampoco deberías.

**Los avisos naranjas importan.** Aparecen cuando una respuesta se apoya en un
texto que conviene contrastar antes de usarlo.

**"El corpus cargado no contiene una respuesta a esto"** es una respuesta
correcta, no un fallo. Significa que la norma que resolvería tu duda no está
cargada. Es preferible a que se lo invente: si le preguntas por un plazo que no
tiene, el sistema está diseñado para callarse en vez de copiar el de otro país.

## Cuándo no fiarte

### 1. Ninguna norma está cotejada

Las once vienen de PDF oficiales, pero nadie ha comparado todavía el texto
cargado contra SPIJ ni ha confirmado que sea la versión vigente. El corpus
valida bien —sin huecos ni duplicados— y eso no es lo mismo que estar
verificado.

Para una cita que vaya a un entregable: ábrela en SPIJ y confírmala.

### 2. Cuando la respuesta toca algo que no está cargado

Falta, entre otras cosas, el reglamento de la Ley 30424, las resoluciones de la
SBS sobre gestión de riesgos, el Código Penal, la libre competencia, y todo lo
tributario, societario, ambiental y sectorial.

Si tu consulta cruza materias, puede responder bien la parte que conoce y **no
mencionar que la otra mitad existe**.

### 3. El corpus no sabe qué pasó ayer

Se actualiza a mano, cuando alguien carga la norma nueva. Una modificatoria
publicada esta semana no está.

## Lo que no hace

- **No es asesoría legal.** El valor está en llegar al artículo correcto en
  segundos, no en decidir por ti.
- **No busca en internet.** Solo lee lo que tiene cargado.
- **No hace OCR.** Un escaneo sin capa de texto se rechaza al subirlo.
- **No lee hojas de cálculo.** Solo PDF y DOCX. Una tabla de miles de filas
  vectorizada devuelve filas parecidas a la pregunta, que no sirve para contar.

## Datos personales en lo que escribes

Puedes escribir consultas con datos reales del caso. Antes de enviarlas al
modelo, el sistema enmascara **DNI, RUC, correos, teléfonos, montos y
tarjetas**, y los devuelve a su sitio en la respuesta.

Dos límites:

- **No reconoce nombres de personas.** Si escribes "Juan Pérez", ese nombre
  sale del entorno. Cuando el nombre no aporte a la pregunta, no lo pongas.
- **No cubre lo que subes.** El contenido de un PDF o un DOCX viaja tal cual al
  vectorizarse. Un documento con datos personales los manda enteros.

## El estimador de multas

El panel lateral calcula rangos de multa por gravedad, en soles, usando la UIT
del año en curso.

Es una **estimación de impacto, no una sanción**. Devuelve el rango que fija la
ley; el monto concreto lo gradúa la autoridad según reincidencia, beneficio
obtenido e intencionalidad. Hoy solo cubre protección de datos.

## El mapa de normas

Debajo del filtro por materia hay un diagrama que muestra qué norma modifica o
reglamenta a cuál.

Lo más útil es lo que aparece con línea discontinua: normas que sabemos que
afectan a las cargadas pero cuyo texto no tenemos. Es el mapa de lo que le
falta al sistema, a la vista y no escondido en un documento técnico.

---

¿Echas en falta una norma? Se puede cargar: el procedimiento está en
[Cargar documentos](INGESTA.md), y el estado de cada fuente en
[Fuentes del corpus](FUENTES.md).
