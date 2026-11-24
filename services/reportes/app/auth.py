from functools import wraps

from flask import g, request

from .config import ROL_ADMIN, ROL_BODEGA, ROL_VENDEDOR, ROLES
from .errores import ApiError

ADM = (ROL_ADMIN,)
ADM_VEN = (ROL_ADMIN, ROL_VENDEDOR)
ADM_BOD = (ROL_ADMIN, ROL_BODEGA)
TODOS = None


def requiere(roles):
    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            if request.headers.get("X-Servicio-Origen") is not None:
                raise ApiError(403, "SIN_PERMISO", "Esta ruta no admite llamadas entre servicios")
            bruto = request.headers.get("X-Empresa-Id", "").strip()
            if not bruto:
                raise ApiError(401, "FALTAN_HEADERS", "Falta X-Empresa-Id")
            if not bruto.isdigit() or int(bruto) < 1:
                raise ApiError(400, "DATOS_INVALIDOS", "El header X-Empresa-Id debe ser un entero positivo")
            rol = request.headers.get("X-Rol", "").strip().lower()
            if not rol:
                raise ApiError(401, "FALTAN_HEADERS", "Falta X-Rol")
            if rol not in ROLES:
                raise ApiError(403, "SIN_PERMISO", "Rol no reconocido")
            if roles is not TODOS and rol not in roles:
                raise ApiError(403, "SIN_PERMISO", "El rol no tiene permiso para este reporte")
            g.empresa_id = int(bruto)
            g.rol = rol
            g.usuario_id = request.headers.get("X-Usuario-Id")
            return funcion(*args, **kwargs)

        return envoltura

    return decorador
