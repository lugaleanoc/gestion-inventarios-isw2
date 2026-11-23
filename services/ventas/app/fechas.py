"""Fechas en hora de Colombia (acuerdo del equipo: America/Bogota).

MySQL guarda las fechas sin zona horaria. Por eso:
  - se guardan "a secas" (sin zona), pero siempre en hora de Bogota;
  - al responder se les pega la zona, y el JSON queda como
    "2026-11-20T15:42:10-05:00".

La imagen python:3.12-slim no trae la base de zonas horarias del sistema;
la trae el paquete tzdata (esta en requirements.txt).
"""

from datetime import datetime
from zoneinfo import ZoneInfo

BOGOTA = ZoneInfo("America/Bogota")


def ahora():
    """Fecha y hora actual de Colombia, sin zona, lista para guardar en MySQL."""
    return datetime.now(BOGOTA).replace(tzinfo=None)


def a_texto(fecha):
    """Convierte una fecha guardada en texto ISO 8601 con la zona de Bogota."""
    if fecha is None:
        return None
    return fecha.replace(tzinfo=BOGOTA).isoformat()
