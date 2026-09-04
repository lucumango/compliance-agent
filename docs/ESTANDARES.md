# Estándares

Qué estándares cumple el código hoy, aunque no los nombre, y cuáles conviene
adoptar. Auditoría del 03/09/2026 sobre 4.507 líneas de Python y 3.363 de
JavaScript.

Tres estados: **sí** (está implementado y verificado en el código), **parcial**
(hay algo pero no lo suficiente para declararlo), **no**.

---

## Resumen

| Marco | Estado | Dónde |
|---|---|---|
| OWASP Top 10 (2021) | Sí, salvo la clave compartida en el bundle | `auth.py`, `nube.py`, SQL |
| OWASP API Security Top 10 (2023) | Sí | `api.py`, `auditoria.py` |
| **OWASP Top 10 para LLM (2025)** | Sí, salvo el indexado sin enmascarar | `answer.py`, `002_documentos.sql` |
| ISO/IEC 27001:2022 (Anexo A) | Parcial — controles técnicos sí, gestión no | todo el backend |
| ISO/IEC 27701 (datos personales) | Parcial | `anonimizar.py`, `purgar_historial` |
| **ISO/IEC 42001:2023 (gestión de IA)** | Sí, salvo asignar los roles | [GOBERNANZA.md](GOBERNANZA.md) |
| NIST AI RMF 1.0 | Sí, las cuatro funciones | [GOBERNANZA.md](GOBERNANZA.md) |
| PEP 8 / PEP 257 | Sí, verificado con `ruff` en el CI | `backend/ruff.toml` |
| OpenAPI 3.1 | Sí, generado y sin usar | `/openapi.json` |
| SemVer | No | — |

---

## Seguridad

### Lo que ya está bien

| Control | Implementación | Estándar que lo cubre |
|---|---|---|
| Aislamiento entre usuarios | Row level security en las cinco tablas; verificado con 0 filas visibles sin sesión | OWASP A01, API1 (BOLA) |
| Sin credencial privilegiada en el servidor | Todo viaja con el JWT del usuario; `service_role` no existe en el despliegue | ISO 27001 A.8.2, A.8.3 |
| RPC que no salta las políticas | `buscar_fragmentos` es `security invoker` | OWASP A01 |
| Secretos fuera del repositorio | `.gitignore` cubre `.env*`; `sync: false` en `render.yaml` | ISO 27001 A.8.24 |
| Comparación de clave en tiempo constante | `hmac.compare_digest` en `auth.py` | ISO 27001 A.8.24 |
| Límite de uso por IP | Ventana deslizante, 30/60 s, con `Retry-After` | OWASP API4 |
| CORS por lista blanca | `ALLOWED_ORIGINS`, no comodín | OWASP A05 |
| Sin inyección de HTML | `react-markdown` sin `rehype-raw`; Mermaid en `securityLevel: strict` | OWASP A03 |
| Sin SQL construido a mano | Todo por PostgREST; el vector se castea dentro de la función | OWASP A03 |
| Subida acotada | 20 MB, extensión y content-type, deduplicado por SHA-256 | OWASP A08 |
| Enmascarado de PII antes de salir | `anonimizar.py`: DNI, RUC, correo, teléfono, tarjeta, cuenta, monto | ISO 27701, Ley 29733 art. 28 |
| Retención con plazo | `purgar_historial(dias)` | ISO 27001 A.5.33, A.8.10 |
| Fuera de los buscadores | `robots.txt` con `Disallow: /` y `noindex` | — |

### Lo que falta

| Hueco | Por qué importa | Estándar |
|---|---|---|
| **La clave compartida viaja en el bundle** | Documentado en `auth.py`, sin resolver. Es visible en las herramientas de desarrollo. Frena el abuso de paso, no a alguien decidido | OWASP A07 |
| **Registro abierto en Supabase** | Cualquiera con la URL se crea cuenta. Además, una consulta sin sesión no deja evento de auditoría | OWASP A07 |
| **CSP en modo aviso, no en modo bloqueo** | Va como `Content-Security-Policy-Report-Only`: informa de las violaciones sin romper nada. Promoverla a `Content-Security-Policy` exige mirar la consola del navegador una vez en el despliegue real | OWASP A05 |
| **El texto del documento se indexa sin enmascarar** | Al subirlo viaja íntegro a Google para vectorizarlo. Enmascararlo antes haría que lo guardado no coincidiera con el original y degradaría la recuperación. Está avisado en la interfaz | ISO 27701 |

### Lo que se cerró en esta ronda

