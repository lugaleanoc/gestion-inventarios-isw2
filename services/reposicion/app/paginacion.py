"""Paginacion y lectura de parametros de la URL.

El contrato dice que todos los listados aceptan `pagina` y `porPagina`
(maximo 100) y responden con esta forma:

    {"datos": [...], "paginacion": {"pagina": 1, "porPagina": 20, "total": 57}}
"""

from flask import request

from .config import Config
from .errores import DatosInvalidos


def parametros_de_pagina():
    """Lee pagina y porPagina de la URL, con sus limites."""
    try:
        pagina = int(request.args.get("pagina", 1))
        por_pagina = int(request.args.get("porPagina", Config.POR_PAGINA_DEFECTO))
    except ValueError:
        raise DatosInvalidos("Los parametros 'pagina' y 'porPagina' deben ser numeros")

    if pagina < 1:
        raise DatosInvalidos("El parametro 'pagina' empieza en 1")
    # Se recorta en vez de fallar: pedir 500 registros devuelve 100.
    por_pagina = max(1, min(por_pagina, Config.POR_PAGINA_MAXIMO))
    return pagina, por_pagina


def paginar(consulta, a_dic):
    """Aplica la paginacion a una consulta de SQLAlchemy.

    consulta: la consulta ya filtrada, sin ejecutar.
    a_dic:    funcion que convierte cada fila en diccionario (normalmente
              el metodo a_dic() del modelo).
    """
    pagina, por_pagina = parametros_de_pagina()
    total = consulta.count()  # cuenta sin traer las filas
    filas = consulta.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return {
        "datos": [a_dic(fila) for fila in filas],
        "paginacion": {"pagina": pagina, "porPagina": por_pagina, "total": total},
    }


def booleano_de_url(nombre, por_defecto=None):
    """Lee un parametro de la URL que representa si/no.

    En una URL todo es texto: ?activo=true llega como la cadena "true".
    """
    valor = request.args.get(nombre)
    if valor is None:
        return por_defecto
    return valor.lower() in ("true", "1", "si", "sí")


def entero_de_url(nombre, por_defecto=None):
    """Lee un parametro numerico de la URL (por ejemplo ?categoriaId=8)."""
    valor = request.args.get(nombre)
    if valor is None or valor == "":
        return por_defecto
    try:
        return int(valor)
    except ValueError:
        raise DatosInvalidos("El parametro '{}' debe ser un numero".format(nombre))
