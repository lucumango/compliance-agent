# CARLOS

**Compliance Audit Regulatory Logic Operational System**

Responde consultas sobre normativa peruana **citando artículo por artículo**, a
partir de un corpus cerrado de 754 unidades extraídas de 8 documentos
normativos. Cuando el corpus no cubre la consulta, lo dice en vez de improvisar.

```
$ python -m rag.cli "¿Cuál es la multa máxima por una infracción muy grave?"

1. Monto máximo en UIT: ... hasta cien unidades impositivas tributarias [F1].
2. Límite según ingresos: no puede exceder del diez por ciento de los
   ingresos brutos anuales ... [F1].

Fuentes:
  [F1] Ley 29733, Artículo 39  (similitud 0.757)
```

## Por dónde empezar

| Si quieres… | Ve a |
|---|---|
| **Usarlo** sin entrar en el código | [Guía de uso](GUIA.md) |
| Entender cómo funciona, o **encontrar el prompt** | [Cómo funciona](SISTEMA.md) |
| Saber qué normas hay cargadas y en qué estado | [Fuentes del corpus](FUENTES.md) |
| **Cargar PDFs nuevos** al corpus | [Cargar documentos](INGESTA.md) |
| Ver qué norma modifica a cuál | [Grafo de trazabilidad](GRAFO.md) |
| Tocar la interfaz | [Sistema de diseño](DESIGN.md) |
| Desplegar | [Desplegar](DEPLOY.md) |
| Saber qué falta por hacer | [Pendiente](PENDIENTE.md) |

## El corpus, de un vistazo

| Norma | Materia | Unidades | Estado del texto |
|---|---|---|---|
| **Ley 29783** — Seguridad y Salud en el Trabajo | `sst_laboral` | 252 | Consolidado al 28/04/2022 |
| **ISO 37001:2016** — Antisoborno | `antisoborno` | 204 | Traducción oficial |
| **Ley 29733** — Protección de Datos Personales | `proteccion_datos` | 194 | Consolidado |
| **DL 1106** — Lucha contra el lavado de activos | `laft` | 33 | Consolidado |
| **Ley 30424** — Responsabilidad admin. de personas jurídicas | `anticorrupcion` | 30 | ⚠⚠ Original de 2016 · OCR |
| **DL 1372** — Beneficiario final | `laft` | 19 | Consolidado |
| **Ley 27693** — Crea la UIF-Perú | `laft` | 18 | Consolidado al 01/10/2025 (SPIJ) |
| **Ley 29038** — Incorpora la UIF a la SBS | `laft` | 4 | Consolidado |

**Total: 754 unidades citables** en 8 normas.

La Ley 30424 requiere cuidado: el detalle está en
[Fuentes del corpus](FUENTES.md).

## El caso negativo es el que importa

Ante *"¿en cuántas horas debo notificar una brecha a la ANPD?"*, el sistema
responde que el corpus no lo contiene y remite al reglamento y a las directivas
de la ANPD.

Un RAG sin esa restricción contesta "72 horas" copiando el GDPR, que no es
derecho peruano. Esa negativa es la característica principal del producto, no
una carencia.

!!! warning "No es asesoría legal"

    El corpus informa; un abogado valida. Las respuestas citan la fuente
    precisamente para que se pueda comprobar.
