"""Identidad y permisos.

Acuerdo del equipo (dia 1): este servicio NO valida tokens JWT.
Quien valida el token es el API Gateway; despues reenvia la identidad en
tres cabeceras:

    X-Usuario-Id   quien hace la peticion
    X-Empresa-Id   a que empresa pertenece  (RNF19: los datos de una empresa
                   nunca se mezclan con los de otra)
    X-Rol          administrador | vendedor | encargado_bodega | tienda_web

Las llamadas entre microservicios no pasan por el Gateway: llegan por la red
interna con X-Servicio-Origen y X-Empresa-Id.
"""

from functools import wraps

from flask import g, request

from .errores import NoAutenticado, SinPermiso

# Roles tal como los define el contrato del Gateway.
ADMIN = "administrador"
VENDEDOR = "vendedor"
BODEGA = "encargado_bodega"
TIENDA_WEB = "tienda_web"


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
        """Texto que se guarda en el kardex para saber quien movio el stock (RF10)."""
        if self.es_interna:
            return "servicio:{}".format(self.servicio)
        return "usuario:{}".format(self.usuario_id)


def leer_identidad():
    """Arma la Identidad a partir de las cabeceras de la peticion.

    Se ejecuta antes de cada peticion y deja el resultado en `g`, que es el
    espacio de Flask donde se guardan datos que duran lo que dura la peticion.
    """
    empresa_id = request.headers.get("X-Empresa-Id")
    g.identidad = Identidad(
        empresa_id=int(empresa_id) if empresa_id and empresa_id.isdigit() else None,
        usuario_id=request.headers.get("X-Usuario-Id"),
        rol=request.headers.get("X-Rol"),
        servicio=request.headers.get("X-Servicio-Origen"),
    )


def identidad():
    """Atajo para leer la identidad desde cualquier ruta."""
    return getattr(g, "identidad", None) or Identidad(empresa_id=None)


def empresa_actual():
    """Devuelve el id de la empresa, o corta la peticion si no llego.

    Toda consulta a la base debe filtrar por este valor. Es la regla que
    impide que una empresa vea los productos de otra.
    """
    actual = identidad()
    if actual.empresa_id is None:
        raise NoAutenticado("Falta la cabecera X-Empresa-Id")
    return actual.empresa_id


def roles_permitidos(*roles):
    """Decorador: deja pasar solo a los roles indicados.

    Se usa encima de la funcion de la ruta:

        @bp.post("/productos")
        @roles_permitidos(ADMIN, BODEGA)
        def crear_producto(): ...

    Las llamadas internas (de otro microservicio) pasan sin revisar rol,
    porque un servicio no tiene rol; su permiso se revisa con solo_interno.
    """

    def decorador(funcion):
        @wraps(funcion)  # conserva el nombre de la funcion original
        def envoltura(*args, **kwargs):
            actual = identidad()
            if actual.empresa_id is None:
                raise NoAutenticado("Falta la identidad en las cabeceras")
            if actual.es_interna:
                return funcion(*args, **kwargs)
            if actual.rol not in roles:
                raise SinPermiso(
                    "El rol '{}' no puede realizar esta operacion".format(actual.rol or "desconocido")
                )
            return funcion(*args, **kwargs)

        return envoltura

    return decorador


def solo_interno(*servicios):
    """Decorador: la ruta solo acepta llamadas de ciertos microservicios.

    Protege los endpoints internos, como el descuento de stock que solo
    debe poder pedir Ventas. Si alguien intenta llegar desde afuera (por el
    Gateway) no trae X-Servicio-Origen y recibe un 403.
    """

    def decorador(funcion):
        @wraps(funcion)
        def envoltura(*args, **kwargs):
            actual = identidad()
            if actual.empresa_id is None:
                raise NoAutenticado("Falta la cabecera X-Empresa-Id")
            if not actual.es_interna:
                raise SinPermiso("Esta ruta es interna: no se llama desde el Gateway")
            if servicios and actual.servicio not in servicios:
                raise SinPermiso(
                    "El servicio '{}' no puede llamar esta ruta".format(actual.servicio)
                )
            return funcion(*args, **kwargs)

        return envoltura

    return decorador
