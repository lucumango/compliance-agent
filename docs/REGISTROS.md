# Registros públicos

El cotejo de DIEGO: comprobar a un tercero contra registros públicos. **Sin
modelo.** El nombre o el RUC no salen del servidor, la comparación es
determinista y el resultado es el mismo cada vez.

```bash
python -m registros.actualizar            # listas de sanciones + OSCE
python -m registros.actualizar --sunat    # además el padrón de SUNAT (392 MB)
python -m registros.evaluar               # 11 comprobaciones, sin cuota
```

---

## Qué se coteja

| Registro | Emisor | Se busca por | Resultado | Última fecha vista (16/09/2026) |
|---|---|---|---|---|
| **SDN** | OFAC, Tesoro de EE. UU. | Nombre | Coincidencia potencial | 16/09/2026 |
| **Lista consolidada** | Consejo de Seguridad de la ONU | Nombre | Coincidencia potencial | 15/09/2026 |
| **Sanciones financieras** | Unión Europea | Nombre | Coincidencia potencial | **05/08/2026** |
| **UK Sanctions List** | FCDO, Reino Unido | Nombre | Coincidencia potencial | 11/09/2026 |
| **Padrón reducido de RUC** | SUNAT | RUC; razón social solo para personas jurídicas | Hecho | 16/09/2026 |
| **Proveedores sancionados** | Tribunal de Contrataciones del Estado (OSCE) | RUC; o nombre | Hecho por RUC, candidato por nombre | **17/12/2025** |

Las dos fechas en negrita no son un fallo de descarga: es lo que publica el
emisor. La de la UE la confirma su propio portal; la del OSCE es la última
publicación del dataset en la Plataforma Nacional de Datos Abiertos. El cotejo
lo avisa en cada resultado.

## Qué no se coteja, y por qué

- **SUNARP** — no publica nada descargable.
- **RNSSC** (sanciones a servidores civiles, SERVIR) — **sí** está en datos
  abiertos, pero anonimizado: nombre `****** ****** ******` y documento
  `********` en las 10.014 filas de los tres ficheros. Sirve para estadística.
  Para comprobar a una persona hay que ir al portal de SERVIR con su DNI.
- **La "Consolidated List" de OFSI** — es la lista británica que sale primero
  en los buscadores, y **se retiró el 28/01/2026**. La que se usa es la UK
  Sanctions List de la FCDO, que la sustituyó.

---

## Una coincidencia es siempre potencial

Cotejar un nombre contra una lista es comparar texto, no identificar a una
persona. "JUAN CARLOS PEREZ" en una lista no es el Juan Carlos Pérez proveedor
de tu cliente hasta que alguien lo contrasta con fecha de nacimiento, documento
o nacionalidad. Por eso cada coincidencia enseña su score y esos datos, y
ninguna función devuelve "está sancionado".

**Y un "no aparece" siempre lleva lista y fecha.** Sin eso no significa nada.

## Cómo se compara

Tildes fuera, mayúsculas, solo letras y dígitos, y fuera las formas
societarias: "Constructora Andina S.A.C." y "CONSTRUCTORA ANDINA SAC" dan lo
mismo.

Después `token_sort_ratio`, con umbral 85. **No `token_set_ratio`**: ese da 100
cuando un nombre está contenido en otro, y "JUAN PEREZ" saldría idéntico a
"JUAN PEREZ ALIAS EL CARNICERO". Con los homónimos que hay en una lista de
33.000 designados, eso es ruido que acaba ignorándose.

Lo que el banco de pruebas exige, y cumple:

| Caso | Qué rompe | Resultado |
|---|---|---|
| `Banco Nacional de Cuba S.A.` | minúsculas y forma societaria | OFAC |
| `MADURO MOROS, Nicolás` | tilde y orden apellido-nombre | OFAC |
| `Nicolas Madruo Moros` | errata | OFAC, score 95 |
| `Rosneft Oil Company PJSC` | forma societaria rusa | OFAC y UK |
| `Constructora Andina del Peru SAC` | empresa inventada | nada |
| `Juan Carlos Perez Garcia` | nombre común | nada |

## Por qué hacen falta varios

Probado con un proveedor real del dataset del OSCE:

| Registro | Dice |
|---|---|
| SUNAT | **ACTIVO / HABIDO** — limpio a primera vista |
| OSCE | **Cuatro inhabilitaciones definitivas** para contratar con el Estado |
| Listas de sanciones | Nada |

Mirando solo la ficha RUC, parecía un proveedor en regla.

El padrón da otro dato por sí solo: de las ~2,3 millones de personas jurídicas,
**316.237 figuran como NO HABIDO**, el 13,7 %.

---

## Las personas naturales, solo por RUC

El padrón de SUNAT incluye a millones de personas naturales con negocio (RUC
que empieza por 10), con nombre completo. Consultar el estado del RUC de un
proveedor que ya te dio su número es debida diligencia; buscar a una persona
por su nombre entre dieciocho millones de registros es otra cosa, y no hace
falta. La búsqueda por nombre en SUNAT se limita a personas jurídicas.

## Nada de esto va a git

Los registros viven en `backend/data/registros/`, que está en `.gitignore`.
Pesan cientos de megas, cambian a diario, y una foto guardada sería vieja al
día siguiente.

**En producción**, el Dockerfile baja las listas de sanciones y el dataset del
OSCE al construir la imagen: cada despliegue lleva los de ese día. Si una fuente
no responde, el build sigue y el cotejo dice qué falta. **El padrón de SUNAT no
entra**: son 1,5 GB y no caben en el plan gratuito de Render. En producción, el
cotejo por RUC responde que el padrón no está disponible.

## Auditoría

Cada cotejo deja un evento `cotejo` en `eventos_auditoria`: quién, cuándo y
cuántas coincidencias. **Sin el nombre ni el RUC cotejado**, por lo mismo que
no se guarda el texto de una consulta.

Requiere `005_auditoria_cotejo.sql`. Sin ella el cotejo funciona pero el evento
se rechaza en silencio.
