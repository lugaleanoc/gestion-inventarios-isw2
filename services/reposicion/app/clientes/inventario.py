"""Llamadas al microservicio de Inventario.

Dos usos:
  - comprobar que el producto existe antes de pedir mas unidades;
  - avisar que llego la mercancia, para que suba el stock.
"""

from ..config import Config
from .http import llamar


def producto_de(producto_id):
    """Devuelve los datos del producto, o None si no existe.

    No es obligatorio: si Inventario no responde al crear una solicitud
    manual, igual se puede registrar la solicitud y revisarla despues.
    """
    respuesta = llamar(
        "inventario",
        "GET",
        "{}/api/inventario/productos/{}".format(Config.INVENTARIO_URL, producto_id),
        obligatorio=False,
    )
    if respuesta is not None and respuesta.status_code == 200:
        return respuesta.json()
    return None


def registrar_entrada(orden_id, producto_id, bodega_id, cantidad):
    """Avisa a Inventario que entro la mercancia de una orden.

    Esta llamada SI es obligatoria: si Inventario no responde, la
    recepcion no se puede dar por hecha, porque el stock no subio. Se
    devuelve 503 y se reintenta mas tarde.

    La ruta de Inventario es idempotente por ordenId: si por un corte de
    red se llama dos veces con la misma orden, no suma el stock dos veces.
    """
    respuesta = llamar(
        "inventario",
        "POST",
        "{}/api/inventario/stock/entradas".format(Config.INVENTARIO_URL),
        json={
            "ordenId": orden_id,
            "items": [
                {"productoId": producto_id, "bodegaId": bodega_id, "cantidad": cantidad}
            ],
        },
        obligatorio=True,
    )
    # 409 significa que esa entrada ya estaba registrada, lo cual para
    # nosotros es un exito: el stock ya subio.
    return respuesta.status_code in (200, 201, 409)
