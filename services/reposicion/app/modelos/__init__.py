"""Modelos de datos del microservicio de Reposicion.

Dos tablas, segun el modelo entidad-relacion de la Entrega 2:

    solicitudes -> una peticion de reponer un producto
    ordenes     -> la orden de compra que sale de una solicitud aprobada

Como en todos los servicios, no hay llaves foraneas hacia otras bases
(RNF02): productoId y proveedorId son referencias logicas, porque esos
datos viven en Inventario y en Proveedores.
"""

from .orden import ESTADOS_ORDEN, Orden
from .solicitud import ESTADOS_ABIERTOS, ESTADOS_SOLICITUD, Solicitud

__all__ = ["Orden", "ESTADOS_ORDEN", "Solicitud", "ESTADOS_SOLICITUD", "ESTADOS_ABIERTOS"]
