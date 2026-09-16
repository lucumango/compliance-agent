"""Registros públicos contra los que DIEGO puede comprobar a un tercero.

Dos clases, y no se tratan igual:

  * **Listas de sanciones** — OFAC, ONU, UE y Reino Unido. Pequeñas, públicas
    y en inglés. Se busca por nombre, y una coincidencia es siempre POTENCIAL.
  * **Padrón de SUNAT** — estado del contribuyente y condición de domicilio.
    Grande. Se busca por RUC, y el resultado es un hecho, no una coincidencia.

Nada de aquí va al modelo. DIEGO no "consulta" estos registros con un LLM: el
cotejo es determinista y el resultado llega al usuario tal cual, con la fecha
de la lista contra la que se comparó. Una lista de sanciones de hace tres
meses no protege a nadie, y un "no aparece" sin decir en qué lista y a qué
fecha es peor que no decir nada.
"""
