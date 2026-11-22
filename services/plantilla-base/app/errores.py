from flask import jsonify


class ApiError(Exception):
    def __init__(self, status, error, detalle):
        super().__init__(detalle)
        self.status = status
        self.error = error
        self.detalle = detalle


def respuesta_error(status, error, detalle):
    return jsonify({"error": error, "detalle": detalle}), status
