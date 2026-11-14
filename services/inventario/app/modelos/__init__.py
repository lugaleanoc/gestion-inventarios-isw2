"""Modelos de datos del microservicio de Inventario.

Cada clase representa una tabla de la base `inventario_db`, siguiendo el
modelo entidad-relacion de la Entrega 2.

Regla de microservicios (RNF02): aqui NO hay llaves foraneas hacia tablas de
otros servicios. Campos como `localId` o `proveedorId` guardan el numero,
pero la base no puede verificarlo porque esa tabla vive en otra base de
datos; se llama "referencia logica" y se valida llamando al otro servicio.

Este archivo solo reexporta las clases para poder escribir:
    from app.modelos import Producto, Stock
"""

from .bodega import Bodega
from .categoria import Categoria
from .movimiento import Movimiento, TIPOS_MOVIMIENTO
from .producto import Producto
from .stock import Stock

__all__ = ["Bodega", "Categoria", "Movimiento", "TIPOS_MOVIMIENTO", "Producto", "Stock"]
