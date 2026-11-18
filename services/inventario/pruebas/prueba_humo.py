"""Prueba de humo del microservicio de Inventario.

No reemplaza las pruebas de rendimiento (esas van con Locust, en
perf-tests/amanda). Esta prueba comprueba que la logica funciona: que los
permisos se respetan, que el stock no queda negativo y que una empresa no
ve los datos de otra.

Como ejecutarla:

    cd services/inventario
    python pruebas/prueba_humo.py

Usa SQLite en memoria, no MySQL: no hace falta levantar la base de datos y
cada ejecucion empieza desde cero. Tampoco necesita que los otros
microservicios esten corriendo.
"""

import os
import sys

# Permite importar el paquete `app` estando dentro de la carpeta pruebas/.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crear_app
from app.config import Config


class ConfigPrueba(Config):
    """Misma configuracion del servicio, pero con una base de prueba."""

    # sqlite:///:memory: = base que vive en la memoria y desaparece al terminar.
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}  # las opciones de MySQL no aplican a SQLite
    CREAR_TABLAS = True


# Cabeceras que normalmente pone el API Gateway. Aqui se mandan a mano.
ADMIN = {"X-Empresa-Id": "1", "X-Usuario-Id": "7", "X-Rol": "administrador"}
VENDEDOR = {"X-Empresa-Id": "1", "X-Usuario-Id": "9", "X-Rol": "vendedor"}
OTRA_EMPRESA = {"X-Empresa-Id": "2", "X-Usuario-Id": "3", "X-Rol": "administrador"}
DESDE_VENTAS = {"X-Empresa-Id": "1", "X-Servicio-Origen": "ventas"}
DESDE_REPOSICION = {"X-Empresa-Id": "1", "X-Servicio-Origen": "reposicion"}

fallos = []


def comprobar(nombre, condicion, respuesta=None):
    """Imprime el resultado de una comprobacion y anota los fallos."""
    print(("OK    | " if condicion else "FALLA | ") + nombre)
    if not condicion:
        fallos.append(nombre)
        if respuesta is not None:
            print("        respuesta: {} {}".format(respuesta.status_code, respuesta.data[:200]))


