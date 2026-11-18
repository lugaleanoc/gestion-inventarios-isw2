"""Prueba de humo del microservicio de Reposicion.

Recorre el ciclo completo: aviso de stock bajo -> solicitud -> aprobacion
-> orden -> recepcion, y comprueba que los estados no se puedan saltar.

    cd services/reposicion
    python pruebas/prueba_humo.py

Usa SQLite en memoria y no necesita que los otros microservicios esten
corriendo: las llamadas a Inventario, Proveedores y Configuracion se
reemplazan por funciones falsas (lo que se llama un "doble de prueba").
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import crear_app
from app.config import Config

# --- Dobles de prueba ---------------------------------------------------
# Se reemplazan las funciones que salen a la red por otras que responden
# al instante. Asi la prueba comprueba NUESTRA logica y no la de los
# demas servicios, y no falla porque un companero no haya terminado.
import app.rutas.solicitudes as rutas_solicitudes
import app.rutas.ordenes as rutas_ordenes

entradas_registradas = []

rutas_solicitudes.stock_minimo_de = lambda producto_id: 10
rutas_solicitudes.proveedor_principal_de = lambda producto_id: 9
rutas_solicitudes.producto_de = lambda producto_id: {
    "productoId": producto_id, "nombre": "Cuaderno", "activo": True
}
rutas_ordenes.registrar_entrada = lambda orden_id, producto_id, bodega_id, cantidad: (
    entradas_registradas.append((orden_id, producto_id, bodega_id, cantidad)) or True
)


class ConfigPrueba(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_ENGINE_OPTIONS = {}
    CREAR_TABLAS = True


ADMIN = {"X-Empresa-Id": "1", "X-Usuario-Id": "7", "X-Rol": "administrador"}
BODEGA = {"X-Empresa-Id": "1", "X-Usuario-Id": "8", "X-Rol": "encargado_bodega"}
VENDEDOR = {"X-Empresa-Id": "1", "X-Usuario-Id": "9", "X-Rol": "vendedor"}
OTRA_EMPRESA = {"X-Empresa-Id": "2", "X-Usuario-Id": "3", "X-Rol": "administrador"}
DESDE_INVENTARIO = {"X-Empresa-Id": "1", "X-Servicio-Origen": "inventario"}

fallos = []


def comprobar(nombre, condicion, respuesta=None):
    print(("OK    | " if condicion else "FALLA | ") + nombre)
    if not condicion:
        fallos.append(nombre)
        if respuesta is not None:
            print("        respuesta: {} {}".format(respuesta.status_code, respuesta.data[:200]))


def main():
    cliente = crear_app(ConfigPrueba).test_client()

    r = cliente.get("/health")
    comprobar("GET /health responde 200", r.status_code == 200, r)

    r = cliente.get("/api/reposicion/solicitudes")
    comprobar("Sin cabeceras de identidad responde 401", r.status_code == 401, r)

    # --- Solicitud automatica (la crea Inventario) ---
    r = cliente.post("/api/reposicion/solicitudes/automaticas",
                     json={"productoId": 105, "stockActual": 3}, headers=DESDE_INVENTARIO)
    comprobar("Inventario crea la solicitud automatica (201)", r.status_code == 201, r)
    solicitud = r.get_json()
    solicitud_id = solicitud["solicitudId"]
    # Minimo 10, factor 3, quedan 3 unidades -> se sugiere 10*3 - 3 = 27.
    comprobar("La cantidad sugerida se calcula sobre el minimo",
              solicitud["cantidadSugerida"] == 27, r)
    comprobar("La solicitud automatica queda a nombre del sistema",
              solicitud["creadaPor"] == "inventario", r)

    r = cliente.post("/api/reposicion/solicitudes/automaticas",
                     json={"productoId": 105, "stockActual": 2}, headers=DESDE_INVENTARIO)
    comprobar("Un segundo aviso no crea otra solicitud (200)",
              r.status_code == 200 and r.get_json()["solicitudId"] == solicitud_id, r)

    r = cliente.post("/api/reposicion/solicitudes/automaticas",
                     json={"productoId": 105, "stockActual": 2}, headers=ADMIN)
    comprobar("La ruta automatica no se puede llamar desde el Gateway (403)",
              r.status_code == 403, r)

    # --- Solicitud manual ---
    r = cliente.post("/api/reposicion/solicitudes",
                     json={"productoId": 105, "cantidadSugerida": 20}, headers=ADMIN)
    comprobar("Producto con solicitud abierta responde 409", r.status_code == 409, r)

    r = cliente.post("/api/reposicion/solicitudes",
                     json={"productoId": 200, "cantidadSugerida": 20,
                           "observacion": "Se agota rapido"}, headers=BODEGA)
    comprobar("El encargado de bodega crea una solicitud manual (201)",
              r.status_code == 201, r)
    manual_id = r.get_json()["solicitudId"]

    r = cliente.post("/api/reposicion/solicitudes",
                     json={"productoId": 300, "cantidadSugerida": 5}, headers=VENDEDOR)
    comprobar("Un vendedor no puede crear solicitudes (403)", r.status_code == 403, r)

    r = cliente.get("/api/reposicion/solicitudes", headers=OTRA_EMPRESA)
    comprobar("Otra empresa no ve estas solicitudes",
              r.get_json()["paginacion"]["total"] == 0, r)

    # --- Aprobacion y rechazo ---
    r = cliente.post("/api/reposicion/ordenes", json={"solicitudId": solicitud_id},
                     headers=ADMIN)
    comprobar("No se emite orden de una solicitud sin aprobar (409)",
              r.status_code == 409, r)

    r = cliente.post("/api/reposicion/solicitudes/{}/aprobacion".format(solicitud_id),
                     json={"cantidadAprobada": 30}, headers=ADMIN)
    comprobar("Aprobar deja la solicitud en 'aprobada' con la cantidad autorizada",
              r.status_code == 200 and r.get_json()["estado"] == "aprobada"
              and r.get_json()["cantidadAprobada"] == 30, r)

    r = cliente.post("/api/reposicion/solicitudes/{}/aprobacion".format(solicitud_id),
                     headers=ADMIN)
    comprobar("Aprobar dos veces responde 409", r.status_code == 409, r)

    r = cliente.post("/api/reposicion/solicitudes/{}/rechazo".format(manual_id),
                     json={"motivo": "Hay existencias en otra bodega"}, headers=ADMIN)
    comprobar("Rechazar deja la solicitud en 'rechazada'",
              r.status_code == 200 and r.get_json()["estado"] == "rechazada", r)

    r = cliente.post("/api/reposicion/solicitudes/{}/rechazo".format(manual_id),
                     json={"motivo": "x"}, headers=BODEGA)
    comprobar("Solo el administrador rechaza (403)", r.status_code == 403, r)

    # --- Orden de compra ---
    r = cliente.post("/api/reposicion/ordenes",
                     json={"solicitudId": solicitud_id, "fechaEstimadaEntrega": "2027-01-15"},
                     headers=ADMIN)
    comprobar("Se emite la orden de la solicitud aprobada (201)", r.status_code == 201, r)
    orden = r.get_json()
    orden_id = orden["ordenId"]
    comprobar("La orden toma la cantidad aprobada, no la sugerida",
              orden["cantidad"] == 30, r)
    comprobar("La orden nace sin datos de recepcion", orden["recepcion"] is None, r)

    r = cliente.get("/api/reposicion/solicitudes/{}".format(solicitud_id), headers=ADMIN)
    comprobar("La solicitud queda en 'en_orden'", r.get_json()["estado"] == "en_orden", r)

    r = cliente.post("/api/reposicion/ordenes", json={"solicitudId": solicitud_id},
                     headers=ADMIN)
    comprobar("No se emite una segunda orden de la misma solicitud (409)",
              r.status_code == 409, r)

    # --- Recepcion ---
    r = cliente.post("/api/reposicion/ordenes/{}/recepcion".format(orden_id),
                     json={"bodegaId": 3, "cantidadRecibida": 99}, headers=BODEGA)
    comprobar("Recibir mas de lo pedido responde 409", r.status_code == 409, r)

    r = cliente.post("/api/reposicion/ordenes/{}/recepcion".format(orden_id),
                     json={"bodegaId": 3, "cantidadRecibida": 30}, headers=BODEGA)
    comprobar("La recepcion deja la orden en 'recibida'",
              r.status_code == 200 and r.get_json()["estado"] == "recibida", r)
    comprobar("La recepcion le avisa a Inventario que entro la mercancia",
              entradas_registradas == [(orden_id, 105, 3, 30)], r)
    comprobar("La respuesta trae los datos de la recepcion",
              r.get_json()["recepcion"]["cantidadRecibida"] == 30, r)

    r = cliente.get("/api/reposicion/solicitudes/{}".format(solicitud_id), headers=ADMIN)
    comprobar("La solicitud queda en 'recibida'", r.get_json()["estado"] == "recibida", r)

    r = cliente.post("/api/reposicion/ordenes/{}/recepcion".format(orden_id),
                     json={"bodegaId": 3, "cantidadRecibida": 30}, headers=BODEGA)
    comprobar("Recibir dos veces la misma orden responde 409", r.status_code == 409, r)

    r = cliente.post("/api/reposicion/ordenes/{}/cancelacion".format(orden_id),
                     json={"motivo": "Tarde"}, headers=ADMIN)
    comprobar("No se cancela una orden ya recibida (409)", r.status_code == 409, r)

    # --- Resumen ---
    r = cliente.get("/api/reposicion/resumen", headers=ADMIN)
    datos = r.get_json()
    comprobar("El resumen cuenta por estado",
              r.status_code == 200 and datos["ordenes"]["recibida"] == 1
              and datos["solicitudes"]["recibida"] == 1, r)

    print()
    if fallos:
        print("FALLARON {} comprobaciones: {}".format(len(fallos), ", ".join(fallos)))
        return 1
    print("Todas las comprobaciones pasaron.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
