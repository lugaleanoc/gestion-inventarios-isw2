from functools import wraps

from flask import g, request

from .config import ROL_ADMIN, ROL_BODEGA, ROLES
from .errores import ApiError

ADM_BOD = (ROL_ADMIN, ROL_BODEGA)
ADM = (ROL_ADMIN,)
TODOS = None


def faltan_headers(detalle):
    return ApiError(401, "FALTAN_HEADERS", detalle)


def sin_permiso(detalle):
    return ApiError(403, "SIN_PERMISO", detalle)


def _empresa_id():
    bruto = request.headers.get("X-Empresa-Id", "").strip()
    if not bruto:
        return None
    if not bruto.isdigit() or int(bruto) < 1:
        raise ApiError(400, "DATOS_INVALIDOS", "El header X-Empresa-Id debe ser un entero positivo")
    return int(bruto)


def _nombre_servicio(valor):
    nombre = valor.strip().lower()
    return nombre[: -len("-service")] if nombre.endswith("-service") else nombre


def requiere(roles, origenes=()):
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            origen = request.headers.get("X-Servicio-Origen")
            empresa_id = _empresa_id()
            g.rol = None
            g.usuario_id = None
            g.origen = None
            if origen is not None:
                if _nombre_servicio(origen) not in origenes:
                    raise sin_permiso("El servicio de origen no tiene permiso para esta ruta")
                if empresa_id is None:
                    raise faltan_headers("Falta X-Empresa-Id")
                g.origen = _nombre_servicio(origen)
            else:
                if empresa_id is None:
                    raise faltan_headers("Falta X-Empresa-Id")
                rol = request.headers.get("X-Rol", "").strip().lower()
                if not rol:
                    raise faltan_headers("Falta X-Rol")
                if rol not in ROLES:
                    raise sin_permiso("Rol no reconocido")
                if roles is not TODOS and rol not in roles:
                    raise sin_permiso("El rol no tiene permiso para esta operación")
                g.rol = rol
                g.usuario_id = request.headers.get("X-Usuario-Id")
            g.empresa_id = empresa_id
            return funcion(*args, **kwargs)

        return envoltura

    return decorador
