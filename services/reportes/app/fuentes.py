import logging

from flask import current_app

from .resiliencia import ServicioNoDisponible

registro = logging.getLogger("reportes.fuentes")

OK = "ok"
NO_ENCONTRADO = "no_encontrado"
CAIDO = "caido"


class Fuentes:
    def __init__(self, empresa_id):
        self.empresa_id = empresa_id
        self.no_disponibles = []
        self._memo = {}

    def _marcar(self, servicio):
        if servicio not in self.no_disponibles:
            self.no_disponibles.append(servicio)

    def consultar(self, servicio, ruta, params=None):
        clave = (servicio, ruta, tuple(sorted((params or {}).items())))
        if clave in self._memo:
            return self._memo[clave]
        resultado = self._pedir(servicio, ruta, params)
        self._memo[clave] = resultado
        return resultado

    def _pedir(self, servicio, ruta, params):
        cfg = current_app.config
        sesion = current_app.extensions["sesion_http"]
        try:
            respuesta = current_app.extensions["resiliencia"].llamar(
                servicio,
                lambda: sesion.get(
                    cfg["SERVICIOS"][servicio] + ruta,
                    params=params,
                    headers={"X-Servicio-Origen": "reportes", "X-Empresa-Id": str(self.empresa_id)},
                    timeout=(cfg["TIMEOUT_CONEXION"], cfg["TIMEOUT_LECTURA"]),
                ),
                idempotente=True,
            )
        except ServicioNoDisponible as exc:
            registro.warning("%s no responde: %s", servicio, exc)
            self._marcar(servicio)
            return CAIDO, None
        if respuesta.status_code == 404:
            return NO_ENCONTRADO, None
        if respuesta.status_code != 200:
            registro.warning("%s respondió %s en %s", servicio, respuesta.status_code, ruta)
            self._marcar(servicio)
            return CAIDO, None
        try:
            return OK, respuesta.json()
        except ValueError:
            registro.warning("%s respondió algo que no es JSON en %s", servicio, ruta)
            self._marcar(servicio)
            return CAIDO, None

    def datos(self, servicio, ruta, params=None):
        return self.consultar(servicio, ruta, params)[1]
