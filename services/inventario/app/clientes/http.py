"""Llamadas HTTP a otros servicios, con reintentos y circuit breaker (RF30).

El problema que resuelve este archivo: si el servicio de Configuracion se
cae, cada peticion nuestra se quedaria esperando y terminariamos cayendo
nosotros tambien. Para evitarlo hay dos mecanismos:

1. Timeout y reintentos: se espera poco y se reintenta un par de veces, por
   si fue un fallo pasajero.
2. Circuit breaker ("cortacircuitos"): si un servicio falla muchas veces
   seguidas, se deja de llamarlo durante un rato y se devuelve el error de
   una vez, sin esperar. Pasado ese rato se vuelve a probar.

   Estados:   cerrado  -> todo normal, las llamadas pasan
              abierto  -> el servicio esta caido, no se llama y se falla ya
"""

import time

import requests
from flask import current_app, g

from ..config import Config
from ..errores import ServicioNoDisponible

# Memoria de fallos por servicio. Se guarda en memoria del proceso: si el
# contenedor se reinicia, el contador vuelve a cero, lo cual esta bien.
_estado_circuito = {}


def _circuito(nombre):
    """Devuelve (y crea si hace falta) el estado del circuito de un servicio."""
    return _estado_circuito.setdefault(nombre, {"fallos": 0, "abierto_hasta": 0})


def _esta_abierto(nombre):
    """True si todavia estamos en el periodo de 'no llamar a este servicio'."""
    return time.time() < _circuito(nombre)["abierto_hasta"]


def _registrar_fallo(nombre):
    """Suma un fallo y, si ya son demasiados, abre el circuito."""
    circuito = _circuito(nombre)
    circuito["fallos"] += 1
    if circuito["fallos"] >= Config.CB_FALLOS_PARA_ABRIR:
        circuito["abierto_hasta"] = time.time() + Config.CB_SEGUNDOS_ABIERTO
        circuito["fallos"] = 0
        current_app.logger.warning(
            "Circuito abierto para %s durante %ss", nombre, Config.CB_SEGUNDOS_ABIERTO
        )


def _registrar_exito(nombre):
    """Una llamada que funciona borra los fallos acumulados."""
    _circuito(nombre).update(fallos=0, abierto_hasta=0)


def _cabeceras_internas():
    """Cabeceras con las que este servicio se identifica ante los demas."""
    return {
        "X-Servicio-Origen": Config.NOMBRE_SERVICIO,
        # La empresa viaja siempre: el otro servicio necesita saber de quien
        # son los datos que le estamos pidiendo (RNF19).
        "X-Empresa-Id": str(getattr(g, "identidad", None).empresa_id)
        if getattr(g, "identidad", None) and g.identidad.empresa_id
        else "",
        "X-Request-Id": getattr(g, "request_id", ""),
        "Content-Type": "application/json",
    }


def llamar(nombre_servicio, metodo, url, json=None, obligatorio=True):
    """Hace una peticion HTTP a otro microservicio.

    nombre_servicio: para los logs y el circuit breaker ("configuracion").
    obligatorio:     True  -> si falla, lanza 503 y la operacion se cancela.
                     False -> si falla, devuelve None y el que llama decide
                              (asi una alerta no tumba una venta).
    """
    # Si el circuito esta abierto, ni se intenta.
    if _esta_abierto(nombre_servicio):
        if obligatorio:
            raise ServicioNoDisponible(
                "El servicio '{}' no esta respondiendo".format(nombre_servicio)
            )
        return None

    ultimo_error = None
    for intento in range(1, Config.MAX_REINTENTOS + 1):
        try:
            respuesta = requests.request(
                metodo,
                url,
                json=json,
                headers=_cabeceras_internas(),
                timeout=Config.TIMEOUT_SEGUNDOS,
            )
            # 5xx = el otro servicio esta fallando, vale la pena reintentar.
            if respuesta.status_code >= 500:
                ultimo_error = "respondio {}".format(respuesta.status_code)
                continue
            # 4xx no se reintenta: la peticion esta mal y lo seguira estando.
            _registrar_exito(nombre_servicio)
            return respuesta
        except requests.RequestException as exc:
            # No respondio a tiempo o no se pudo conectar.
            ultimo_error = str(exc)
            current_app.logger.warning(
                "Intento %s/%s fallido hacia %s: %s",
                intento, Config.MAX_REINTENTOS, nombre_servicio, exc,
            )

    # Se agotaron los intentos.
    _registrar_fallo(nombre_servicio)
    if obligatorio:
        raise ServicioNoDisponible(
            "El servicio '{}' no respondio despues de {} intentos ({})".format(
                nombre_servicio, Config.MAX_REINTENTOS, ultimo_error
            )
        )
    return None
