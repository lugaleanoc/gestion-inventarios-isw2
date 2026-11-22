import requests
from flask import Flask, jsonify
from requests.adapters import HTTPAdapter
from werkzeug.exceptions import HTTPException

from .config import ajustes
from .db import DBNoDisponible, cerrar_db
from .errores import ApiError, respuesta_error
from .routes import bp as reportes_bp

NOMBRES_HTTP = {
    400: "DATOS_INVALIDOS",
    404: "RUTA_NO_ENCONTRADA",
    405: "METODO_NO_PERMITIDO",
    415: "DATOS_INVALIDOS",
}


def crear_sesion_http():
    sesion = requests.Session()
    adaptador = HTTPAdapter(pool_connections=20, pool_maxsize=100)
    sesion.mount("http://", adaptador)
    sesion.mount("https://", adaptador)
    return sesion


def create_app(config=None):
    app = Flask(__name__)
    app.json.sort_keys = False
    app.json.ensure_ascii = False
    app.url_map.strict_slashes = False
    app.config.update(ajustes())
    app.config.update(config or {})
    app.extensions["sesion_http"] = crear_sesion_http()
    app.teardown_appcontext(cerrar_db)
    app.register_blueprint(reportes_bp)

    @app.get("/health")
    def health():
        return jsonify({"estado": "ok", "servicio": "reportes-service"})

    @app.errorhandler(ApiError)
    def manejar_api_error(exc):
        return respuesta_error(exc.status, exc.error, exc.detalle)

    @app.errorhandler(DBNoDisponible)
    def manejar_bd(exc):
        app.logger.error("Base de datos no disponible: %s", exc)
        return respuesta_error(503, "SERVICIO_NO_DISPONIBLE", "La base de datos no responde")

    @app.errorhandler(HTTPException)
    def manejar_http(exc):
        return respuesta_error(exc.code, NOMBRES_HTTP.get(exc.code, "ERROR_HTTP"), exc.description)

    @app.errorhandler(Exception)
    def manejar_error(exc):
        app.logger.exception("Error no controlado")
        return respuesta_error(500, "ERROR_INTERNO", "Ocurrió un error inesperado")

    return app
