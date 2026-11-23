"""Verificacion del flujo completo de Configuracion, Ventas y Balance Diario.

    python flujo.py

Necesita los servicios arriba con los puertos de prueba:
    docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build

Hace, en orden:
  1. Flujo completo: crear empresa -> crear local -> definir stock minimo ->
     registrar venta -> consultar el balance del dia.
  2. Errores esperados: 401 (faltan headers), 403 (sin permiso) y 409 (conflictos).
  3. Resiliencia: apaga balance-service, registra una venta (queda "pendiente"),
     lo vuelve a encender y reintenta el registro en Balance.

Cada ejecucion crea una empresa nueva (NIT distinto), asi no choca con las
anteriores. Funciona en Windows, Mac y Linux (necesita el comando docker
para el paso 3).
"""
import os
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone

import requests

# Puertos de docker-compose.pruebas.yml (se pueden cambiar con variables de entorno).
C = os.getenv("CONFIGURACION_URL", "http://localhost:8003")
V = os.getenv("VENTAS_URL", "http://localhost:8004")
B = os.getenv("BALANCE_URL", "http://localhost:8005")
HOY = datetime.now(timezone(timedelta(hours=-5))).date().isoformat()


def paso(titulo, metodo, url, headers=None, cuerpo=None, params=None, mostrar=None):
    """Hace una peticion e imprime el codigo y el JSON de respuesta.

    mostrar: lista de campos a imprimir (para no llenar la pantalla); None = todos.
    """
    r = requests.request(metodo, url, headers=headers or {}, json=cuerpo, params=params, timeout=30)
    datos = r.json()
    if mostrar:
        datos = {k: datos[k] for k in mostrar if k in datos}
    print("\n### {}\n{} {} -> {}".format(titulo, metodo, url.replace("http://localhost", ""), r.status_code))
    print(json.dumps(datos, ensure_ascii=False))
    return r


print("=" * 70, "\nFLUJO COMPLETO\n" + "=" * 70)
for nombre, url in (("configuracion", C), ("ventas", V), ("balance", B)):
    paso("Health " + nombre, "GET", url + "/health")

nit = "900{}-1".format(int(time.time()) % 1000000)
r = paso("1. Crear empresa (como el Gateway)", "POST", C + "/api/configuracion/empresas",
         {"X-Servicio-Origen": "gateway"}, {"nombre": "Papeleria La Estrella", "nit": nit})
eid = str(r.json()["empresaId"])
ADMIN = {"X-Empresa-Id": eid, "X-Usuario-Id": "1", "X-Rol": "administrador"}
VEND = {"X-Empresa-Id": eid, "X-Usuario-Id": "12", "X-Rol": "vendedor"}
WEB = {"X-Empresa-Id": eid, "X-Usuario-Id": "50", "X-Rol": "tienda_web"}

r = paso("2. Crear local", "POST", C + "/api/configuracion/locales", ADMIN,
         {"nombre": "Sede Centro", "ciudad": "Manizales"})
lid = r.json()["localId"]

paso("3. Definir stock minimo del producto 105", "PUT", C + "/api/configuracion/stock-minimo/105",
     ADMIN, {"stockMinimo": 10})
paso("3b. Inventario lo consulta (interna)", "GET", C + "/api/configuracion/stock-minimo/105",
     {"X-Empresa-Id": eid, "X-Servicio-Origen": "inventario"})

r = paso("4. Registrar venta (sin bodegaId, Inventario en mock)", "POST", V + "/api/ventas", VEND,
         {"localId": lid, "canal": "tienda_fisica", "medioPago": "efectivo",
          "items": [{"productoId": 105, "cantidad": 2}, {"productoId": 230, "cantidad": 1}]})
paso("4b. Venta por tienda web con QR", "POST", V + "/api/ventas", WEB,
     {"localId": lid, "canal": "tienda_web", "medioPago": "qr", "items": [{"productoId": 105, "cantidad": 1}]},
     mostrar=["ventaId", "total", "estado", "estadoBalance"])
venta_id = r.json()["ventaId"]

paso("5. Balance del dia", "GET", B + "/api/balance/diario", VEND, params={"localId": lid, "fecha": HOY})
paso("5b. Resumen de ventas (desde Reportes)", "GET", V + "/api/ventas/resumen",
     {"X-Empresa-Id": eid, "X-Servicio-Origen": "reportes"})

print("\n" + "=" * 70, "\nERRORES\n" + "=" * 70)
paso("401 sin X-Empresa-Id", "GET", V + "/api/ventas", {"X-Rol": "vendedor"})
paso("403 vendedor define stock minimo", "PUT", C + "/api/configuracion/stock-minimo/105", VEND, {"stockMinimo": 1})
paso("403 tienda_web con canal tienda_fisica", "POST", V + "/api/ventas", WEB,
     {"localId": lid, "canal": "tienda_fisica", "medioPago": "qr", "items": [{"productoId": 1, "cantidad": 1}]})
paso("403 un usuario llama la ruta interna de Balance", "POST", B + "/api/balance/movimientos/ventas", ADMIN,
     {"ventaId": venta_id, "localId": lid, "canal": "tienda_fisica", "medioPago": "efectivo",
      "monto": 1, "fechaHora": HOY + "T10:00:00-05:00"})
paso("409 NIT repetido", "POST", C + "/api/configuracion/empresas", {"X-Servicio-Origen": "gateway"},
     {"nombre": "Otra", "nit": nit})
paso("409 stock insuficiente (mock: mas de 100 unidades)", "POST", V + "/api/ventas", VEND,
     {"localId": lid, "canal": "tienda_fisica", "medioPago": "tarjeta", "items": [{"productoId": 7, "cantidad": 500}]})
paso("    ...la venta queda rechazada en el historial", "GET", V + "/api/ventas", ADMIN,
     params={"estado": "rechazada"}, mostrar=["paginacion"])
paso("409 Balance no duplica el ingreso de la venta {}".format(venta_id), "POST",
     B + "/api/balance/movimientos/ventas", {"X-Empresa-Id": eid, "X-Servicio-Origen": "ventas"},
     {"ventaId": venta_id, "localId": lid, "canal": "tienda_fisica", "medioPago": "efectivo",
      "monto": 25000, "fechaHora": HOY + "T10:00:00-05:00"})

print("\n" + "=" * 70, "\nRESILIENCIA: Balance apagado\n" + "=" * 70)
subprocess.run(["docker", "stop", "balance-service"], capture_output=True)
r = paso("Venta con Balance caido -> confirmada pero pendiente", "POST", V + "/api/ventas", VEND,
         {"localId": lid, "canal": "tienda_fisica", "medioPago": "tarjeta", "items": [{"productoId": 9, "cantidad": 1}]},
         mostrar=["ventaId", "estado", "estadoBalance"])
pendiente = r.json()["ventaId"]
subprocess.run(["docker", "start", "balance-service"], capture_output=True)
for _ in range(30):
    try:
        if requests.get(B + "/health", timeout=2).status_code == 200:
            break
    except requests.RequestException:
        pass
    time.sleep(1)
paso("Reintento manual (administrador) con Balance de vuelta", "POST",
     V + "/api/ventas/{}/reintento-balance".format(pendiente), ADMIN, mostrar=["ventaId", "estadoBalance"])
paso("Balance del dia final", "GET", B + "/api/balance/diario", VEND, params={"localId": lid, "fecha": HOY},
     mostrar=["ingresos", "disponible", "ventasPorCanal"])
