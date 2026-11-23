"""Fabrica de la aplicacion Flask del microservicio de Ventas.

Aqui se arma la aplicacion: se carga la configuracion, se conecta la base de
datos, se registran los manejadores de error, las rutas y la pagina de Swagger.
Sigue la misma estructura que Inventario y Reposicion.
"""

import json
import logging
import os
import sys
import time
import uuid

from flask import Flask, g, request
from sqlalchemy.exc import OperationalError, ProgrammingError

from .config import Config
from .errores import registrar_manejadores
from .extensiones import db
from .seguridad import leer_identidad


class FormatoLogJSON(logging.Formatter):
    """Escribe cada linea de log como un JSON (acuerdo del equipo, RNF10)."""

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
    """Manda los logs a la salida estandar en formato JSON."""
    manejador = logging.StreamHandler(sys.stdout)
    manejador.setFormatter(FormatoLogJSON())
    app.logger.handlers = [manejador]
    app.logger.setLevel(logging.INFO)


def crear_app(config=None):
    """Construye y devuelve la aplicacion lista para usar.

    config: permite pasar otra configuracion en las pruebas (por ejemplo
            apuntando a una base de datos distinta).
    """
    app = Flask(__name__)
    app.config.from_object(config or Config)
    _configurar_logs(app)

    db.init_app(app)
    registrar_manejadores(app)

    @app.before_request
    def _antes_de_cada_peticion():
        # Identificador para seguir la peticion en los logs de todos los servicios.
        g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        # Deja en `g` quien hace la peticion (empresa, usuario, rol).
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

    # --- Rutas ---
    from .rutas.salud import bp as bp_salud
    from .rutas.ventas import bp as bp_ventas

    for bp in (bp_salud, bp_ventas):
        app.register_blueprint(bp)

    # --- Swagger (RNF08) ---
    _publicar_swagger(app)

    # --- Tablas ---
    if app.config.get("CREAR_TABLAS"):
        _crear_tablas(app)

    return app


def _crear_tablas(app):
    """Crea las tablas que no existan, reintentando hasta que MySQL responda.

    Al hacer  docker compose up  el contenedor del servicio puede arrancar
    antes de que MySQL acepte conexiones. Tambien pasa que gunicorn arranca
    2 workers a la vez y los dos intentan crear las tablas: si el otro se
    adelanto, el error se resuelve solo en el siguiente intento, porque
    create_all ve que las tablas ya existen y no hace nada.
    """
    intentos = app.config.get("INTENTOS_BD", 30)
    espera = app.config.get("ESPERA_BD", 3)
    with app.app_context():
        for intento in range(1, intentos + 1):
            try:
                db.create_all()
                app.logger.info("Tablas listas (intento %s)", intento)
                return
            except (OperationalError, ProgrammingError) as exc:
                db.session.rollback()
                app.logger.warning("MySQL no responde todavia (intento %s/%s): %s",
                                   intento, intentos, exc.__class__.__name__)
                time.sleep(espera)
    raise RuntimeError("No se pudo conectar a MySQL despues de {} intentos".format(intentos))


def _publicar_swagger(app):
    """Publica el contrato OpenAPI en /docs para poder probarlo en el navegador.

    Se sirve el mismo ventas-openapi.yaml de docs/api, asi la pagina
    y el contrato no se desincronizan.
    """
    ruta_contrato = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs",
                                 "ventas-openapi.yaml")
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
        # Que falte Swagger no debe impedir que el servicio arranque.
        app.logger.warning("No se pudo publicar Swagger: %s", exc)
