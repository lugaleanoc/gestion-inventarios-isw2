"""Modelos de datos del microservicio de Configuracion (base configuracion_db).

Regla de microservicios (RNF02): `productoId` es una referencia logica al
producto de Inventario; aqui no hay llave foranea hacia esa base.
Tampoco hay llaves foraneas entre las tablas de este servicio y empresas:
empresa_id se valida con el header X-Empresa-Id.

Este archivo solo reexporta las clases para poder escribir:
    from app.modelos import Empresa, Local, StockMinimo
"""

from .empresa import Empresa
from .local import Local
from .preferencias import ConfigAlertas, ConfigDashboard
from .stock_minimo import StockMinimo

__all__ = ["Empresa", "Local", "StockMinimo", "ConfigAlertas", "ConfigDashboard"]
