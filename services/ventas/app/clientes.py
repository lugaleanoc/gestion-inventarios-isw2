"""Llamadas a otros microservicios (RF30).

Ventas llama a:
    Inventario  GET  /api/inventario/bodegas?localId=...   (elegir bodega)
    Inventario  POST /api/inventario/stock/descuentos      (descontar stock)
    Balance     POST /api/balance/movimientos/ventas       (registrar el ingreso)

Politica del equipo: cada llamada espera maximo 3 segundos y se intenta
hasta 3 veces. Cada fallo queda en el log.

Solo se reintenta cuando el otro servicio NO RESPONDE (timeout, conexion
rechazada) o responde 5xx. Un 4xx (400, 409...) es una respuesta valida:
reintentarla daria el mismo resultado.

Reintentar es seguro porque las dos operaciones de escritura usan el ventaId
para no repetir nada: Inventario no descuenta dos veces la misma venta y
Balance no registra dos veces el mismo ingreso.
"""

import requests
from flask import current_app, g

from .errores import ServicioNoDisponible


class RespuestaSimulada:
    """Imita una respuesta de requests para el modo mock de Inventario."""

    def __init__(self, status_code, datos):
        self.status_code = status_code
        self._datos = datos

    def json(self):
        return self._datos


def llamar(servicio, metodo, url, empresa_id, json=None, params=None):
    """Hace una peticion HTTP a otro microservicio con timeout y reintentos.

    servicio: nombre para los logs ("inventario", "balance").
    Devuelve la respuesta (cualquier codigo menor a 500).
    Si despues de los intentos no hubo respuesta, lanza ServicioNoDisponible (503).
    """
    config = current_app.config
    headers = {
        # Asi se identifica Ventas en las llamadas internas.
        "X-Servicio-Origen": config["NOMBRE_SERVICIO"],
        "X-Empresa-Id": str(empresa_id),
        "X-Request-Id": getattr(g, "request_id", ""),
    }

    ultimo_error = None
    for intento in range(1, config["MAX_INTENTOS"] + 1):
        try:
            respuesta = requests.request(metodo, url, json=json, params=params,
                                         headers=headers, timeout=config["TIMEOUT_SEGUNDOS"])
            if respuesta.status_code < 500:
                return respuesta
            ultimo_error = "respondio {}".format(respuesta.status_code)
        except requests.RequestException as exc:
            # Timeout o no se pudo conectar.
            ultimo_error = exc.__class__.__name__
        current_app.logger.warning(
            "Ventas -> %s: intento %s/%s fallido (%s %s): %s",
            servicio, intento, config["MAX_INTENTOS"], metodo, url, ultimo_error,
        )

    current_app.logger.error("Ventas -> %s: sin respuesta despues de %s intentos",
                             servicio, config["MAX_INTENTOS"])
    raise ServicioNoDisponible("Ventas -> {}: el servicio no respondio despues de {} intentos ({})"
                               .format(servicio.capitalize(), config["MAX_INTENTOS"], ultimo_error))


# Inventario
def bodegas_del_local(empresa_id, local_id):
    """Lista de bodegas activas de un local (GET /api/inventario/bodegas)."""
    if current_app.config["USAR_MOCK_INVENTARIO"]:
        # Modo simulado: todos los locales tienen la bodega 1.
        return [{"bodegaId": 1, "localId": local_id, "nombre": "Bodega simulada", "activo": True}]

    respuesta = llamar("inventario", "GET", current_app.config["INVENTARIO_URL"] + "/api/inventario/bodegas",
                       empresa_id, params={"localId": local_id, "activo": "true"})
    if respuesta.status_code != 200:
        raise ServicioNoDisponible("Inventario respondio {} al consultar las bodegas"
                                   .format(respuesta.status_code))
    return respuesta.json()


def descontar_stock(empresa_id, venta_id, items):
    """Pide a Inventario descontar el stock de TODOS los items ("todo o nada").

    items: [{"productoId": 105, "bodegaId": 3, "cantidad": 2}, ...]
    Devuelve la respuesta de Inventario. Si es 200, trae el precioUnitario
    de cada producto.
    """
    cuerpo = {"ventaId": venta_id, "items": items}

    if current_app.config["USAR_MOCK_INVENTARIO"]:
        # Modo simulado: precio fijo y "hay stock" hasta MOCK_STOCK_DISPONIBLE unidades.
        disponible = current_app.config["MOCK_STOCK_DISPONIBLE"]
        for item in items:
            if item["cantidad"] > disponible:
                return RespuestaSimulada(409, {
                    "error": "STOCK_INSUFICIENTE",
                    "detalle": "El producto {} tiene {} unidades disponibles en la bodega {} y se pidieron {}"
                               .format(item["productoId"], disponible, item["bodegaId"], item["cantidad"]),
                })
        precio = current_app.config["MOCK_PRECIO"]
        return RespuestaSimulada(200, {
            "ventaId": venta_id,
            "items": [dict(item, precioUnitario=precio) for item in items],
        })

    return llamar("inventario", "POST",
                  current_app.config["INVENTARIO_URL"] + "/api/inventario/stock/descuentos",
                  empresa_id, json=cuerpo)


# Balance Diario
def registrar_ingreso(venta):
    """Envia el ingreso de una venta confirmada a Balance Diario.

    Devuelve True si Balance lo tiene registrado (201 = recien creado,
    409 = ya existia de un intento anterior). Devuelve False si Balance no
    respondio o rechazo los datos: la venta queda "pendiente".
    Nunca lanza error: una caida de Balance no debe tumbar la venta.
    """
    datos = venta.a_dic()
    cuerpo = {
        "ventaId": datos["ventaId"],
        "localId": datos["localId"],
        "canal": datos["canal"],
        "medioPago": datos["medioPago"],
        "monto": datos["total"],
        "fechaHora": datos["fechaHora"],
    }
    try:
        respuesta = llamar("balance", "POST",
                           current_app.config["BALANCE_URL"] + "/api/balance/movimientos/ventas",
                           venta.empresa_id, json=cuerpo)
    except ServicioNoDisponible as exc:
        current_app.logger.error("Venta %s queda con estadoBalance=pendiente: %s",
                                 venta.venta_id, exc.detalle)
        return False

    if respuesta.status_code in (201, 409):
        return True
    current_app.logger.error("Balance rechazo el ingreso de la venta %s: %s %s",
                             venta.venta_id, respuesta.status_code, respuesta.text[:200])
    return False
