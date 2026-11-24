import posixpath

from flask import Blueprint, Response, current_app, g, request

from .config import RUTAS_INTERNAS
from .errores import ApiError
from .resiliencia import ServicioNoDisponible
from .sesion import autenticar

bp = Blueprint("proxy", __name__, url_prefix="/api")

METODOS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
HEADERS_REENVIADOS = ("Content-Type", "Accept", "Accept-Language")


def normalizar(ruta):
    limpia = posixpath.normpath(ruta)
    return limpia if limpia.startswith("/") else "/" + limpia


@bp.route("/<servicio>", methods=METODOS)
@bp.route("/<servicio>/<path:resto>", methods=METODOS)
def reenviar(servicio, resto=""):
    cfg = current_app.config
    base = cfg["SERVICIOS"].get(servicio)
    if base is None:
        raise ApiError(404, "RUTA_NO_ENCONTRADA", "La ruta no existe")
    autenticar()
    ruta = request.path
    if ".." in ruta.split("/"):
        raise ApiError(400, "DATOS_INVALIDOS", "La ruta no es válida")
    if normalizar(ruta) in RUTAS_INTERNAS:
        raise ApiError(403, "SIN_PERMISO", "Esta ruta solo la pueden llamar otros servicios")
    headers = {nombre: request.headers[nombre] for nombre in HEADERS_REENVIADOS if nombre in request.headers}
    headers["X-Empresa-Id"] = str(g.empresa_id)
    headers["X-Usuario-Id"] = str(g.sujeto_id)
    headers["X-Rol"] = g.rol
    url = base + ruta
    consulta = request.query_string.decode("latin-1")
    if consulta:
        url += "?" + consulta
    sesion = current_app.extensions["sesion_http"]
    cuerpo = request.get_data()
    metodo = request.method

    def enviar():
        return sesion.request(
            metodo,
            url,
            data=cuerpo,
            headers=headers,
            timeout=(cfg["TIMEOUT_CONEXION"], cfg["TIMEOUT_LECTURA"]),
            allow_redirects=True,
        )

    try:
        respuesta = current_app.extensions["resiliencia"].llamar(
            servicio, enviar, idempotente=metodo in ("GET", "PUT", "DELETE")
        )
    except ServicioNoDisponible:
        raise ApiError(503, "SERVICIO_NO_DISPONIBLE", f"El servicio {servicio} no responde")
    return Response(
        respuesta.content,
        status=respuesta.status_code,
        content_type=respuesta.headers.get("Content-Type"),
    )
