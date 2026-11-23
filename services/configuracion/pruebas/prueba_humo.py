"""Prueba de humo del microservicio de Configuracion.

Como ejecutarla:

    cd services/configuracion
    python pruebas/prueba_humo.py

Usa SQLite en memoria, no MySQL: no hace falta levantar la base de datos y
cada ejecucion empieza desde cero.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crear_app
from app.config import Config


class ConfigPrueba(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    CREAR_TABLAS = True
    STOCK_MINIMO_POR_DEFECTO = 5


GATEWAY = {"X-Servicio-Origen": "gateway"}
VENDEDOR = {"X-Empresa-Id": "1", "X-Usuario-Id": "9", "X-Rol": "vendedor"}

fallos = []


def comprobar(nombre, condicion, respuesta=None):
    print(("OK    | " if condicion else "FALLA | ") + nombre)
    if not condicion:
        fallos.append(nombre)
        if respuesta is not None:
            print("        respuesta: {} {}".format(respuesta.status_code, respuesta.data[:200]))


def main():
    cliente = crear_app(ConfigPrueba).test_client()

    # --- Salud y headers ---
    r = cliente.get("/health")
    comprobar("GET /health responde 200", r.status_code == 200, r)

    r = cliente.get("/api/configuracion/locales")
    comprobar("Sin X-Empresa-Id responde 401 FALTAN_HEADERS",
              r.status_code == 401 and r.get_json() == {
                  "error": "FALTAN_HEADERS", "detalle": "Falta el header X-Empresa-Id"}, r)

    # --- Empresas ---
    empresa = {"nombre": "Papeleria La Estrella", "nit": "900123456-7"}
    r = cliente.post("/api/configuracion/empresas", json=empresa, headers=VENDEDOR)
    comprobar("Solo el Gateway crea empresas (403)", r.status_code == 403, r)

    r = cliente.post("/api/configuracion/empresas", json=empresa, headers=GATEWAY)
    comprobar("El Gateway crea la empresa (201)", r.status_code == 201, r)
    empresa_id = str(r.get_json()["empresaId"])
    comprobar("fechaCreacion en hora de Colombia (-05:00)",
              r.get_json()["fechaCreacion"].endswith("-05:00"), r)

    r = cliente.post("/api/configuracion/empresas", json=empresa, headers=GATEWAY)
    comprobar("NIT repetido responde 409", r.status_code == 409, r)

    admin = {"X-Empresa-Id": empresa_id, "X-Usuario-Id": "7", "X-Rol": "administrador"}
    vendedor = {"X-Empresa-Id": empresa_id, "X-Usuario-Id": "9", "X-Rol": "vendedor"}
    inventario = {"X-Empresa-Id": empresa_id, "X-Servicio-Origen": "inventario"}
    otra = {"X-Empresa-Id": "999", "X-Usuario-Id": "3", "X-Rol": "administrador"}

    r = cliente.put("/api/configuracion/empresa", json={"stockMinimoPorDefecto": 7}, headers=admin)
    comprobar("El admin cambia el stock minimo por defecto",
              r.status_code == 200 and r.get_json()["stockMinimoPorDefecto"] == 7, r)

    # --- Locales ---
    local = {"nombre": "Sede Centro", "direccion": "Cra 23 # 25-10", "ciudad": "Manizales"}
    r = cliente.post("/api/configuracion/locales", json=local, headers=admin)
    comprobar("Crear local responde 201", r.status_code == 201, r)
    local_id = r.get_json()["localId"]

    r = cliente.post("/api/configuracion/locales", json=local, headers=admin)
    comprobar("Local repetido responde 409", r.status_code == 409, r)

    r = cliente.post("/api/configuracion/locales", json={"nombre": "Otro"}, headers=vendedor)
    comprobar("Un vendedor no puede crear locales (403)", r.status_code == 403, r)

    r = cliente.post("/api/configuracion/locales", json={}, headers=admin)
    comprobar("Local sin nombre responde 400", r.status_code == 400, r)

    r = cliente.get("/api/configuracion/locales/{}".format(local_id), headers=inventario)
    comprobar("Inventario puede consultar el local (interno)", r.status_code == 200, r)

    r = cliente.get("/api/configuracion/locales/{}".format(local_id), headers=otra)
    comprobar("Otra empresa no ve el local (404)", r.status_code == 404, r)

    r = cliente.put("/api/configuracion/locales/{}".format(local_id),
                    json={"nombre": "Sede Norte", "ciudad": "Manizales"}, headers=admin)
    comprobar("Actualizar local", r.status_code == 200 and r.get_json()["nombre"] == "Sede Norte", r)

    r = cliente.delete("/api/configuracion/locales/{}".format(local_id), headers=admin)
    comprobar("Baja logica del local", r.status_code == 200 and r.get_json()["activo"] is False, r)

    r = cliente.get("/api/configuracion/locales", headers=vendedor)
    comprobar("El local dado de baja ya no se lista", r.get_json() == [], r)

    # --- Stock minimo ---
    r = cliente.get("/api/configuracion/stock-minimo/105", headers=inventario)
    comprobar("Sin valor propio usa el de la empresa (7)",
              r.get_json() == {"productoId": 105, "stockMinimo": 7, "origen": "por_defecto"}, r)

    r = cliente.put("/api/configuracion/stock-minimo/105", json={"stockMinimo": 10}, headers=admin)
    comprobar("Definir stock minimo responde 200", r.status_code == 200, r)

    r = cliente.put("/api/configuracion/stock-minimo/105", json={"stockMinimo": 3}, headers=inventario)
    comprobar("Un servicio interno no puede definir stock minimo (403)", r.status_code == 403, r)

    r = cliente.put("/api/configuracion/stock-minimo/105", json={"stockMinimo": -1}, headers=admin)
    comprobar("Stock minimo negativo responde 400", r.status_code == 400, r)

    r = cliente.put("/api/configuracion/stock-minimo/105", json={"stockMinimo": 3}, headers=vendedor)
    comprobar("Un vendedor no puede definir stock minimo (403)", r.status_code == 403, r)

    r = cliente.get("/api/configuracion/stock-minimo/105", headers=inventario)
    comprobar("Inventario lee el valor propio",
              r.get_json() == {"productoId": 105, "stockMinimo": 10, "origen": "producto"}, r)

    r = cliente.get("/api/configuracion/stock-minimo", headers=vendedor)
    comprobar("Listado de stock minimo tiene 1 producto", len(r.get_json()) == 1, r)

    r = cliente.get("/api/configuracion/stock-minimo/105", headers=otra)
    comprobar("Otra empresa no ve el valor de esta empresa", r.get_json()["origen"] == "por_defecto", r)

    # --- Alertas y dashboard ---
    r = cliente.get("/api/configuracion/alertas", headers=inventario)
    comprobar("Alertas por defecto activas", r.get_json()["stockMinimo"] is True, r)

    r = cliente.put("/api/configuracion/alertas", json={"reposicionPendiente": False}, headers=admin)
    comprobar("Desactivar una alerta", r.get_json()["reposicionPendiente"] is False, r)

    r = cliente.put("/api/configuracion/dashboard",
                    json={"metricas": ["balance_diario"], "preferencias": {"periodoPorDefecto": "mes"}},
                    headers=admin)
    comprobar("Configurar dashboard", r.status_code == 200 and r.get_json()["metricas"] == ["balance_diario"], r)

    r = cliente.put("/api/configuracion/dashboard", json={"metricas": ["inventada"]}, headers=admin)
    comprobar("Metrica desconocida responde 400", r.status_code == 400, r)

    print()
    if fallos:
        print("{} comprobaciones fallaron".format(len(fallos)))
        sys.exit(1)
    print("Todas las comprobaciones pasaron")


if __name__ == "__main__":
    main()
