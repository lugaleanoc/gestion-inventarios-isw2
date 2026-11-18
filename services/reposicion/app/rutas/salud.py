"""Endpoint de salud: lo usa Kubernetes para saber si el contenedor sirve."""

from flask import Blueprint, jsonify

from ..config import Config
from ..extensiones import db

bp = Blueprint("salud", __name__)


@bp.get("/health")
def salud():
    """GET /health (publico). 200 si el servicio y su base estan en pie."""
    try:
        db.session.execute(db.text("SELECT 1"))
        estado, codigo = "ok", 200
    except Exception:  # noqa: BLE001
        estado, codigo = "sin_base_de_datos", 503
    return jsonify({"servicio": Config.NOMBRE_SERVICIO, "estado": estado}), codigo
