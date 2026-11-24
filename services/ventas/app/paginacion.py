"""Paginacion y lectura de parametros de la URL.

Igual que en Inventario. Los listados aceptan `pagina` y `porPagina`
(maximo 100) y responden con esta forma:

    {"datos": [...], "paginacion": {"pagina": 1, "porPagina": 20, "total": 57}}
"""

from datetime import date, datetime, timedelta

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
    """Aplica la paginacion a una consulta de SQLAlchemy ya filtrada."""
    pagina, por_pagina = parametros_de_pagina()
    total = consulta.count()  # cuenta sin traer las filas
    filas = consulta.offset((pagina - 1) * por_pagina).limit(por_pagina).all()
    return {
        "datos": [a_dic(fila) for fila in filas],
        "paginacion": {"pagina": pagina, "porPagina": por_pagina, "total": total},
    }


def entero_de_url(nombre, por_defecto=None, obligatorio=False):
    """Lee un parametro numerico de la URL (por ejemplo ?localId=1)."""
    valor = request.args.get(nombre)
    if valor is None or valor == "":
        if obligatorio:
            raise DatosInvalidos("Falta el parametro '{}'".format(nombre))
        return por_defecto
    try:
        return int(valor)
    except ValueError:
        raise DatosInvalidos("El parametro '{}' debe ser un numero".format(nombre))


def opcion_de_url(nombre, opciones):
    """Lee un parametro que debe ser uno de los valores permitidos (o no venir)."""
    valor = request.args.get(nombre)
    if valor in (None, ""):
        return None
    if valor not in opciones:
        raise DatosInvalidos("El parametro '{}' debe ser: {}".format(nombre, ", ".join(opciones)))
    return valor


def fecha_de_url(nombre, por_defecto=None, obligatorio=False):
    """Lee una fecha AAAA-MM-DD de la URL y la devuelve como date."""
    valor = request.args.get(nombre)
    if valor in (None, ""):
        if obligatorio:
            raise DatosInvalidos("Falta el parametro '{}' (formato AAAA-MM-DD)".format(nombre))
        return por_defecto
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise DatosInvalidos("El parametro '{}' debe tener formato AAAA-MM-DD".format(nombre))


def rango_del_dia(desde, hasta):
    """Convierte dos fechas en el rango [desde 00:00, hasta+1 00:00) para filtrar fecha_hora.

    Se usa "menor que el dia siguiente" para incluir todo el ultimo dia,
    hasta las 23:59:59.
    """
    inicio = datetime.combine(desde, datetime.min.time())
    fin = datetime.combine(hasta + timedelta(days=1), datetime.min.time())
    return inicio, fin
