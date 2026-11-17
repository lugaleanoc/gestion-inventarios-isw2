"""Fabrica de la aplicacion Flask del microservicio de Reposicion."""

import json
import logging
import os
import sys
import uuid

from flask import Flask, g, jsonify, request

from .config import Config
from .errores import registrar_manejadores
from .extensiones import db
from .seguridad import leer_identidad


class FormatoLogJSON(logging.Formatter):
    """Una linea de log por peticion, en JSON (RNF10).

    Los tres integrantes usamos el mismo formato para poder buscar por
    requestId cuando una peticion cruza varios servicios.
    """

    def format(self, registro):
        linea = {
            "servicio": Config.NOMBRE_SERVICIO,
            "nivel": registro.levelname,
            "mensaje": registro.getMessage(),
            "requestId": getattr(registro, "request_id", None),
        }
        if registro.exc_info:
            linea["traza"] = self.formatException(registro.exc_info)
        return json.dumps(linea, ensure_ascii=False)


def _configurar_logs(app):
    """Los logs van a la salida estandar, que es de donde los lee Kubernetes."""
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(FormatoLogJSON())
    app.logger.handlers = [manejador]
    app.logger.setLevel(logging.INFO)


def crear_app(config=None):
    """Construye la aplicacion ya configurada y lista para usar."""
    app = Flask(__name__)
    app.config.from_object(config or Config)
    _configurar_logs(app)

    db.init_app(app)
    registrar_manejadores(app)

    @app.before_request
    def _antes_de_cada_peticion():
        g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        leer_identidad()

    @app.after_request
    def _despues_de_cada_peticion(respuesta):
        app.logger.info(
            "%s %s -> %s",
            request.method,
            request.path,
            respuesta.status_code,
            extra={"request_id": getattr(g, "request_id", None)},
        )
        respuesta.headers["X-Request-Id"] = getattr(g, "request_id", "")
        return respuesta

    from .rutas.ordenes import bp as bp_ordenes
    from .rutas.salud import bp as bp_salud
    from .rutas.solicitudes import bp as bp_solicitudes

    for bp in (bp_salud, bp_solicitudes, bp_ordenes):
        app.register_blueprint(bp)

    _publicar_swagger(app)

    if app.config.get("CREAR_TABLAS"):
        with app.app_context():
            db.create_all()

    return app


def _publicar_swagger(app):
    """Publica el contrato OpenAPI en /docs (RNF08)."""
    ruta_contrato = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs",
                                 "reposicion-openapi.yaml")
    try:
        import yaml
        from flasgger import Swagger
        
        with open(ruta_contrato, "r", encoding="utf-8") as archivo:
            contrato = yaml.safe_load(archivo)

        Swagger(
            app,
            template=contrato,
            config={
                "headers": [],
                "specs": [{"endpoint": "contrato", "route": "/openapi.json"}],
                "static_url_path": "/swagger",
                "swagger_ui": True,
                "specs_route": "/docs/",
            },
        )
    except Exception as exc:  # noqa: BLE001
        app.logger.warning("No se pudo publicar Swagger: %s", exc)
