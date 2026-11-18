"""Fabrica de la aplicacion Flask del microservicio de Inventario.

Aqui se arma la aplicacion: se carga la configuracion, se conecta la base de
datos, se registran los manejadores de error, las rutas y la pagina de Swagger.
"""

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
    """Escribe cada linea de log como un JSON.

    El acuerdo del equipo (RNF10, observabilidad) es que los tres escribamos
    los logs igual, en una sola linea y en JSON, para poder leerlos con
    `kubectl logs` y buscar por requestId cuando una peticion cruza varios
    servicios.
    """

    def format(self, registro):
        linea = {
            "servicio": Config.NOMBRE_SERVICIO,
            "nivel": registro.levelname,
            "mensaje": registro.getMessage(),
            # getattr con valor por defecto: no todas las lineas de log
            # ocurren dentro de una peticion, y entonces no hay requestId.
            "requestId": getattr(registro, "request_id", None),
        }
        if registro.exc_info:
            linea["traza"] = self.formatException(registro.exc_info)
        return json.dumps(linea, ensure_ascii=False)


def _configurar_logs(app):
    """Manda los logs a la salida estandar en formato JSON.

    En contenedores no se escriben archivos de log: todo va a la salida
    estandar y Docker o Kubernetes se encargan de recogerla.
    """
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

    # Conecta SQLAlchemy con esta aplicacion.
    db.init_app(app)

    # Convierte nuestras excepciones en respuestas {error, detalle}.
    registrar_manejadores(app)

    @app.before_request
    def _antes_de_cada_peticion():
        """Se ejecuta antes de atender cualquier peticion."""
        # Identificador unico para seguir la peticion en los logs de todos
        # los servicios. Si el Gateway ya mando uno, se respeta.
        g.request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:12]
        # Deja en `g` quien hace la peticion (empresa, usuario, rol).
        leer_identidad()

    @app.after_request
    def _despues_de_cada_peticion(respuesta):
        """Deja una linea de log por peticion y devuelve el requestId."""
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
    # Cada grupo de rutas vive en su propio archivo (un Blueprint de Flask)
    # y se registra aqui. Se importan dentro de la funcion para evitar
    # importaciones circulares.
    from .rutas.alertas import bp as bp_alertas
    from .rutas.bodegas import bp as bp_bodegas
    from .rutas.categorias import bp as bp_categorias
    from .rutas.movimientos import bp as bp_movimientos
    from .rutas.productos import bp as bp_productos
    from .rutas.salud import bp as bp_salud
    from .rutas.stock import bp as bp_stock

    for bp in (bp_salud, bp_categorias, bp_productos, bp_bodegas, bp_stock,
               bp_movimientos, bp_alertas):
        app.register_blueprint(bp)

    # --- Swagger (RNF08) ---
    _publicar_swagger(app)

    # --- Tablas ---
    if app.config.get("CREAR_TABLAS"):
        # create_all crea las tablas que falten. No modifica las que ya
        # existen: si se cambia una columna hay que borrar la tabla o migrar.
        with app.app_context():
            db.create_all()

    return app


def _publicar_swagger(app):
    """Publica el contrato OpenAPI en /docs para poder probarlo en el navegador.

    No se escribe la documentacion a mano: se sirve el mismo archivo
    inventario-openapi.yaml que disenamos en la Entrega 2, de modo que la
    pagina y el contrato nunca se desincronicen.
    """
    ruta_contrato = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs",
                                 "inventario-openapi.yaml")
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
