"""Llamadas al microservicio de Reposicion (tambien es mio).

Cuando el total de un producto queda en o por debajo del minimo, Inventario
le avisa a Reposicion para que cree la solicitud automatica de compra
(decisiones 3 y 4 de la Entrega 2).
"""

from ..config import Config
from .http import llamar


def avisar_stock_bajo(producto_id, stock_actual):
    """Pide a Reposicion que abra una solicitud automatica para el producto.

    Si Reposicion no responde no se cancela nada: el movimiento de inventario
    que disparo el aviso ya es valido. Solo queda anotado en el log.
    """
    llamar(
        "reposicion",
        "POST",
        "{}/api/reposicion/solicitudes/automaticas".format(Config.REPOSICION_URL),
        json={"productoId": producto_id, "stockActual": stock_actual},
        obligatorio=False,
    )