def main():
    app = crear_app(ConfigPrueba)
    # test_client simula peticiones HTTP sin levantar un servidor de verdad.
    cliente = app.test_client()

    # --- Salud y autenticacion ---
    r = cliente.get("/health")
    comprobar("GET /health responde 200", r.status_code == 200, r)

    r = cliente.get("/api/inventario/productos")
    comprobar("Sin cabeceras de identidad responde 401", r.status_code == 401, r)

    # --- Categorias ---
    r = cliente.post("/api/inventario/categorias", json={"nombre": "Cuadernos"}, headers=ADMIN)
    comprobar("Crear categoria responde 201", r.status_code == 201, r)
    categoria_id = r.get_json()["categoriaId"]

    r = cliente.post("/api/inventario/categorias", json={"nombre": "Cuadernos"}, headers=ADMIN)
    comprobar("Categoria repetida responde 409", r.status_code == 409, r)

    r = cliente.post("/api/inventario/categorias", json={"nombre": "Otra"}, headers=VENDEDOR)
    comprobar("Un vendedor no puede crear categorias (403)", r.status_code == 403, r)

    # --- Productos ---
    producto = {
        "codigo": "CUA-100",
        "nombre": "Cuaderno argollado 100 hojas",
        "categoriaId": categoria_id,
        "unidadMedida": "unidad",
        "precio": 12500,
    }
    r = cliente.post("/api/inventario/productos", json=producto, headers=ADMIN)
    comprobar("Crear producto responde 201", r.status_code == 201, r)
    producto_id = r.get_json()["productoId"]

    r = cliente.post("/api/inventario/productos", json=producto, headers=ADMIN)
    comprobar("Codigo de producto repetido responde 409", r.status_code == 409, r)

    r = cliente.get("/api/inventario/productos?q=cuad", headers=ADMIN)
    comprobar("La busqueda por texto encuentra el producto",
              r.get_json()["paginacion"]["total"] == 1, r)

    # Aislamiento entre empresas (RNF19): es la prueba mas importante de todas.
    r = cliente.get("/api/inventario/productos", headers=OTRA_EMPRESA)
    comprobar("Otra empresa no ve estos productos",
              r.get_json()["paginacion"]["total"] == 0, r)

    r = cliente.get("/api/inventario/productos/{}".format(producto_id), headers=OTRA_EMPRESA)
    comprobar("Un producto de otra empresa responde 404", r.status_code == 404, r)

    # --- Bodegas ---
    r = cliente.post("/api/inventario/bodegas", json={"nombre": "Principal", "localId": 1},
                     headers=ADMIN)
    comprobar("Crear bodega responde 201", r.status_code == 201, r)
    bodega_id = r.get_json()["bodegaId"]

    r = cliente.post("/api/inventario/bodegas", json={"nombre": "Secundaria", "localId": 1},
                     headers=ADMIN)
    bodega_destino_id = r.get_json()["bodegaId"]

    # --- Movimientos ---
    r = cliente.post(
        "/api/inventario/movimientos",
        json={"tipo": "entrada", "productoId": producto_id, "bodegaId": bodega_id,
              "cantidad": 10, "motivo": "Compra inicial"},
        headers=ADMIN,
    )
    comprobar("Una entrada de 10 deja el saldo en 10",
              r.status_code == 201 and r.get_json()["saldoResultante"] == 10, r)

    r = cliente.post(
        "/api/inventario/movimientos",
        json={"tipo": "salida", "productoId": producto_id, "bodegaId": bodega_id,
              "cantidad": 99, "motivo": "Prueba"},
        headers=ADMIN,
    )
    comprobar("Sacar mas de lo que hay responde 409 STOCK_INSUFICIENTE",
              r.status_code == 409 and r.get_json()["error"] == "STOCK_INSUFICIENTE", r)

    r = cliente.post(
        "/api/inventario/movimientos",
        json={"tipo": "traslado", "productoId": producto_id, "bodegaId": bodega_id,
              "bodegaDestinoId": bodega_destino_id, "cantidad": 4, "motivo": "Traslado"},
        headers=ADMIN,
    )
    comprobar("Un traslado genera dos movimientos",
              r.status_code == 201 and len(r.get_json()) == 2, r)

    r = cliente.get("/api/inventario/stock/productos/{}".format(producto_id), headers=ADMIN)
    datos = r.get_json()
    comprobar("El traslado no cambia el total, solo el reparto",
              datos["total"] == 10 and len(datos["porBodega"]) == 2, r)

    r = cliente.post(
        "/api/inventario/movimientos",
        json={"tipo": "venta", "productoId": producto_id, "bodegaId": bodega_id,
              "cantidad": 1, "motivo": "x"},
        headers=ADMIN,
    )
    comprobar("El tipo 'venta' no se puede registrar a mano (400)", r.status_code == 400, r)

    # --- Rutas internas ---
    r = cliente.post(
        "/api/inventario/stock/descuentos",
        json={"ventaId": 3021, "items": [{"productoId": producto_id,
                                          "bodegaId": bodega_id, "cantidad": 2}]},
        headers=DESDE_VENTAS,
    )
    comprobar("Ventas puede descontar stock (200)", r.status_code == 200, r)

    r = cliente.post(
        "/api/inventario/stock/descuentos",
        json={"ventaId": 1, "items": [{"productoId": producto_id,
                                       "bodegaId": bodega_id, "cantidad": 1}]},
        headers=ADMIN,
    )
    comprobar("La ruta interna no se puede llamar desde el Gateway (403)",
              r.status_code == 403, r)

    r = cliente.post(
        "/api/inventario/stock/entradas",
        json={"ordenId": 84, "items": [{"productoId": producto_id,
                                        "bodegaId": bodega_id, "cantidad": 5}]},
        headers=DESDE_REPOSICION,
    )
    comprobar("Reposicion puede registrar una entrada (201)", r.status_code == 201, r)

    r = cliente.post(
        "/api/inventario/stock/entradas",
        json={"ordenId": 84, "items": [{"productoId": producto_id,
                                        "bodegaId": bodega_id, "cantidad": 5}]},
        headers=DESDE_REPOSICION,
    )
    comprobar("La misma orden dos veces responde 409 (idempotencia)",
              r.status_code == 409, r)

    # --- Consultas ---
    r = cliente.get("/api/inventario/movimientos?productoId={}".format(producto_id),
                    headers=ADMIN)
    comprobar("El kardex lista los movimientos",
              r.get_json()["paginacion"]["total"] >= 5, r)

    r = cliente.get("/api/inventario/indicadores", headers=ADMIN)
    comprobar("Los indicadores traen el valor del inventario",
              r.status_code == 200 and r.get_json()["valorTotal"] > 0, r)

    r = cliente.get("/api/inventario/indicadores", headers=VENDEDOR)
    comprobar("Un vendedor no ve los indicadores (403)", r.status_code == 403, r)

    r = cliente.delete("/api/inventario/bodegas/{}".format(bodega_id), headers=ADMIN)
    comprobar("Una bodega con existencias no se da de baja (409)", r.status_code == 409, r)

    print()
    if fallos:
        print("FALLARON {} comprobaciones: {}".format(len(fallos), ", ".join(fallos)))
        return 1
    print("Todas las comprobaciones pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
