# Gobernanza del sistema de IA

Lo que hay que tener escrito para que CARLOS sea un sistema de IA gestionado y
no un script con suerte. Sigue la estructura de **ISO/IEC 42001:2023**, que es
el estándar de sistema de gestión de IA, y el mapeo con **NIST AI RMF 1.0**
está al final.

Redactado el 03/09/2026. Lo que está en tabla se revisa; lo que está en prosa
se discute.

---

## 1. Alcance

**Qué es.** Un asistente que responde consultas sobre normativa peruana de
compliance citando artículo por artículo, sobre un corpus cerrado de 824
unidades en 11 normas, más los documentos que cada usuario sube.

**Qué decide.** Nada. Redacta y cita. No clasifica personas, no puntúa
riesgos, no aprueba ni deniega. Toda decisión la toma quien lee la respuesta.

**Quién lo usa.** Analistas de compliance y de debida diligencia de EY. No es un
producto de cara al cliente ni al público.

**Cuántos agentes.** Dos: CARLOS y DIEGO, cada uno con su corpus y su alcance
declarado en [AGENTES.md](AGENTES.md). El alcance no es documentación: entra
literal al prompt y hay casos que comprueban que se respeta.

**Qué alimenta.** Borradores de trabajo interno: memorandos, matrices de
requisitos, preparación de entrevistas. **No entra en un entregable sin que un
profesional coteje la cita contra la fuente oficial.**

**Fuera de alcance, declarado.** No tipifica delitos —el Código Penal está
deliberadamente fuera del corpus, ver [FUENTES.md](FUENTES.md)—, no da
asesoría legal, no cubre lo tributario, societario, ambiental ni sectorial, y
no sabe qué se publicó ayer.

---

## 2. Evaluación de impacto

Quién puede salir perjudicado y cómo.

| Qué puede fallar | A quién afecta | Gravedad | Qué lo contiene | Riesgo que queda |
|---|---|---|---|---|
| **Cita una norma derogada como vigente** | El cliente de la auditoría | Alta — un hallazgo mal fundado | Se carga solo la última versión consolidada; `estado_texto` y `vigente` por unidad; aviso en la respuesta | **Alto.** Ninguna de las 11 normas está cotejada contra SPIJ |
| **Inventa un artículo o un plazo** | El analista, que lo copia | Alta | Respuesta anclada a fuentes recuperadas; regla 7 del prompt; `rag.eval_prompt` verifica que las cifras salgan de una fuente | Medio-bajo |
| **Presenta una política interna como obligación legal** | El cliente | Alta — le exige lo que no le exige la ley | Regla 2 del prompt; `[F]` y `[D]` separados en la interfaz; aviso automático al citar documentos | Medio. Es la regla que ningún control automático verifica |
| **Responde solo la mitad y no dice que falta la otra** | El analista | Media | Regla 3 y regla 5 del prompt; el grafo de trazabilidad marca las normas que no están cargadas | Medio |
| **Datos personales del caso salen a Google** | El titular de los datos | Alta | `anonimizar.py` enmascara DNI, RUC, correo, teléfono, tarjeta, cuenta y monto de la consulta **y** de los fragmentos de documento que entran al prompt, con la misma tabla | **Medio.** No cubre nombres, y el texto del documento sí viaja íntegro al vectorizarse. Avisado en la interfaz |
| **Un usuario ve documentos de otro** | Dos clientes a la vez | Crítica | Row level security en las cinco tablas; el servidor no tiene credencial que la salte; verificado con 0 filas sin sesión | Bajo |
| **Alguien borra el historial o el registro de auditoría de todos** | Todos los usuarios a la vez | Crítica | Las funciones de purga ya no son invocables desde el API (`004_permisos_purga.sql`), y las nuevas nacen cerradas | Bajo, desde el 04/09/2026 |
| **Un documento subido inyecta instrucciones en el prompt** | Quien lee la respuesta | Media | Bloques `<fuente>` delimitados, el delimitador escapado dentro del texto del usuario, y la regla 9 del prompt. Con caso en `rag.eval_prompt` | Bajo |

**El alto que queda es uno: el cotejo contra SPIJ.** La inyección de prompt y
la anonimización de documentos bajaron al cerrarlas; lo que sigue sin cubrir de
la segunda es el indexado, que va avisado en la interfaz. El cotejo no es
trabajo de código y está en [PENDIENTE.md](PENDIENTE.md).

