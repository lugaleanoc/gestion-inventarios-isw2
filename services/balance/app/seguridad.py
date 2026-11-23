"""Identidad y permisos.

Acuerdo del equipo: este servicio NO valida tokens JWT.
Quien valida el token es el API Gateway; despues reenvia la identidad en
tres headers:

    X-Usuario-Id   quien hace la peticion
    X-Empresa-Id   a que empresa pertenece  (RNF19: los datos de una empresa
                   nunca se mezclan con los de otra)
    X-Rol          administrador | vendedor | encargado_bodega | tienda_web

Las llamadas entre microservicios no pasan por el Gateway: llegan por la red
interna con X-Servicio-Origen y X-Empresa-Id.

Reglas:
    - Falta X-Empresa-Id                       -> 401 FALTAN_HEADERS
    - El rol o el servicio no tiene permiso    -> 403 SIN_PERMISO
"""

from functools import wraps

from flask import g, request

from .errores import FaltanHeaders, SinPermiso

# Roles tal como los define el contrato del Gateway.
ADMIN = "administrador"
VENDEDOR = "vendedor"
BODEGA = "encargado_bodega"
TIENDA_WEB = "tienda_web"
TODOS_LOS_ROLES = (ADMIN, VENDEDOR, BODEGA, TIENDA_WEB)


class Identidad:
    """Quien esta haciendo la peticion actual."""

    def __init__(self, empresa_id, usuario_id=None, rol=None, servicio=None):
        self.empresa_id = empresa_id
        self.usuario_id = usuario_id
        self.rol = rol
        self.servicio = servicio  # nombre del microservicio, si es llamada interna

    @property
    def es_interna(self):
        """True si quien llama es otro microservicio y no una persona."""
        return self.servicio is not None

    def quien(self):
        """Texto para guardar quien hizo una operacion (usuario o servicio)."""
        if self.es_interna:
            return self.servicio
        return str(self.usuario_id)


def leer_identidad():
    """Arma la Identidad a partir de los headers de la peticion.

    Se ejecuta antes de cada peticion y deja el resultado en `g`, que es el
    espacio de Flask donde se guardan datos que duran lo que dura la peticion.
    """
    empresa_id = request.headers.get("X-Empresa-Id", "")
    g.identidad = Identidad(
        # Si llega algo que no es un numero, se trata como si no hubiera llegado.
        empresa_id=int(empresa_id) if empresa_id.isdigit() else None,
        usuario_id=request.headers.get("X-Usuario-Id"),
        rol=request.headers.get("X-Rol"),
        servicio=request.headers.get("X-Servicio-Origen"),
    )


def identidad():
    """Atajo para leer la identidad desde cualquier ruta."""
    return getattr(g, "identidad", None) or Identidad(empresa_id=None)


def empresa_actual():
    """Devuelve el id de la empresa, o corta la peticion con 401 si no llego.

    Toda consulta a la base debe filtrar por este valor. Es la regla que
    impide que una empresa vea los datos de otra.
    """
    actual = identidad()
    if actual.empresa_id is None:
        raise FaltanHeaders("Falta el header X-Empresa-Id")
    return actual.empresa_id


def permitir(roles=(), servicios=()):
    """Decorador: define QUIEN puede llamar una ruta.

    roles:     roles de usuario (llamadas que vienen del Gateway).
    servicios: microservicios que pueden llamarla por la red interna.

    Ejemplo, una ruta que usan el administrador y el servicio de Reportes:

        @bp.get("/resumen")
        @permitir(roles=[ADMIN], servicios=["reportes"])
        def resumen(): ...

    Si una ruta no pone `servicios`, ningun microservicio puede llamarla:
    asi un servicio no puede hacer cosas que el contrato solo permite al
    administrador.
    """

    def decorador(funcion):
        @wraps(funcion)  # conserva el nombre de la funcion original
        def envoltura(*args, **kwargs):
            actual = identidad()
            empresa_actual()  # 401 si falta X-Empresa-Id

            if actual.es_interna:
                if actual.servicio not in servicios:
                    raise SinPermiso(
                        "El servicio '{}' no puede llamar esta ruta".format(actual.servicio)
                    )
            elif actual.rol not in roles:
                raise SinPermiso(
                    "El rol '{}' no puede realizar esta operacion".format(actual.rol or "desconocido")
                )
            return funcion(*args, **kwargs)

        return envoltura

    return decorador
