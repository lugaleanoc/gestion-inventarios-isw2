"""Llamadas al microservicio de Proveedores (lo hace Kevin).

Se usa al crear o editar un producto: como el proveedor vive en otra base de
datos, MySQL no puede verificar que el proveedorId exista. Hay que
preguntarselo al servicio dueno de ese dato (decision 6 de la Entrega 2).
"""

from ..config import Config
from .http import llamar


def proveedor_existe(proveedor_id):
    """True si el proveedor existe y esta activo en esta empresa."""
    if proveedor_id is None:
        return True  # el proveedor es opcional en el contrato
    respuesta = llamar(
        "proveedores",
        "GET",
        "{}/api/proveedores/{}".format(Config.PROVEEDORES_URL, proveedor_id),
        # Obligatorio: si no podemos comprobarlo, preferimos cancelar la
        # creacion del producto antes que guardar un proveedor inventado.
        obligatorio=True,
    )
    return respuesta.status_code == 200
