"""Pruebas de rendimiento (RNF06, RNF11).

15 pruebas = 5 endpoints x 3 escenarios (normal, pico, estres), sobre los tres
microservicios Configuracion, Ventas y Balance Diario:

    E1  GET  /api/configuracion/stock-minimo/{id}   Configuracion  (lectura, llamada interna)
    E2  PUT  /api/configuracion/stock-minimo/{id}   Configuracion  (escritura)
    E3  POST /api/ventas                            Ventas -> Inventario (mock) -> Balance
    E4  GET  /api/ventas/resumen                    Ventas         (lectura que suma ventas)
    E5  GET  /api/balance/diario                    Balance Diario (lectura que suma movimientos)

Cada endpoint es una clase de usuario simulado. El script ejecutar_pruebas.py
elige la clase y la cantidad de usuarios de cada escenario.

Correr una sola, con interfaz web (http://localhost:8089):

    locust -f locustfile.py E3RegistrarVenta

Antes de correrlas: python datos_prueba.py (crea la empresa, el local y los
stocks minimos, y guarda los ids en datos_prueba.json).

Las direcciones son las de docker-compose.pruebas.yml (8003, 8004, 8005) y se
pueden cambiar con variables de entorno. Como todavia no hay API Gateway,
cada peticion lleva los headers que el pondria (X-Empresa-Id, X-Usuario-Id,
X-Rol) o los de una llamada interna (X-Servicio-Origen, X-Empresa-Id).
"""

import json
import os
import random
from datetime import datetime, timedelta, timezone

from locust import HttpUser, between, task

CONFIGURACION = os.getenv("CONFIGURACION_URL", "http://localhost:8003")
VENTAS = os.getenv("VENTAS_URL", "http://localhost:8004")
BALANCE = os.getenv("BALANCE_URL", "http://localhost:8005")

# Ids que creo datos_prueba.py. Si el archivo no existe se usan 1, 1 y 1-20.
try:
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_prueba.json"),
              encoding="utf-8") as _archivo:
        _datos = json.load(_archivo)
except (OSError, ValueError):
    _datos = {}
EMPRESA_ID = str(_datos.get("empresaId", 1))
LOCAL_ID = _datos.get("localId", 1)
PRODUCTOS = _datos.get("productos", list(range(1, 21)))

# Headers que pondria el Gateway (usuarios) o que envia otro servicio (llamadas internas).
ADMIN = {"X-Empresa-Id": EMPRESA_ID, "X-Usuario-Id": "1", "X-Rol": "administrador"}
VENDEDOR = {"X-Empresa-Id": EMPRESA_ID, "X-Usuario-Id": "2", "X-Rol": "vendedor"}
DESDE_INVENTARIO = {"X-Empresa-Id": EMPRESA_ID, "X-Servicio-Origen": "inventario"}
DESDE_REPORTES = {"X-Empresa-Id": EMPRESA_ID, "X-Servicio-Origen": "reportes"}


def hoy():
    """Fecha de hoy en Colombia, en formato AAAA-MM-DD.

    Colombia esta siempre en UTC-5 (no tiene horario de verano), asi que basta
    con un desfase fijo. No se usa ZoneInfo("America/Bogota") porque en Windows
    necesitaria instalar tzdata.
    """
    return datetime.now(timezone(timedelta(hours=-5))).date().isoformat()


class UsuarioBase(HttpUser):
    """Lo comun a todas las pruebas: el tiempo de espera entre peticiones.

    Cada usuario simulado espera entre 0.5 y 1.5 s antes de la siguiente
    peticion, como una persona o un servicio real. Lo que cambia entre
    escenarios es CUANTOS usuarios hay, no lo rapido que va cada uno.
    """

    abstract = True          # no es una prueba, solo una base para las demas
    wait_time = between(0.5, 1.5)


# Configuracion
class E1ConsultarStockMinimo(UsuarioBase):
    """Inventario o Reposicion preguntando el stock minimo de un producto.
    Es la consulta mas frecuente del sistema (se hace en cada movimiento de stock).
    Productos 1-10 tienen valor propio; 11-20 usan el valor por defecto."""

    host = CONFIGURACION

    @task
    def consultar(self):
        self.client.get("/api/configuracion/stock-minimo/{}".format(random.choice(PRODUCTOS)),
                        headers=DESDE_INVENTARIO, name="E1 GET /stock-minimo/[id]")


class E2DefinirStockMinimo(UsuarioBase):
    """El administrador cambiando el stock minimo (escribe en MySQL)."""

    host = CONFIGURACION

    @task
    def definir(self):
        self.client.put("/api/configuracion/stock-minimo/{}".format(random.choice(PRODUCTOS)),
                        headers=ADMIN, json={"stockMinimo": random.randint(1, 20)},
                        name="E2 PUT /stock-minimo/[id]")


# Ventas
class E3RegistrarVenta(UsuarioBase):
    """Un vendedor registrando una venta. Es la operacion mas completa:
    Ventas guarda la venta, pide a Inventario descontar el stock (mock por ahora)
    y registra el ingreso en Balance Diario. Mide la comunicacion entre servicios."""

    host = VENTAS

    @task
    def vender(self):
        productos = random.sample(PRODUCTOS, random.randint(1, 3))
        venta = {
            "localId": LOCAL_ID,
            "canal": random.choice(["tienda_fisica", "tienda_web"]),
            "medioPago": random.choice(["efectivo", "tarjeta", "qr"]),
            "items": [{"productoId": p, "cantidad": random.randint(1, 3)} for p in productos],
        }
        with self.client.post("/api/ventas", headers=VENDEDOR, json=venta,
                              name="E3 POST /ventas", catch_response=True) as r:
            # Exito = venta confirmada (201) Y con el ingreso registrado en Balance.
            if r.status_code != 201:
                r.failure("Respondio {}: {}".format(r.status_code, r.text[:100]))
            elif r.json().get("estadoBalance") != "registrado":
                r.failure("Venta confirmada pero Balance no registro el ingreso (pendiente)")


class E4ResumenVentas(UsuarioBase):
    """Reportes pidiendo los totales de ventas por canal y medio de pago.
    Suma todas las ventas confirmadas: se vuelve mas pesada a medida que hay mas ventas."""

    host = VENTAS

    @task
    def resumen(self):
        self.client.get("/api/ventas/resumen", headers=DESDE_REPORTES, name="E4 GET /ventas/resumen")


# Balance Diario
class E5BalanceDiario(UsuarioBase):
    """Un vendedor consultando el balance del dia del local (ingresos, egresos y
    disponible por medio de pago). Suma todos los movimientos del dia."""

    host = BALANCE

    @task
    def balance(self):
        self.client.get("/api/balance/diario", params={"localId": LOCAL_ID, "fecha": hoy()},
                        headers=VENDEDOR, name="E5 GET /balance/diario")