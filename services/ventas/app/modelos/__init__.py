"""Modelos de datos del microservicio de Ventas (base ventas_db).

Regla de microservicios (RNF02): empresaId, localId, bodegaId y productoId
son referencias LOGICAS a datos de otros servicios (Configuracion e
Inventario). No hay llaves foraneas hacia esas bases.

La unica llave foranea es items_venta -> ventas, porque las dos tablas son
de este mismo servicio.
"""

from .venta import ItemVenta, Venta

__all__ = ["Venta", "ItemVenta"]