**Decisión.** El sistema se usa con esos riesgos porque es una herramienta de
borrador con obligación de cotejo, no una fuente de verdad. Esa obligación es
lo que sostiene el riesgo alto de cotejo, y por eso el descargo va en cada
respuesta y no en un pie de página.

---

## 3. Roles

Un sistema sin nombres detrás no está gestionado. Cuatro papeles; una misma
persona puede llevar varios, pero cada uno tiene que tener dueño.

| Papel | Decide | Asignado a |
|---|---|---|
| **Responsable del sistema** | Que exista, qué alcance tiene, cuándo se retira | _por asignar_ |
| **Responsable del corpus** | Qué norma entra, con qué texto y con qué estado. Firma el cotejo contra SPIJ | _por asignar_ |
| **Responsable técnico** | Prompt, modelo, recuperación, despliegue. Ejecuta las evaluaciones | _por asignar_ |
| **Revisor de uso** | Lee el registro de auditoría y decide si el uso real coincide con el alcance | _por asignar_ |

Regla que no se salta: **quien carga una norma no es quien firma que está
cotejada.** Cotejar es comparar contra SPIJ, y comparar contra uno mismo no es
comparar.

---

## 4. Ciclo de vida

**Una norma entra** cuando el responsable del corpus la aprueba. El proceso
técnico está en [INGESTA.md](INGESTA.md). Entra con `metadata_verificada` en
falso y un caso de evaluación propio. Sin caso de evaluación no entra: nadie
sabría cuándo deja de recuperarse.

**Una norma se coteja** después, contra SPIJ, artículo por artículo. Solo
entonces `metadata_verificada` pasa a verdadero, con `url_fuente` y
`fecha_publicacion` reales. Nada se afirma de memoria.

**Una norma sale** cuando se deroga entera. Una modificatoria no crea una
entrada nueva: se sustituye el texto consolidado y se reindexa.

**El prompt cambia** solo con `rag.eval_prompt` en verde después. Cambiarlo
mueve `PROMPT_VERSION`, que queda grabada en cada respuesta.

**El modelo cambia** con las dos evaluaciones en verde. Cambiar el modelo de
embeddings obliga a reindexar entero: los vectores viejos y los nuevos no son
comparables y la degradación es silenciosa.

**El sistema se retira** si el corpus lleva más de un año sin cotejar y sigue
usándose para entregables. Un asistente normativo desactualizado no es neutro:
es peor que no tenerlo, porque da confianza.

---

## 5. Inventario de versiones

Qué produjo cada respuesta, y dónde consta.

| Componente | Identificador | Dónde queda grabado |
|---|---|---|
| Prompt | Etiqueta + hash de `_SISTEMA` **y del bloque del agente**: dos agentes no comparten prompt | `mensajes.prompt_version`, `eventos_auditoria.prompt_version`, `/api/agentes` |
| Agente | Cuál respondió, y su alcance declarado | Respuesta de la API y `/api/agentes` |
| Modelo | El que respondió de verdad, no el configurado | `mensajes.modelo`, `eventos_auditoria.modelo` |
| Cadena de respaldo | Modelos fijados, nunca un alias `-latest` | `rag/config.py`, verificable con `rag.modelos` |
| Corpus | Número de unidades indexadas | `eventos_auditoria.corpus_unidades` y `/api/salud` |
| Fuentes citadas | Cita y texto, copiados enteros | `mensaje_fuentes` |

La versión del prompt lleva hash a propósito: la etiqueta se sube a mano y se
olvida, el hash no. Si alguien edita `_SISTEMA` sin tocar la etiqueta, la
versión cambia igual y las dos siguen siendo distinguibles.

El modelo se anota porque **la cadena de respaldo degrada sola**: al agotarse
la cuota de uno, responde el siguiente. Sin esa columna, "esta respuesta la dio
Gemini 3.5 Flash" es una suposición.

---

## 6. Seguimiento

**Qué se mide y cuándo.**

