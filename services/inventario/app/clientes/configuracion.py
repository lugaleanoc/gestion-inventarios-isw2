"""Llamadas al microservicio de Configuracion (lo hace Jasmin).

De alli sacamos el stock minimo de cada producto, que es el umbral que
dispara las alertas (RF09).

Mientras ese servicio no exista, esta funcion devuelve el valor de la
variable de entorno STOCK_MINIMO_POR_DEFECTO. Eso permite trabajar y probar
Inventario sin esperar a nadie; cuando Configuracion este listo no hay que
cambiar codigo, solo apuntar la variable CONFIGURACION_URL.
"""

from ..config import Config
from .http import llamar


def stock_minimo_de(producto_id):
    """Devuelve el stock minimo vigente del producto."""
    respuesta = llamar(
        "configuracion",
        "GET",
        "{}/api/configuracion/stock-minimo/{}".format(Config.CONFIGURACION_URL, producto_id),
        # No es obligatorio: si Configuracion no responde, seguimos con el
        # valor por defecto en vez de bloquear una venta o una consulta.
        obligatorio=False,
    )
    if respuesta is not None and respuesta.status_code == 200:
        return respuesta.json().get("stockMinimo", Config.STOCK_MINIMO_POR_DEFECTO)
    return Config.STOCK_MINIMO_POR_DEFECTO
