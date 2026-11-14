"""Clientes HTTP hacia los otros microservicios.

Toda comunicacion entre servicios es REST (RNF17). Estas llamadas NO pasan
por el API Gateway: van directo por la red interna, identificandose con las
cabeceras X-Servicio-Origen y X-Empresa-Id.
"""

from .configuracion import stock_minimo_de
from .proveedores import proveedor_existe
from .reposicion import avisar_stock_bajo

__all__ = ["stock_minimo_de", "proveedor_existe", "avisar_stock_bajo"]
