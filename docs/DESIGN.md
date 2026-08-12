# Sistema de diseño

Sigue la marca **EY**. Este documento existe porque `App.css` lo citaba desde
su primera línea sin que llegara a escribirse nunca; lo que sigue está leído de
la hoja de estilos, no inventado.

## Las dos reglas de marca

Gobiernan casi todo lo demás.

**1. Sin `border-radius`.** EY es angular; el redondeo rompe la identidad. Hay
una regla global que lo impone y evita que cualquier componente lo reintroduzca
por descuido:

```css
* { border-radius: 0; }
```

**2. El amarillo `#FFE600` nunca como texto sobre claro.** Contraste 2.2:1
sobre blanco — no pasa WCAG AA. El amarillo se usa de tres formas, todas
válidas:

- como **fondo** con texto `#161D23` encima (botón primario, sello, chips),
- como **borde** o anillo de foco,
- como **texto** solo sobre superficies oscuras (`#161D23`).

## Paleta

### Marca — no se tematiza

| Token | Valor | Uso |
|---|---|---|
| `--color-ey-yellow` | `#FFE600` | Acento, foco, CTA, rombos de decisión |
| `--color-ey-black` | `#161D23` | Cabecera, globo del usuario. **Nunca negro puro** |

Estos dos son la identidad, no el tema: valen lo mismo en claro y en oscuro.

### Tokens semánticos — estos sí cambian

| Token | Claro | Oscuro |
|---|---|---|
| `--background` | `#FFFFFF` | `#1B2229` |
| `--surface` | `#F2F2F2` | `#12181D` |
| `--border` | `#E8E8E8` | `#2B343C` |
| `--text-primary` | `#161D23` | `#F2F2F2` |
| `--text-secondary` | `#333333` | `#CBD3DA` |
| `--text-muted` | `#999999` | `#8B959E` |

En oscuro, `--surface` es **más oscuro** que `--background`: el fondo de la
página se hunde y las tarjetas flotan sobre él, que es al revés de lo que pasa
en claro. Esa inversión es deliberada — mantiene la misma jerarquía de
profundidad con los papeles intercambiados.

### Texto sobre superficies permanentemente oscuras

| Token | Valor | Uso |
|---|---|---|
| `--on-dark` | `#FFFFFF` | Texto en cabecera, globo del usuario, gravedad activa |
| `--on-dark-muted` | `#CCCCCC` | Texto secundario en la cabecera |

**No se tematizan.** Si se invirtieran, en modo oscuro quedaría texto oscuro
sobre el negro EY de la cabecera, que sigue siendo negro en ambos temas. Es el
error más fácil de cometer al tocar esta hoja.

### Riesgo

La escala de gravedad de las infracciones (leve / grave / muy grave) mapea
directamente sobre los colores semánticos de riesgo, en vez de definir una
paleta propia:

| Token | Valor | Gravedad |
|---|---|---|
| `--color-risk-low` | `#168736` | Leve |
| `--color-risk-medium` | `#FF6D00` | Grave |
| `--color-risk-high` | `#C4001A` | Muy grave |

Los tintes de fondo (`--tint-green`, `--tint-orange`, `--tint-red`,
`--tint-yellow`) se rebajan en oscuro: a plena saturación sobre fondo oscuro
vibran y cuesta leer encima.

## Cómo funciona el tema

Tres estados, no dos:

1. **Sin elegir** (por defecto) — manda el sistema operativo, vía
   `@media (prefers-color-scheme: dark)`.
2. **Claro elegido** — `data-theme="light"` en el `<html>`.
3. **Oscuro elegido** — `data-theme="dark"` en el `<html>`.

Por eso el bloque oscuro se declara **dos veces**: una bajo la media query
guardada con `:root:not([data-theme="light"])`, para que elegir claro gane
sobre un sistema en oscuro; y otra bajo `:root[data-theme="dark"]`, para que
elegir oscuro gane sobre un sistema en claro.

La elección se guarda en `localStorage` bajo `compliance:tema`. El hook está en
`App.jsx` (`useTema`), y el conmutador vive en la cabecera.

**Regla al añadir estilos:** usa siempre los tokens semánticos
(`--background`, `--text-primary`, `--border`…), nunca un hex literal ni los
grises de marca directamente. Si un color solo se define dentro del bloque
oscuro, en claro queda sin valor.

### Mermaid es la excepción

Mermaid no lee variables CSS: resuelve su tema al inicializar y necesita
valores literales. Por eso `Mermaid.jsx` duplica la paleta en dos objetos
(`TEMA_CLARO` y `TEMA_OSCURO`) y reinicializa al cambiar el tema, siguiendo el
`data-theme` del `<html>` con un `MutationObserver`.

Si cambias un color en `App.css`, mira si tiene equivalente ahí.

## Tipografía

**Nunito**, servida desde Google Fonts con `display=swap` para que el texto sea
legible mientras carga. Sustituye a EYInterstate, que es propietaria y no se
puede distribuir.

| Uso | Tamaño / interlineado | Peso |
|---|---|---|
| Cuerpo | 16 / 26 | 400 |
| Prosa de la respuesta | 16 / 26 | 400 |
| Interfaz y controles | 14 / 20–22 | 300–400 |
| Metadatos y notas | 12 / 18 | 300 |
| Rótulos de sección | 11 / 16, versalitas, `letter-spacing: .06em` | 700 |
| Títulos | 18 / 26 | 700 |

## Accesibilidad

- **Anillo de foco amarillo** en todo elemento interactivo, vía
  `:focus-visible`. No se elimina en ningún componente.
- El amarillo **nunca** como texto sobre claro (ver arriba).
- Los iconos decorativos llevan `aria-hidden="true"`; los que comunican estado
  llevan texto o `aria-label`.
- Los chips de cita son `<button>` reales, no `<span>` con `onClick`: navegan
  con teclado y se anuncian con el artículo que citan.
- Nada depende **solo** del hover: el chip de cita muestra la norma al pasar
  por encima, pero también se puede pulsar, que es lo que funciona en táctil.

## Iconos

Exclusivamente [`lucide-react`](https://lucide.dev). Sin emojis. Tamaño 14–16 px
en interfaz, 24 px en la marca.

## Componentes con reglas propias

**Chips de cita.** El modelo cita con etiquetas desnudas (`[F1]`) porque son lo
único que puede escribir sin equivocarse. En claro van en amarillo pleno con
borde negro; en oscuro se invierten a contorno amarillo sobre el fondo, porque
el amarillo pleno dentro de un párrafo deslumbra. Una etiqueta que no
corresponde a ninguna fuente se pinta en rojo con borde discontinuo: **no se
oculta**, porque que se vea es la señal de que la respuesta va mal.

**Barra de riesgo de la calculadora.** El ancho representa dónde cae el tramo
dentro de la escala del régimen, y el color sale de `--color-risk-*`. Lleva
`role="img"` con `aria-label`, porque la proporción no se puede leer.

**Avisos de corpus.** Las normas que vienen de escaneo con OCR llevan un aviso
permanente en el panel lateral. No es decorativo: condiciona cuánto se puede
confiar en la cita.
