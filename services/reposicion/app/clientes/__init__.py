"""Clientes HTTP hacia los otros microservicios (RNF17).

Reposicion llama a tres servicios:
    Inventario     para comprobar el producto y registrar la entrada
    Proveedores    para saber a quien se le compra
    Configuracion  para saber el stock minimo del producto
"""

from .configuracion import stock_minimo_de
from .inventario import producto_de, registrar_entrada
from .proveedores import proveedor_principal_de

__all__ = ["stock_minimo_de", "producto_de", "registrar_entrada", "proveedor_principal_de"]
