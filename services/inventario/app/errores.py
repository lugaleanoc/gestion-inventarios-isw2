"""Manejo de errores.

El contrato dice que TODOS los errores del sistema tienen la misma forma:

    {"error": "STOCK_INSUFICIENTE", "detalle": "Hay 2 unidades y se piden 5"}

Para no repetir esa estructura en cada ruta, aqui se define una excepcion
propia (ErrorAPI) y unos manejadores que la convierten en respuesta JSON.
En las rutas basta con hacer:  raise NoEncontrado("El producto no existe")
"""

from flask import jsonify


class ErrorAPI(Exception):
    """Excepcion base de la que heredan todos nuestros errores.

    codigo_http: el numero que viaja en la respuesta (404, 409, ...).
    error:       el codigo en mayusculas que el contrato define.
    """

    codigo_http = 500
    error = "ERROR_INTERNO"

    def __init__(self, detalle, error=None, codigo_http=None):
        super().__init__(detalle)
        self.detalle = detalle
        # Permite cambiar el codigo sin crear una clase nueva, por ejemplo:
        #   raise Conflicto("...", error="STOCK_INSUFICIENTE")
        if error:
            self.error = error
        if codigo_http:
            self.codigo_http = codigo_http

    def a_respuesta(self):
        """Convierte la excepcion en la tupla (json, codigo) que espera Flask."""
        return jsonify({"error": self.error, "detalle": self.detalle}), self.codigo_http


class DatosInvalidos(ErrorAPI):
    """400 - Faltan campos o vienen con un valor que no sirve."""

    codigo_http = 400
    error = "DATOS_INVALIDOS"


class NoAutenticado(ErrorAPI):
    """401 - No llegaron las cabeceras de identidad que pone el Gateway.

    El codigo es FALTAN_HEADERS, acordado por el equipo: como ningun
    servicio valida el token, el unico fallo de autenticacion posible
    aqui es que falten las cabeceras.
    """

    codigo_http = 401
    error = "FALTAN_HEADERS"


class SinPermiso(ErrorAPI):
    """403 - El rol del usuario no puede hacer esta operacion."""

    codigo_http = 403
    error = "SIN_PERMISO"


class NoEncontrado(ErrorAPI):
    """404 - El recurso no existe, o es de otra empresa (que para quien
    pregunta es lo mismo: no debe enterarse de que existe)."""

    codigo_http = 404
    error = "NO_ENCONTRADO"


class Conflicto(ErrorAPI):
    """409 - La operacion choca con el estado actual de los datos,
    por ejemplo un codigo de producto repetido o stock insuficiente."""

    codigo_http = 409
    error = "CONFLICTO"


class ServicioNoDisponible(ErrorAPI):
    """503 - Un servicio del que dependemos no respondio (RF30)."""

    codigo_http = 503
    error = "SERVICIO_NO_DISPONIBLE"


def registrar_manejadores(app):
    """Conecta los manejadores de error a la aplicacion.

    Un manejador es una funcion que Flask llama automaticamente cuando se
    lanza cierta excepcion, en vez de devolver la pagina de error por defecto.
    """

    @app.errorhandler(ErrorAPI)
    def _error_propio(exc):
        # Cualquier excepcion nuestra ya sabe convertirse en respuesta.
        return exc.a_respuesta()

    @app.errorhandler(404)
    def _ruta_inexistente(_):
        # Una URL que no existe tambien debe responder con nuestro formato,
        # no con el HTML que trae Flask de fabrica.
        return jsonify({"error": "NO_ENCONTRADO", "detalle": "La ruta no existe"}), 404

    @app.errorhandler(405)
    def _metodo_no_permitido(_):
        return (
            jsonify({"error": "METODO_NO_PERMITIDO", "detalle": "El metodo HTTP no aplica a esta ruta"}),
            405,
        )

    @app.errorhandler(Exception)
    def _error_inesperado(exc):
        # Red de seguridad: si algo falla y no lo previmos, igual respondemos
        # con el formato del contrato. El detalle completo queda en el log.
        app.logger.exception("Error no controlado: %s", exc)
        return (
            jsonify({"error": "ERROR_INTERNO", "detalle": "Ocurrio un error inesperado en el servicio"}),
            500,
        )
