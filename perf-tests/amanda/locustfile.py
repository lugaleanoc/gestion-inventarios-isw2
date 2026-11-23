"""Pruebas de rendimiento de Inventario y Reposicion (RNF11).

Herramienta: Locust. Cada clase de abajo es UNA prueba: define a que
endpoint le pega y con que datos. El escenario (cuantos usuarios y por
cuanto tiempo) no va aqui, se pasa por linea de comandos; asi el mismo
archivo sirve para carga normal, pico y estres.

Para correr una sola a mano:

    locust -f locustfile.py E1_StockDeProducto --headless -u 10 -r 2 -t 2m

Para correr las 15:  python ejecutar.py

Como funciona Locust: levanta N "usuarios" simulados, cada uno en paralelo.
Cada usuario repite su tarea, espera un momento (wait_time) y vuelve a
empezar. Locust mide cuanto tardo cada peticion y cuantas fallaron.
"""

import json
import os
import random

from locust import HttpUser, between, task

# --- Datos sembrados -----------------------------------------------------
# Los ids reales de los productos los crea datos_de_prueba.py. Si el
# archivo no existe, se usan ids inventados y casi todo responderia 404,
# que medirian la velocidad del error y no la del caso real.
RUTA_DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos_sembrados.json")

try:
    with open(RUTA_DATOS, encoding="utf-8") as archivo:
        DATOS = json.load(archivo)
    PRODUCTOS = DATOS["productos"]
    BODEGAS = DATOS["bodegas"]
except (OSError, KeyError, ValueError):
    print("AVISO: no se encontro datos_sembrados.json. "
          "Corre primero:  python datos_de_prueba.py")
    PRODUCTOS = [1]
    BODEGAS = [1]

# Palabras que existen en los nombres sembrados, para que la busqueda
# devuelva resultados de verdad y no una lista vacia.
BUSQUEDAS = ["cuaderno", "argollado", "rayado", "escolar", "oficina", "eco"]

