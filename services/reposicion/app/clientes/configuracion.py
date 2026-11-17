"""Llamadas al microservicio de Configuracion.

Da el stock minimo del producto, que sirve para calcular cuanto sugerir
que se compre. Mientras ese servicio no exista, se usa el valor de la
variable de entorno STOCK_MINIMO_POR_DEFECTO.
"""

from ..config import Config
from .http import llamar


def stock_minimo_de(producto_id):
    """Devuelve el stock minimo vigente del producto."""
    respuesta = llamar(
        "configuracion",
        "GET",
        "{}/api/configuracion/stock-minimo/{}".format(Config.CONFIGURACION_URL, producto_id),
        obligatorio=False,
    )
    if respuesta is not None and respuesta.status_code == 200:
        return respuesta.json().get("stockMinimo", Config.STOCK_MINIMO_POR_DEFECTO)
    return Config.STOCK_MINIMO_POR_DEFECTO
