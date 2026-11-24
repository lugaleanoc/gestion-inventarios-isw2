"""Modelos de datos del microservicio de Balance Diario (base balance_db).

Regla de microservicios (RNF02): empresaId, localId y ventaId son
referencias LOGICAS a datos de Configuracion y Ventas; no hay llaves
foraneas hacia esas bases.
"""

from .movimiento import Movimiento

__all__ = ["Movimiento"]