| Evaluación | Qué mide | Cuándo se corre |
|---|---|---|
| `python -m ingestion.validate` | Calidad del corpus parseado | Al tocar el parser, el registro o los PDF |
| `python -m rag.eval` | Recuperación: que el artículo correcto salga | Al tocar recuperación, índice o embeddings |
| `python -m rag.eval_prompt` | Que el modelo cumpla sus propias reglas | Al tocar `_SISTEMA` o cambiar de modelo |
| `ruff check backend/` + `pip-audit` + `npm audit` | Lint y vulnerabilidades de dependencias | En cada push, automático |
| `python -m rag.modelos` | Que los modelos declarados sigan existiendo | Cada mes |
| `python -m agentes.evaluar` | Que cada agente encuentre lo suyo, cite artículos que existen y rechace lo ajeno | Al tocar un agente. La parte gratis, en cada push |

`rag.eval_prompt` verifica las reglas 1, 3, 4, 5, 7, 8 y 9. Las reglas **2 y 6 no
tienen control automático** —no confundir norma con política interna, y no dar
asesoría— porque son de matiz y una comprobación que dependa de otro modelo
para juzgar convierte un fallo en una discusión. Se leen a mano.

**Qué se registra.** `eventos_auditoria` guarda quién, cuándo, qué acción, qué
modelo, qué versión del prompt, cuántas unidades tenía el corpus y qué normas
se citaron.

**Qué no se registra, y por qué.** El texto de la consulta. Lleva datos del
caso y la anonimización reconoce patrones, no nombres. El historial de chat ya
lo guarda para quien lo escribió y bajo su propia política; duplicarlo en el
registro multiplica la exposición sin añadir nada que una revisión necesite.

**Quién no puede borrarlo.** Nadie desde la aplicación. `eventos_auditoria`
tiene política de inserción y de lectura, y ninguna de modificación ni de
borrado: PostgREST las rechaza. Se lee entero desde el panel de Supabase.

**Sin sesión no hay evento.** Una consulta anónima no queda registrada, porque
no hay a quién atribuirla. Es una razón más para cerrar el alta abierta.

---

## 7. Incidentes

Qué cuenta como incidente aquí:

- una función de Postgres alcanzable desde internet que no debía serlo —pasó el
  04/09/2026 con las dos funciones de purga, ver
  [ESTANDARES.md](ESTANDARES.md);

- una cita que resultó ser de una norma derogada, o que no dice lo que la
  respuesta afirmó;
- una respuesta que presentó una política interna como obligación legal;
- un fragmento de documento visible para quien no es su dueño;
- datos personales identificables enviados al modelo.

Qué se hace: se reproduce con la `prompt_version` y el modelo que constan en el
mensaje, se anota en [CORRECCIONES.md](CORRECCIONES.md) con la respuesta antes
y después, y si el arreglo toca el prompt se añade un caso a `rag.eval_prompt`
que lo fije. Un incidente sin caso de evaluación vuelve.

CORRECCIONES.md es el registro de incidentes. Ya tiene ocho.

---

## 8. Correspondencia con los estándares

| ISO/IEC 42001 pide | Aquí |
|---|---|
| Alcance del sistema de IA | Sección 1 |
| Evaluación de impacto | Sección 2 |
| Roles y responsabilidades | Sección 3 — **falta asignar nombres** |
| Ciclo de vida del sistema | Sección 4 |
| Datos y su procedencia | [FUENTES.md](FUENTES.md), `ingestion/registry.py` |
| Información para el usuario | [GUIA.md](GUIA.md), y el descargo en cada respuesta |
| Seguimiento y medición | Sección 6 |
| Registro de incidentes | Sección 7, [CORRECCIONES.md](CORRECCIONES.md) |
| Trazabilidad de las salidas | Sección 5 |

| NIST AI RMF | Aquí |
|---|---|
| **GOVERN** | Secciones 1, 3 y 4 |
| **MAP** | Sección 2, y el grafo de cobertura en [GRAFO.md](GRAFO.md) |
| **MEASURE** | Sección 6 |
| **MANAGE** | Sección 7 |

**Lo único que queda para poder decirlo entero: poner nombres en la sección 3.**
El resto está escrito y, donde toca, implementado.

Ver [ESTANDARES.md](ESTANDARES.md) para el resto de marcos —OWASP, ISO 27001,
27701— y lo que falta en cada uno.
