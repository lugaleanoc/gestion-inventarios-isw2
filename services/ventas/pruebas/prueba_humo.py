"""Prueba de humo del microservicio de Ventas.

    cd services/ventas
    python pruebas/prueba_humo.py

Usa SQLite en memoria y el modo simulado de Inventario: no hace falta
levantar MySQL ni los otros servicios. Las llamadas a Balance Diario se
simulan reemplazando requests.request por una funcion de prueba.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests

from app import clientes, crear_app
from app.config import Config


class ConfigPrueba(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    CREAR_TABLAS = True
    USAR_MOCK_INVENTARIO = True
    MOCK_PRECIO = 2500
    MOCK_STOCK_DISPONIBLE = 100
    BALANCE_URL = "http://balance-falso:8000"


VENDEDOR = {"X-Empresa-Id": "1", "X-Usuario-Id": "12", "X-Rol": "vendedor"}
ADMIN = {"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "administrador"}
TIENDA_WEB = {"X-Empresa-Id": "1", "X-Usuario-Id": "50", "X-Rol": "tienda_web"}
BODEGA = {"X-Empresa-Id": "1", "X-Usuario-Id": "3", "X-Rol": "encargado_bodega"}
REPORTES = {"X-Empresa-Id": "1", "X-Servicio-Origen": "reportes"}
OTRA = {"X-Empresa-Id": "2", "X-Usuario-Id": "1", "X-Rol": "administrador"}

VENTA = {"localId": 1, "canal": "tienda_fisica", "medioPago": "efectivo",
         "items": [{"productoId": 105, "cantidad": 2}, {"productoId": 230, "cantidad": 1}]}

fallos = []
balance_recibido = []


class Respuesta:
    def __init__(self, codigo):
        self.status_code = codigo
        self.text = ""


def balance_que_responde(metodo, url, **kwargs):
    """Simula a Balance Diario: 201 la primera vez, 409 si la venta ya llego."""
    venta_id = kwargs["json"]["ventaId"]
    if venta_id in balance_recibido:
        return Respuesta(409)
    balance_recibido.append(venta_id)
    return Respuesta(201)


def balance_caido(metodo, url, **kwargs):
    raise requests.ConnectionError("Balance apagado")


def comprobar(nombre, condicion, respuesta=None):
    print(("OK    | " if condicion else "FALLA | ") + nombre)
    if not condicion:
        fallos.append(nombre)
        if respuesta is not None:
            print("        respuesta: {} {}".format(respuesta.status_code, respuesta.data[:300]))


def main():
    cliente = crear_app(ConfigPrueba).test_client()

    r = cliente.get("/health")
    comprobar("GET /health -> {servicio: ventas, estado: ok}",
              r.get_json() == {"servicio": "ventas", "estado": "ok"}, r)

    r = cliente.post("/api/ventas", json=VENTA)
    comprobar("Sin headers responde 401 FALTAN_HEADERS",
              r.status_code == 401 and r.get_json()["error"] == "FALTAN_HEADERS", r)

    r = cliente.post("/api/ventas", json=VENTA, headers=BODEGA)
    comprobar("encargado_bodega no puede vender (403)", r.status_code == 403, r)

    r = cliente.post("/api/ventas", json=VENTA, headers=TIENDA_WEB)
    comprobar("tienda_web con canal tienda_fisica -> 403 SIN_PERMISO",
              r.status_code == 403 and r.get_json()["error"] == "SIN_PERMISO", r)

    r = cliente.post("/api/ventas", json=dict(VENTA, medioPago="cheque"), headers=VENDEDOR)
    comprobar("Medio de pago invalido -> 400", r.status_code == 400, r)

    malo = dict(VENTA, items=[{"productoId": 105, "cantidad": 1, "precioUnitario": 1}])
    r = cliente.post("/api/ventas", json=malo, headers=VENDEDOR)
    comprobar("El cliente no puede enviar el precio -> 400", r.status_code == 400, r)

    # --- Venta normal, con Balance respondiendo ---
    clientes.requests.request = balance_que_responde
    r = cliente.post("/api/ventas", json=VENTA, headers=VENDEDOR)
    venta = r.get_json()
    comprobar("Venta confirmada (201) con estadoBalance registrado",
              r.status_code == 201 and venta["estado"] == "confirmada"
              and venta["estadoBalance"] == "registrado", r)
    comprobar("Precio de Inventario (mock 2500) y total 3 x 2500 = 7500",
              venta["total"] == 7500 and venta["items"][0]["precioUnitario"] == 2500
              and venta["bodegaId"] == 1, r)
    comprobar("fechaHora en hora de Colombia", venta["fechaHora"].endswith("-05:00"), r)

    # --- Stock insuficiente (el mock rechaza mas de 100 unidades) ---
    r = cliente.post("/api/ventas", json=dict(VENTA, items=[{"productoId": 1, "cantidad": 500}]),
                     headers=VENDEDOR)
    comprobar("Sin stock -> 409 STOCK_INSUFICIENTE",
              r.status_code == 409 and r.get_json()["error"] == "STOCK_INSUFICIENTE", r)
    r = cliente.get("/api/ventas?estado=rechazada", headers=ADMIN)
    comprobar("La venta rechazada queda en el historial",
              r.get_json()["paginacion"]["total"] == 1, r)

    # --- Balance caido: la venta igual queda confirmada, pero pendiente ---
    clientes.requests.request = balance_caido
    r = cliente.post("/api/ventas", json=dict(VENTA, canal="tienda_web", medioPago="qr"), headers=TIENDA_WEB)
    pendiente = r.get_json()
    comprobar("Balance caido -> 201 con estadoBalance pendiente",
              r.status_code == 201 and pendiente["estadoBalance"] == "pendiente", r)

    r = cliente.post("/api/ventas/{}/reintento-balance".format(pendiente["ventaId"]), headers=ADMIN)
    comprobar("Reintento con Balance todavia caido -> 503", r.status_code == 503, r)

    clientes.requests.request = balance_que_responde
    r = cliente.post("/api/ventas/{}/reintento-balance".format(pendiente["ventaId"]), headers=ADMIN)
    comprobar("Reintento con Balance arriba -> 200 registrado",
              r.status_code == 200 and r.get_json()["estadoBalance"] == "registrado", r)

    r = cliente.post("/api/ventas/{}/reintento-balance".format(pendiente["ventaId"]), headers=ADMIN)
    comprobar("Reintentar algo ya registrado -> 409 BALANCE_YA_REGISTRADO",
              r.status_code == 409 and r.get_json()["error"] == "BALANCE_YA_REGISTRADO", r)

    # --- Consultas ---
    r = cliente.get("/api/ventas", headers=VENDEDOR)
    comprobar("Listado paginado con 2 ventas confirmadas",
              r.get_json()["paginacion"]["total"] == 2 and len(r.get_json()["datos"]) == 2, r)

    r = cliente.get("/api/ventas/{}".format(venta["ventaId"]), headers=OTRA)
    comprobar("Otra empresa no ve la venta (404)", r.status_code == 404, r)

    r = cliente.get("/api/ventas/resumen", headers=REPORTES)
    resumen = r.get_json()
    comprobar("Resumen (Reportes): 2 ventas, 7500 fisica + 7500 web",
              r.status_code == 200 and resumen["cantidadVentas"] == 2
              and resumen["porCanal"] == {"tienda_fisica": 7500, "tienda_web": 7500}
              and resumen["porMedioPago"]["qr"] == 7500, r)

    r = cliente.get("/api/ventas/resumen", headers=VENDEDOR)
    comprobar("Un vendedor no ve el resumen (403)", r.status_code == 403, r)

    r = cliente.get("/api/ventas/resumen", headers={"X-Empresa-Id": "1", "X-Servicio-Origen": "inventario"})
    comprobar("Un servicio no autorizado no ve el resumen (403)", r.status_code == 403, r)

    print()
    if fallos:
        print("{} comprobaciones fallaron".format(len(fallos)))
        sys.exit(1)
    print("Todas las comprobaciones pasaron")


if __name__ == "__main__":
    main()
