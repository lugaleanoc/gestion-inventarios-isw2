"""Llamadas al microservicio de Proveedores.

Sirve para saber a que proveedor se le compra un producto. Si el producto
tiene varios, se toma el marcado como principal.
"""

from ..config import Config
from .http import llamar


def proveedor_principal_de(producto_id):
    """Devuelve el proveedorId principal del producto, o None.

    No es obligatorio: una solicitud sin proveedor se puede crear igual y
    el administrador decide despues. El contrato permite proveedorId nulo.
    """
    respuesta = llamar(
        "proveedores",
        "GET",
        "{}/api/proveedores/por-producto/{}".format(Config.PROVEEDORES_URL, producto_id),
        obligatorio=False,
    )
    if respuesta is None or respuesta.status_code != 200:
        return None

    asociaciones = respuesta.json()
    if not asociaciones:
        return None

    # Primero el marcado como principal; si ninguno lo esta, el primero.
    for asociacion in asociaciones:
        if asociacion.get("principal"):
            return asociacion.get("proveedorId")
    return asociaciones[0].get("proveedorId")
