import time
import uuid
from functools import wraps

from flask import current_app, g, request

from .config import ROL_TIENDA
from .db import get_db
from .errores import ApiError
from .jwt_utils import TokenError, firmar, verificar
from .tiempo import desde_epoch, iso


def emitir_token(tipo, sujeto_id, empresa_id, rol):
    cfg = current_app.config
    minutos = cfg["JWT_TIENDA_EXPIRA_MINUTOS"] if tipo == "tienda" else cfg["JWT_EXPIRA_MINUTOS"]
    emitido = int(time.time())
    exp = emitido + minutos * 60
    claims = {
        "sub": sujeto_id,
        "emp": empresa_id,
        "rol": rol,
        "tip": tipo,
        "jti": uuid.uuid4().hex,
        "iat": emitido,
        "exp": exp,
    }
    return firmar(claims, cfg["JWT_SECRET"]), iso(desde_epoch(exp))


def autenticar():
    cabecera = request.headers.get("Authorization", "")
    if not cabecera.lower().startswith("bearer ") or not cabecera[7:].strip():
        raise ApiError(401, "TOKEN_AUSENTE", "Falta el token en el header Authorization")
    try:
        claims = verificar(cabecera[7:].strip(), current_app.config["JWT_SECRET"])
    except TokenError as exc:
        raise ApiError(401, exc.codigo, exc.detalle)
    db = get_db()
    if db.fila("SELECT jti FROM tokens_revocados WHERE jti = %s", (claims["jti"],)):
        raise ApiError(401, "TOKEN_INVALIDO", "La sesión fue cerrada")
    if claims["tip"] == "tienda":
        fila = db.fila("SELECT empresa_id, activo FROM tiendas_web WHERE tienda_id = %s", (claims["sub"],))
        rol = ROL_TIENDA
    else:
        fila = db.fila("SELECT empresa_id, rol, activo FROM usuarios WHERE usuario_id = %s", (claims["sub"],))
        rol = fila["rol"] if fila else None
    if fila is None or not fila["activo"]:
        raise ApiError(401, "TOKEN_INVALIDO", "La cuenta asociada al token está inactiva")
    g.claims = claims
    g.tipo = claims["tip"]
    g.sujeto_id = claims["sub"]
    g.empresa_id = fila["empresa_id"]
    g.rol = rol
    return claims


def requiere_sesion(roles=None, solo_usuarios=False):
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            autenticar()
            if solo_usuarios and g.tipo != "usuario":
                raise ApiError(403, "SIN_PERMISO", "Esta operación es solo para usuarios")
            if roles is not None and g.rol not in roles:
                raise ApiError(403, "SIN_PERMISO", "El rol no tiene permiso para esta operación")
            return funcion(*args, **kwargs)

        return envoltura

    return decorador
