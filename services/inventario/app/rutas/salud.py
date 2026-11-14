"""Endpoint de salud.

Todos los servicios del sistema exponen GET /health, publico y sin token.
Kubernetes lo usa para saber si el contenedor esta vivo y si ya puede
recibir trafico; si deja de responder, lo reinicia solo.
"""

from flask import Blueprint, jsonify

from ..config import Config
from ..extensiones import db

bp = Blueprint("salud", __name__)


@bp.get("/health")
def salud():
    """Responde 200 si el servicio y su base de datos estan en pie."""
    try:
        # Consulta minima para comprobar que la conexion a MySQL funciona.
        db.session.execute(db.text("SELECT 1"))
        estado = "ok"
        codigo = 200
    except Exception:  # noqa: BLE001
        # El servicio responde, pero no sirve de nada sin su base: 503.
        estado = "sin_base_de_datos"
        codigo = 503
    return jsonify({"servicio": Config.NOMBRE_SERVICIO, "estado": estado}), codigo