| Hueco | Qué se hizo |
|---|---|
| Sin registro de auditoría | `eventos_auditoria`, sin política de borrado ni de modificación |
| Sin análisis de dependencias | `pip-audit` y `npm audit` en el CI, con `ruff` |
| El contenedor corría como root | `USER carlos` (uid 10001) después de los `COPY`, así que los ficheros le quedan de solo lectura |
| Sin cabeceras de seguridad | `nosniff`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy` y la CSP en modo aviso, en `vercel.json` |
| Clave de API en la query string | A la cabecera `x-goog-api-key`. Una URL con `?key=` acaba en los registros de cualquier proxy |
| **Las funciones de purga estaban abiertas** | `purgar_historial` y `purgar_auditoria` son `security definer` y Postgres les concede `EXECUTE` a `PUBLIC` por defecto. PostgREST las exponía en `/rest/v1/rpc/` y la clave `anon` es pública: cualquiera podía borrar las conversaciones de todos. `004_permisos_purga.sql` revoca el permiso y deja las siguientes funciones cerradas por defecto |

## OWASP Top 10 para LLM

El marco más específico para lo que es esto. La versión de 2025.

| Riesgo | Estado |
|---|---|
| LLM01 Inyección de prompt | **Sí.** Cada fuente va en su bloque `<fuente id="F1">…</fuente>`, el delimitador se escapa dentro del texto del usuario para que no pueda forjarse, y la regla 9 dice que lo de dentro son datos y nunca órdenes. Con un caso en `rag.eval_prompt` |
| LLM02 Fuga de información sensible | **Parcial.** `anonimizar.py` cubre ya la consulta **y** los fragmentos de documento que entran al prompt, con la misma tabla de marcadores. Lo que sigue saliendo sin enmascarar es el texto que se vectoriza al subir el fichero; está avisado en la interfaz |
| LLM03 Cadena de suministro | **Parcial.** `pip-audit` y `npm audit` en el CI. Sigue sin SBOM y con versiones por rango |
| LLM04 Envenenamiento de datos | **Sí.** El corpus normativo se construye en local desde PDF oficiales y viaja ya indexado |
| LLM05 Manejo inseguro de la salida | **Sí.** El Markdown se renderiza sin HTML; el Mermaid, en modo estricto |
| LLM06 Agencia excesiva | **Sí.** El modelo no tiene herramientas. Solo redacta |
| LLM07 Fuga del prompt de sistema | **No evaluado.** El prompt no es secreto, pero nada impide extraerlo |
| **LLM08 Debilidades de vectores y embeddings** | **Sí, y es el punto fuerte.** Los fragmentos del usuario viven en Postgres bajo RLS, no en el índice común, y tienen cuota separada. Un filtro por usuario que se olvida una vez filtra documentos de un cliente a otro; aquí no hay filtro que olvidar |
| LLM09 Desinformación | **Sí, medido.** Ocho reglas, descargo y citas obligatorias, y `rag.eval_prompt` verifica seis de las ocho. Las reglas 2 y 6 son de matiz y se leen a mano |
| LLM10 Consumo ilimitado | **Parcial.** Límite por IP, sí; por cuenta, no; presupuesto de tokens, no |

Queda LLM02 a medias —el indexado— y LLM10, que a esta escala no aprieta.

---

## Gestión de IA: ISO/IEC 42001

Es el estándar de sistema de gestión para IA, equivalente a lo que la 27001 es
para seguridad. Certificable. Y el que un cliente de EY va a preguntar.

**Está cubierto.** Lo que faltaba se escribió en [GOBERNANZA.md](GOBERNANZA.md)
—alcance, evaluación de impacto, roles, ciclo de vida, seguimiento e
incidentes— y lo que había que implementar está implementado:

| Lo que faltaba | Qué se hizo |
|---|---|
| Evaluación de impacto | Siete escenarios con gravedad, control y riesgo residual. Tres siguen en alto y están nombrados |
| Roles | Cuatro papeles definidos, con la regla de que quien carga una norma no firma su cotejo |
| Inventario de versiones | `PROMPT_VERSION` (etiqueta + hash de `_SISTEMA`), el modelo que respondió de verdad, y las unidades del corpus. En `mensajes`, en `eventos_auditoria` y en `/api/salud` |
| Ciclo de vida | Cuándo entra una norma, cuándo se coteja, cuándo sale, y cuándo se retira el sistema |
| Seguimiento | Tres evaluaciones con disparador declarado, y un registro de auditoría que nadie puede borrar desde la aplicación |
| Incidentes | `CORRECCIONES.md` es el registro. Un incidente que toca el prompt exige un caso nuevo en `rag.eval_prompt` |

**Lo único que queda es poner nombres en los cuatro roles.** Eso no lo decide
el código.

**NIST AI RMF 1.0** queda cubierto por el mismo documento: GOVERN, MAP, MEASURE
y MANAGE tienen su sección.

---

## Prompts

El prompt de sistema vive en `rag/answer.py`, en `_SISTEMA`. Ocho reglas.

### Lo que ya sigue las guías publicadas

| Práctica | Fuente | Dónde |
|---|---|---|
| Rol + tarea + restricciones, en ese orden | Google, Anthropic | primera línea de `_SISTEMA` |
| El contexto largo antes de la consulta | Google (contexto largo), Anthropic (documentos primero) | `FUENTES:` y luego `CONSULTA:` |
| Instrucción explícita de admitir ignorancia | Anthropic | regla 3 |
| Formato de cita exigido y verificable | Anthropic (citas ancladas) | regla 1, etiquetas `[F#]` y `[D#]` |
| Temperatura baja para tareas de fidelidad | Google | `temperatura=0.2` |
| Restricciones numeradas, no en prosa | ambas | las ocho reglas |
| Distinguir clases de fuente | específico de aquí | regla 2 |

Esa regla 2 —norma que obliga frente a documento interno que no— no está en
ninguna guía y es la mejor decisión de prompt del proyecto.

### Lo que las guías dicen y aquí ya se hace

**Delimitadores estructurados.** Antes las fuentes iban separadas por `---` y
encabezadas por `[F1]`, y un documento que contuviera `---` o `[F3]` se
confundía con la estructura. Ahora cada una va en su bloque
`<fuente id="F1" clase="norma" cita="…">…</fuente>`, que es lo que recomiendan
las guías para contexto largo. Dentro del texto, la secuencia `<fuente` se
neutraliza —el `<` pasa a `‹`— para que un PDF no pueda cerrar el bloque antes
de tiempo y colarse a la altura de las reglas.

### Lo que las guías dicen y aquí no se hace

- **Citar antes de responder.** La práctica de pedir al modelo que extraiga
  primero las frases relevantes y responda después reduce la invención en
  contexto largo. No se hace.
- **`systemInstruction`.** Gemini tiene un campo aparte para las instrucciones
  de sistema. `gemini.py` manda todo —reglas, fuentes y consulta— en un único
  turno de usuario. El modelo trata las reglas con menos peso del que podría.
- **Ejemplos.** Cero. Un par de ejemplos de respuesta bien citada y de negativa
  bien redactada valen más que otra regla.
- **`safetySettings` explícitos.** No se configuran, así que aplican los
  valores por defecto. Un asistente que habla de soborno, fraude y lavado de
  activos es el caso donde un filtro por defecto bloquea contenido legítimo.
  `gemini.py` ya trata la respuesta vacía con `finishReason`, que es
  exactamente la forma que tiene un bloqueo.

### El hueco que había

`rag.eval` mide **recuperación** y no mira nada de lo que produce el modelo.
Las ocho reglas del prompt no tenían un solo caso que las verificara: cambiar
una palabra en `_SISTEMA` no rompía nada porque no había nada que romper.

Ahora existe `python -m rag.eval_prompt`, con seis casos que cubren las reglas
1, 3, 4, 5, 7 y 8. Las comprobaciones son deterministas —presencia, ausencia,
formato— porque una que dependa de otro modelo para juzgar convierte un fallo
en una discusión. Eso deja fuera las reglas 2 y 6, que son de matiz y se leen a
mano.

La primera ejecución encontró un defecto real: el modelo abría con *"De acuerdo
con la normativa peruana, el titular puede ejercer los siguientes derechos"*,
que es exactamente la bisagra que la regla 8 prohíbe. Se endureció la regla y
desapareció. Eso es para lo que sirve el banco.

---

## Estándares de código

| Estándar | Estado |
|---|---|
| PEP 8, PEP 257, anotaciones de tipo | Se siguen de forma consistente. **Ninguna herramienta lo comprueba**: no hay `ruff` ni `black` |
| Lint del frontend | `oxlint` configurado, con tres reglas. No corre en CI |
| OpenAPI 3.1 | FastAPI lo genera en `/openapi.json` y `/docs`. Nadie lo usa ni lo versiona |
| Versionado semántico | `api.py` dice `0.1.0`, `package.json` dice `0.0.0`, y no hay etiquetas de git |
| Mensajes de commit | Frases imperativas en español, coherentes. No son Conventional Commits, y no pasa nada |
| Pruebas | **Cero.** Ni una |
| CI | Solo publica documentación. No hay lint, ni pruebas, ni análisis de dependencias |

---

## Qué queda, en orden

Cerrado en las dos últimas rondas: evaluación del prompt, `prompt_version`,
registro de auditoría, gobernanza, delimitadores estructurados, anonimización
de los documentos en el prompt, CI con auditoría de dependencias y lint,
contenedor sin root, cabeceras de seguridad y la clave fuera de la query
string.

1. **Cerrar el alta abierta en Supabase.** Panel → Authentication → Providers →
   Email. Es de tres clics y es el último hueco de OWASP A07 que se puede
   cerrar.
2. **Promover la CSP a modo bloqueo.** Está desplegada en modo aviso; hace
   falta abrir la consola del navegador una vez en producción, ver que no
   reporta violaciones, y quitarle el `-Report-Only`.
3. **`systemInstruction` y ejemplos en el prompt.** Las dos recomendaciones de
   Google y Anthropic que siguen sin aplicarse.
4. **`safetySettings` explícitos.** Un asistente que habla de soborno y lavado
   es el caso donde un filtro por defecto bloquea contenido legítimo.
5. **Presupuesto por cuenta**, no solo por IP. Cierra LLM10.
6. **Cotejar el corpus contra SPIJ.** No es código, y es el riesgo alto que más
   pesa.
7. **Poner nombres en los cuatro roles** de [GOBERNANZA.md](GOBERNANZA.md).