# --- Cabeceras -----------------------------------------------------------
# El API Gateway es de Kevin y no entra en estas pruebas: medimos nuestros
# servicios directamente, mandando a mano las cabeceras que el pondria.
# Esto ademas aisla la medicion: si el Gateway estuviera en el medio,
# estariamos midiendo dos servicios y no sabriamos cual es el lento.
USUARIO = {"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "administrador"}
BODEGA = {"X-Empresa-Id": "1", "X-Usuario-Id": "2", "X-Rol": "encargado_bodega"}
# Las rutas internas se identifican con el nombre del servicio que llama.
COMO_VENTAS = {"X-Empresa-Id": "1", "X-Servicio-Origen": "ventas"}
COMO_INVENTARIO = {"X-Empresa-Id": "1", "X-Servicio-Origen": "inventario"}

INVENTARIO = os.getenv("URL_INVENTARIO", "http://localhost:8001")
REPOSICION = os.getenv("URL_REPOSICION", "http://localhost:8002")


class _Base(HttpUser):
    """Cosas comunes a todas las pruebas. No se ejecuta por si sola."""

    abstract = True
    # Pausa entre una peticion y la siguiente del mismo usuario. Simula a
    # una persona que lee la pantalla antes de volver a hacer clic. Sin
    # pausa, 10 usuarios pegarian como 200 y el numero no significaria nada.
    wait_time = between(0.5, 1.5)


# =========================================================================
# E1 - Consulta puntual de stock          (Inventario, lectura)
# =========================================================================
class E1_StockDeProducto(_Base):
    """El endpoint mas usado del sistema: cada venta lo consulta.

    Es una lectura sencilla: busca las filas de stock de un producto y
    suma. Deberia ser la prueba mas rapida de todas.
    """

    host = INVENTARIO

    @task
    def consultar_stock(self):
        producto_id = random.choice(PRODUCTOS)
        # name agrupa todas las peticiones bajo un mismo nombre en el
        # reporte. Sin esto, Locust mostraria una fila por cada id y el
        # resumen seria ilegible.
        self.client.get(
            "/api/inventario/stock/productos/{}".format(producto_id),
            headers=USUARIO,
            name="E1 GET /stock/productos/{id}",
        )


# =========================================================================
# E2 - Busqueda de productos              (Inventario, lectura con filtro)
# =========================================================================
class E2_BusquedaDeProductos(_Base):
    """Busqueda por texto (RF12).

    Mas pesada que E1: usa LIKE '%texto%' sobre nombre y codigo, y ese
    tipo de busqueda no puede aprovechar bien los indices. Es la
    candidata natural a salir lenta, y por eso esta en la lista.
    """

    host = INVENTARIO

    @task
    def buscar(self):
        self.client.get(
            "/api/inventario/productos",
            params={"q": random.choice(BUSQUEDAS), "porPagina": 20},
            headers=USUARIO,
            name="E2 GET /productos?q=",
        )


# =========================================================================
# E3 - Descuento de stock                 (Inventario, ESCRITURA)
# =========================================================================
class E3_DescuentoDeStock(_Base):
    """La ruta interna que llama Ventas cada vez que se vende algo.

    Es la prueba mas interesante de las cinco porque escribe: bloquea la
    fila de stock con SELECT ... FOR UPDATE, la actualiza y ademas inserta
    una fila en el kardex. Bajo carga alta, varios usuarios van a pelear
    por la misma fila y ahi es donde se ve el costo del bloqueo.
    """

    host = INVENTARIO
    contador = 0

    @task
    def descontar(self):
        # Cada venta necesita un ventaId distinto: si se repitiera, el
        # servicio lo tomaria como un reintento.
        E3_DescuentoDeStock.contador += 1
        venta_id = random.randint(1, 10 ** 9)
        self.client.post(
            "/api/inventario/stock/descuentos",
            json={
                "ventaId": venta_id,
                "items": [{
                    "productoId": random.choice(PRODUCTOS),
                    "bodegaId": BODEGAS[0],
                    "cantidad": 1,
                }],
            },
            headers=COMO_VENTAS,
            name="E3 POST /stock/descuentos",
        )


# =========================================================================
# E4 - Resumen de reposicion              (Reposicion, lectura agregada)
# =========================================================================
class E4_ResumenDeReposicion(_Base):
    """Cuenta solicitudes y ordenes por estado, con dos GROUP BY.

    Lo consulta el dashboard de Reportes. Sirve para comparar cuanto
    cuesta una consulta que agrupa frente a una que solo filtra (E1).
    """

    host = REPOSICION

    @task
    def resumen(self):
        self.client.get(
            "/api/reposicion/resumen",
            headers=USUARIO,
            name="E4 GET /reposicion/resumen",
        )


# =========================================================================
# E5 - Solicitud automatica               (Reposicion, ESCRITURA)
# =========================================================================
class E5_SolicitudAutomatica(_Base):
    """La ruta interna que llama Inventario cuando un producto baja del minimo.

    Antes de crear nada, revisa si ya hay una solicitud abierta para ese
    producto, asi que mide una escritura CON comprobacion previa. Tambien
    deja ver el circuit breaker: este endpoint intenta llamar a
    Configuracion y a Proveedores, que no estan levantados, y despues de
    unos pocos fallos deja de intentarlo y responde rapido.
    """

    host = REPOSICION

    @task
    def crear_solicitud(self):
        self.client.post(
            "/api/reposicion/solicitudes/automaticas",
            json={
                # Id al azar en un rango amplio para que casi siempre sea
                # un producto nuevo y la prueba mida la creacion.
                "productoId": random.randint(1, 10 ** 6),
                "stockActual": random.randint(0, 4),
            },
            headers=COMO_INVENTARIO,
            name="E5 POST /solicitudes/automaticas",
        )
