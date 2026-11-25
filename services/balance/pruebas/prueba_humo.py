"""Prueba de humo del microservicio de Balance Diario.

    cd services/balance
    python pruebas/prueba_humo.py

Usa SQLite en memoria: no hace falta levantar MySQL.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crear_app
from app.config import Config
from app.fechas import ahora


class ConfigPrueba(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    CREAR_TABLAS = True


ADMIN = {"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "administrador"}
VENDEDOR = {"X-Empresa-Id": "1", "X-Usuario-Id": "12", "X-Rol": "vendedor"}
TIENDA_WEB = {"X-Empresa-Id": "1", "X-Usuario-Id": "50", "X-Rol": "tienda_web"}
DESDE_VENTAS = {"X-Empresa-Id": "1", "X-Servicio-Origen": "ventas"}
DESDE_REPORTES = {"X-Empresa-Id": "1", "X-Servicio-Origen": "reportes"}
OTRA = {"X-Empresa-Id": "2", "X-Usuario-Id": "1", "X-Rol": "administrador"}

fallos = []


def comprobar(nombre, condicion, respuesta=None):
    print(("OK    | " if condicion else "FALLA | ") + nombre)
    if not condicion:
        fallos.append(nombre)
        if respuesta is not None:
            print("        respuesta: {} {}".format(respuesta.status_code, respuesta.data[:300]))


def main():
    cliente = crear_app(ConfigPrueba).test_client()
    hoy = ahora().date().isoformat()
    venta = {"ventaId": 3021, "localId": 1, "canal": "tienda_web", "medioPago": "qr",
             "monto": 43000, "fechaHora": ahora().isoformat() + "-05:00"}

    r = cliente.get("/health")
    comprobar("GET /health -> balance-diario ok",
              r.get_json() == {"servicio": "balance-diario", "estado": "ok"}, r)

    r = cliente.get("/api/balance/diario?localId=1&fecha=" + hoy)
    comprobar("Sin headers -> 401 FALTAN_HEADERS", r.status_code == 401
              and r.get_json()["error"] == "FALTAN_HEADERS", r)

    # --- Ingreso de una venta (ruta interna) ---
    r = cliente.post("/api/balance/movimientos/ventas", json=venta, headers=ADMIN)
    comprobar("Un usuario no puede usar la ruta de Ventas (403)", r.status_code == 403, r)

    r = cliente.post("/api/balance/movimientos/ventas", json=venta,
                     headers={"X-Empresa-Id": "1", "X-Servicio-Origen": "inventario"})
    comprobar("Otro servicio distinto de ventas -> 403", r.status_code == 403, r)

    r = cliente.post("/api/balance/movimientos/ventas", json=venta, headers=DESDE_VENTAS)
    ingreso = r.get_json()
    comprobar("Ventas registra el ingreso (201)", r.status_code == 201
              and ingreso["origen"] == "venta" and ingreso["registradoPor"] == "ventas", r)

    r = cliente.post("/api/balance/movimientos/ventas", json=venta, headers=DESDE_VENTAS)
    comprobar("Misma venta otra vez -> 409 VENTA_YA_REGISTRADA (no duplica)",
              r.status_code == 409 and r.get_json()["error"] == "VENTA_YA_REGISTRADA", r)

    r = cliente.post("/api/balance/movimientos/ventas", json=dict(venta, ventaId=1, monto=0),
                     headers=DESDE_VENTAS)
    comprobar("Monto 0 -> 400", r.status_code == 400, r)

    # --- Movimientos manuales ---
    base = {"localId": 1, "tipo": "ingreso", "medioPago": "efectivo", "monto": 100000,
            "concepto": "Base de caja"}
    r = cliente.post("/api/balance/movimientos", json=base, headers=VENDEDOR)
    comprobar("Vendedor registra ingreso manual (201)", r.status_code == 201, r)

    domicilio = {"localId": 1, "tipo": "egreso", "medioPago": "efectivo", "monto": 30000,
                 "concepto": "Pago de domicilio"}
    r = cliente.post("/api/balance/movimientos", json=domicilio, headers=VENDEDOR)
    egreso_id = r.get_json()["movimientoId"]
    comprobar("Vendedor registra egreso (201)", r.status_code == 201, r)

    r = cliente.post("/api/balance/movimientos", json=domicilio, headers=TIENDA_WEB)
    comprobar("tienda_web no tiene acceso (403)", r.status_code == 403, r)

    r = cliente.post("/api/balance/movimientos", json=dict(domicilio, tipo="ajuste"), headers=ADMIN)
    comprobar("tipo ajuste no va por esta ruta (400)", r.status_code == 400, r)

    # --- Ajuste: el egreso era de 25.000, no de 30.000 ---
    ajuste = {"monto": 5000, "motivo": "El domicilio costo 25.000"}
    r = cliente.post("/api/balance/movimientos/{}/ajustes".format(egreso_id), json=ajuste, headers=VENDEDOR)
    comprobar("Un vendedor no puede hacer ajustes (403)", r.status_code == 403, r)

    r = cliente.post("/api/balance/movimientos/{}/ajustes".format(egreso_id), json=ajuste, headers=ADMIN)
    comprobar("Admin registra el ajuste (201)", r.status_code == 201
              and r.get_json()["ajustaA"] == egreso_id, r)

    r = cliente.get("/api/balance/movimientos/{}".format(egreso_id), headers=VENDEDOR)
    comprobar("El original no cambia y lista su ajuste",
              r.get_json()["monto"] == 30000 and len(r.get_json()["ajustes"]) == 1, r)

    r = cliente.put("/api/balance/movimientos/{}".format(egreso_id), json={"monto": 1}, headers=ADMIN)
    comprobar("No existe PUT: los movimientos no se editan (405)", r.status_code == 405, r)

    # --- Balance diario ---
    r = cliente.get("/api/balance/diario?localId=1&fecha=" + hoy, headers=VENDEDOR)
    b = r.get_json()
    # efectivo: 100000 - 30000 + 5000 = 75000 ; qr: 43000
    comprobar("disponible = ingresos - egresos + ajustes (efectivo 75000, qr 43000)",
              b["disponible"] == {"efectivo": 75000, "tarjeta": 0, "qr": 43000, "total": 118000}, r)
    comprobar("ventasPorCanal tienda_web 43000", b["ventasPorCanal"]["tienda_web"] == 43000, r)

    r = cliente.get("/api/balance/diario?localId=1", headers=VENDEDOR)
    comprobar("Falta la fecha -> 400", r.status_code == 400, r)

    r = cliente.get("/api/balance/diario?localId=1&fecha=" + hoy, headers=OTRA)
    comprobar("Otra empresa ve su balance en ceros", r.get_json()["disponible"]["total"] == 0, r)

    r = cliente.get("/api/balance/reporte?fechaDesde={0}&fechaHasta={0}".format(hoy), headers=DESDE_REPORTES)
    comprobar("Reporte (Reportes): 1 balance y totales 118000",
              r.status_code == 200 and len(r.get_json()["balances"]) == 1
              and r.get_json()["totales"]["total"] == 118000, r)

    r = cliente.get("/api/balance/movimientos?tipo=egreso", headers=VENDEDOR)
    comprobar("Listado paginado filtrado por tipo", r.get_json()["paginacion"]["total"] == 1, r)

    # --- Balance consolidado (sin localId): lo usa el dashboard general de Reportes ---
    otro_local = {"localId": 2, "tipo": "ingreso", "medioPago": "tarjeta", "monto": 20000,
                  "concepto": "Venta en sede norte"}
    cliente.post("/api/balance/movimientos", json=otro_local, headers=VENDEDOR)
    r = cliente.get("/api/balance/diario?fecha=" + hoy, headers=DESDE_REPORTES)
    b = r.get_json()
    comprobar("Sin localId: consolida los 2 locales (total 138000, localId null)",
              r.status_code == 200 and b["localId"] is None
              and b["disponible"] == {"efectivo": 75000, "tarjeta": 20000, "qr": 43000, "total": 138000}, r)
    r = cliente.get("/api/balance/diario?localId=1&fecha=" + hoy, headers=VENDEDOR)
    comprobar("Con localId=1 sigue mostrando solo ese local (118000)",
              r.get_json()["disponible"]["total"] == 118000, r)

    print()
    if fallos:
        print("{} comprobaciones fallaron".format(len(fallos)))
        sys.exit(1)
    print("Todas las comprobaciones pasaron")


if __name__ == "__main__":
    main()
