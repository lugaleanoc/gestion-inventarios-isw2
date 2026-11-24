from flask import Blueprint, current_app, jsonify

from .config import ROL_ADMIN
from .db import get_db
from .errores import ApiError
from .resiliencia import ServicioNoDisponible
from .routes_admin import crear_usuario
from .routes_auth import exigir_contrasena_fuerte
from .validar import correo_valido, cuerpo_json, objeto_obligatorio, texto

bp = Blueprint("empresas", __name__, url_prefix="/api/empresas")


def registro_duplicado():
    return ApiError(409, "REGISTRO_DUPLICADO", "El NIT o el correo ya están registrados")


def crear_empresa_en_configuracion(nombre, nit):
    cfg = current_app.config
    sesion = current_app.extensions["sesion_http"]
    url = f"{cfg['SERVICIOS']['configuracion']}/api/configuracion/empresas"
    try:
        respuesta = current_app.extensions["resiliencia"].llamar(
            "configuracion",
            lambda: sesion.post(
                url,
                json={"nombre": nombre, "nit": nit},
                headers={"X-Servicio-Origen": "gateway"},
                timeout=(cfg["TIMEOUT_CONEXION"], cfg["TIMEOUT_LECTURA"]),
            ),
            idempotente=False,
        )
    except ServicioNoDisponible:
        raise ApiError(503, "SERVICIO_NO_DISPONIBLE", "El servicio de configuración no responde")
    if respuesta.status_code == 409:
        raise registro_duplicado()
    if respuesta.status_code == 400:
        raise ApiError(400, "DATOS_INVALIDOS", "Configuración rechazó los datos de la empresa")
    if respuesta.status_code != 201:
        raise ApiError(503, "SERVICIO_NO_DISPONIBLE", "El servicio de configuración no pudo crear la empresa")
    try:
        empresa = respuesta.json()
        int(empresa["empresaId"])
    except (ValueError, KeyError, TypeError):
        raise ApiError(503, "SERVICIO_NO_DISPONIBLE", "El servicio de configuración respondió algo inesperado")
    return empresa


@bp.post("/registro")
def registrar_empresa():
    datos = cuerpo_json()
    nombre_empresa = texto(datos, "nombreEmpresa", 150, obligatorio=True)
    nit = texto(datos, "nit", 30, obligatorio=True)
    admin = objeto_obligatorio(datos, "administrador")
    nombre = texto(admin, "nombre", 150, obligatorio=True, etiqueta="administrador.nombre")
    correo = correo_valido(admin, "correo", etiqueta="administrador.correo")
    contrasena = admin.get("contrasena")
    exigir_contrasena_fuerte(contrasena)
    db = get_db()
    if db.fila("SELECT usuario_id FROM usuarios WHERE correo = %s", (correo,)):
        raise registro_duplicado()
    empresa = crear_empresa_en_configuracion(nombre_empresa, nit)
    usuario = crear_usuario(db, int(empresa["empresaId"]), nombre, correo, contrasena, ROL_ADMIN)
    return jsonify({"empresaId": usuario["empresa_id"], "usuarioId": usuario["usuario_id"]}), 201
