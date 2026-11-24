import logging
import os
import tempfile
import threading
import time
import unittest

from flask import Flask, jsonify, request
from werkzeug.serving import make_server

from app import create_app
from app.db import crear_tablas

logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("reportes.fuentes").setLevel(logging.CRITICAL)
logging.getLogger("reportes.cache").setLevel(logging.CRITICAL)

TODAS = [
    "ventas_por_canal",
    "productos_baja_rotacion",
    "productos_agotados",
    "estado_reposiciones",
    "balance_diario",
    "ingresos_egresos",
    "valor_inventario",
]


def totales(e, t, q):
    return {"efectivo": e, "tarjeta": t, "qr": q, "total": e + t + q}


def crear_upstream_falso():
    falso = Flask(__name__)
    falso.llamadas = []
    falso.fallar = set()
    falso.dashboard = {"metricas": TODAS, "preferencias": {}}

    @falso.before_request
    def registrar():
        servicio = request.path.split("/")[2]
        falso.llamadas.append((request.path, request.args.to_dict(), dict(request.headers)))
        if request.headers.get("X-Servicio-Origen") != "reportes" or not request.headers.get("X-Empresa-Id"):
            return jsonify({"error": "NO", "detalle": "x"}), 403
        if servicio in falso.fallar:
            return jsonify({"error": "ERROR_INTERNO", "detalle": "x"}), 500

    @falso.get("/api/configuracion/dashboard")
    def config_dashboard():
        return jsonify(falso.dashboard)

    @falso.get("/api/configuracion/locales/<int:local_id>")
    def local(local_id):
        if local_id not in (1, 2):
            return jsonify({"error": "LOCAL_NO_ENCONTRADO", "detalle": "x"}), 404
        return jsonify({"localId": local_id, "nombre": f"Sede {local_id}", "activo": True})

    @falso.get("/api/ventas/resumen")
    def ventas():
        return jsonify(
            {
                "fechaDesde": request.args.get("fechaDesde"),
                "fechaHasta": request.args.get("fechaHasta"),
                "localId": request.args.get("localId", type=int),
                "totalVentas": 1500000,
                "cantidadVentas": 12,
                "porCanal": {"tienda_fisica": 1000000, "tienda_web": 500000},
                "porMedioPago": {"efectivo": 700000, "tarjeta": 600000, "qr": 200000},
            }
        )

    @falso.get("/api/inventario/indicadores")
    def indicadores():
        return jsonify(
            {
                "valorTotal": 9000000,
                "cantidadProductos": 40,
                "productosAgotados": [{"productoId": 3, "nombre": "Arroz", "stockTotal": 0}],
                "productosBajoMinimo": [{"productoId": 5, "nombre": "Pan", "stockTotal": 2, "stockMinimo": 10}],
                "mayorRotacion": [{"productoId": 1, "nombre": "Leche", "unidadesSalidas": 50}],
                "menorRotacion": [{"productoId": 9, "nombre": "Sal", "unidadesSalidas": 1}],
            }
        )

    @falso.get("/api/reposicion/resumen")
    def resumen_reposicion():
        return jsonify({"pendiente": 2, "aprobada": 1, "en_orden": 1})

    @falso.get("/api/balance/diario")
    def diario():
        return jsonify(
            {
                "localId": request.args.get("localId", type=int),
                "fecha": request.args.get("fecha"),
                "ingresos": totales(100, 50, 25),
                "egresos": totales(20, 0, 0),
                "ajustes": totales(0, 0, 0),
                "disponible": totales(80, 50, 25),
                "ventasPorCanal": {"tienda_fisica": 150, "tienda_web": 25},
            }
        )

    @falso.get("/api/balance/reporte")
    def reporte_balance():
        return jsonify(
            {
                "fechaDesde": request.args.get("fechaDesde"),
                "fechaHasta": request.args.get("fechaHasta"),
                "balances": [
                    {"localId": 1, "fecha": "2026-11-18", "ingresos": totales(100, 50, 25), "egresos": totales(20, 0, 0), "disponible": totales(80, 50, 25)},
                    {"localId": 1, "fecha": "2026-11-19", "ingresos": totales(30, 10, 5), "egresos": totales(10, 0, 0), "disponible": totales(100, 60, 30)},
                ],
                "totales": totales(0, 0, 0),
            }
        )

    servidor = make_server("127.0.0.1", 0, falso, threaded=True)
    threading.Thread(target=servidor.serve_forever, daemon=True).start()
    return falso, servidor


def cabeceras(rol, empresa="1"):
    return {"X-Empresa-Id": empresa, "X-Usuario-Id": "7", "X-Rol": rol}


ADM = cabeceras("administrador")
VEN = cabeceras("vendedor")
BOD = cabeceras("encargado_bodega")
TW = cabeceras("tienda_web")
BASE = "/api/reportes"


class PruebasReportes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.falso, cls.servidor = crear_upstream_falso()
        cls.url = f"http://127.0.0.1:{cls.servidor.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()

    def setUp(self):
        descriptor, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        cfg_bd = {"driver": "sqlite", "path": self.ruta}
        crear_tablas(cfg_bd)
        self.app = create_app(
            {
                "DB": cfg_bd,
                "SERVICIOS": {n: self.url for n in ("configuracion", "inventario", "ventas", "reposicion", "balance")},
                "TIMEOUT_CONEXION": 1,
                "TIMEOUT_LECTURA": 3,
                "REINTENTO_ESPERA": 0,
                "CIRCUITO_SEGUNDOS": 0.3,
            }
        )
        self.cli = self.app.test_client()
        self.falso.llamadas.clear()
        self.falso.fallar.clear()
        self.falso.dashboard = {"metricas": TODAS, "preferencias": {}}

    def tearDown(self):
        os.remove(self.ruta)

    def get(self, ruta, headers=ADM):
        return self.cli.get(BASE + ruta, headers=headers)

    def llamadas_a(self, prefijo):
        return [c for c in self.falso.llamadas if c[0].startswith(prefijo)]

    def test_health_es_publico(self):
        self.assertEqual(self.cli.get("/health").get_json()["servicio"], "reportes")

    def test_sin_headers_da_401(self):
        r = self.cli.get(BASE + "/dashboard")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(set(r.get_json()), {"error", "detalle"})
        self.assertEqual(r.get_json()["error"], "FALTAN_HEADERS")
        sin_rol = self.cli.get(BASE + "/dashboard", headers={"X-Empresa-Id": "1"})
        self.assertEqual((sin_rol.status_code, sin_rol.get_json()["error"]), (401, "FALTAN_HEADERS"))

    def test_rol_sin_permiso_y_llamadas_entre_servicios_dan_403_sin_permiso(self):
        r = self.get("/ventas-por-canal", BOD)
        self.assertEqual((r.status_code, r.get_json()["error"]), (403, "SIN_PERMISO"))
        interno = {"X-Servicio-Origen": "gateway", "X-Empresa-Id": "1"}
        r = self.get("/dashboard", interno)
        self.assertEqual((r.status_code, r.get_json()["error"]), (403, "SIN_PERMISO"))

    def test_matriz_de_roles(self):
        permitidos = {
            "/dashboard": {"administrador", "vendedor", "encargado_bodega", "tienda_web"},
            "/ventas-por-canal": {"administrador", "vendedor"},
            "/inventario": {"administrador", "encargado_bodega"},
            "/productos-agotados": {"administrador", "encargado_bodega"},
            "/reposiciones": {"administrador", "encargado_bodega"},
            "/balance": {"administrador", "vendedor"},
            "/locales/1": {"administrador"},
        }
        roles = {"administrador": ADM, "vendedor": VEN, "encargado_bodega": BOD, "tienda_web": TW}
        for ruta, ok in permitidos.items():
            for rol, cab in roles.items():
                with self.subTest(ruta=ruta, rol=rol):
                    esperado = 200 if rol in ok else 403
                    self.assertEqual(self.get(ruta, cab).status_code, esperado)

    def test_ventas_por_canal(self):
        r = self.get("/ventas-por-canal?localId=2&fechaDesde=2026-11-01&fechaHasta=2026-11-19", VEN)
        datos = r.get_json()
        self.assertEqual(list(datos)[:3], ["generadoEn", "desdeCache", "fuentesNoDisponibles"])
        self.assertFalse(datos["desdeCache"])
        self.assertEqual(datos["fuentesNoDisponibles"], [])
        self.assertEqual(datos["totalVentas"], 1500000)
        self.assertEqual(datos["porCanal"]["tienda_web"], 500000)
        self.assertEqual(datos["porMedioPago"]["tarjeta"], 600000)
        ruta, params, cab = self.llamadas_a("/api/ventas/resumen")[0]
        self.assertEqual(params, {"fechaDesde": "2026-11-01", "fechaHasta": "2026-11-19", "localId": "2"})
        self.assertEqual(cab["X-Servicio-Origen"], "reportes")
        self.assertEqual(cab["X-Empresa-Id"], "1")

    def test_periodo_por_defecto_son_30_dias(self):
        self.get("/ventas-por-canal")
        params = self.llamadas_a("/api/ventas/resumen")[0][1]
        desde, hasta = params["fechaDesde"], params["fechaHasta"]
        from datetime import date

        self.assertEqual((date.fromisoformat(hasta) - date.fromisoformat(desde)).days, 29)

    def test_parametros_invalidos_dan_400(self):
        for ruta in (
            "/ventas-por-canal?fechaDesde=ayer",
            "/ventas-por-canal?fechaDesde=2026-11-10&fechaHasta=2026-11-01",
            "/ventas-por-canal?localId=cero",
            "/inventario?localId=0",
            "/balance?refrescar=quizas",
        ):
            with self.subTest(ruta=ruta):
                r = self.get(ruta)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.get_json()["error"], "DATOS_INVALIDOS")

    def test_inventario(self):
        datos = self.get("/inventario", BOD).get_json()
        self.assertEqual(datos["valorTotal"], 9000000)
        self.assertEqual(datos["cantidadProductos"], 40)
        self.assertEqual(datos["mayorRotacion"], [{"productoId": 1, "nombre": "Leche", "valor": 50}])
        self.assertEqual(datos["menorRotacion"][0]["nombre"], "Sal")

    def test_productos_agotados(self):
        datos = self.get("/productos-agotados", BOD).get_json()
        self.assertEqual(datos["agotados"], [{"productoId": 3, "nombre": "Arroz", "valor": 0}])
        self.assertEqual(datos["bajoMinimo"], [{"productoId": 5, "nombre": "Pan", "valor": 2}])

    def test_reposiciones(self):
        datos = self.get("/reposiciones", BOD).get_json()
        self.assertEqual(
            datos["porEstado"], {"pendiente": 2, "aprobada": 1, "en_orden": 1, "recibida": 0, "rechazada": 0}
        )

    def test_balance_suma_el_disponible_por_medio_de_pago(self):
        datos = self.get("/balance?localId=1", VEN).get_json()
        self.assertEqual(datos["ingresos"], {"efectivo": 130, "tarjeta": 60, "qr": 30, "total": 220})
        self.assertEqual(datos["egresos"]["efectivo"], 30)
        self.assertEqual(datos["disponible"], {"efectivo": 100, "tarjeta": 60, "qr": 30, "total": 190})

    def test_cache_segunda_llamada_no_consulta_a_los_servicios(self):
        primera = self.get("/ventas-por-canal").get_json()
        self.assertFalse(primera["desdeCache"])
        self.falso.llamadas.clear()
        segunda = self.get("/ventas-por-canal").get_json()
        self.assertTrue(segunda["desdeCache"])
        self.assertEqual(segunda["generadoEn"], primera["generadoEn"])
        self.assertEqual(segunda["totalVentas"], primera["totalVentas"])
        self.assertEqual(self.falso.llamadas, [])

    def test_refrescar_ignora_la_cache(self):
        self.get("/ventas-por-canal")
        self.falso.llamadas.clear()
        r = self.get("/ventas-por-canal?refrescar=true").get_json()
        self.assertFalse(r["desdeCache"])
        self.assertEqual(len(self.llamadas_a("/api/ventas/resumen")), 1)

    def test_la_cache_es_por_empresa_y_por_parametros(self):
        self.get("/ventas-por-canal?localId=1")
        self.assertFalse(self.get("/ventas-por-canal?localId=2").get_json()["desdeCache"])
        self.assertFalse(self.get("/ventas-por-canal?localId=1", cabeceras("administrador", "2")).get_json()["desdeCache"])
        self.assertTrue(self.get("/ventas-por-canal?localId=1").get_json()["desdeCache"])

    def test_ttl_cero_desactiva_la_cache(self):
        self.app.config["CACHE_TTL_SEGUNDOS"] = 0
        self.get("/reposiciones")
        self.assertFalse(self.get("/reposiciones").get_json()["desdeCache"])

    def test_reporte_parcial_si_un_servicio_no_responde(self):
        self.falso.fallar.add("balance")
        r = self.get("/balance")
        self.assertEqual(r.status_code, 200)
        datos = r.get_json()
        self.assertEqual(datos["fuentesNoDisponibles"], ["balance"])
        self.assertEqual(datos["disponible"]["total"], 0)

    def test_reporte_parcial_con_servicio_apagado(self):
        self.app.config["SERVICIOS"]["balance"] = "http://127.0.0.1:9"
        datos = self.get("/dashboard").get_json()
        self.assertEqual(datos["fuentesNoDisponibles"], ["balance"])
        self.assertEqual(datos["metricas"]["balance_diario"], {})
        self.assertEqual(datos["metricas"]["ingresos_egresos"]["ingresos"]["total"], 0)
        self.assertEqual(datos["metricas"]["valor_inventario"], 9000000)
        self.assertEqual(datos["metricas"]["estado_reposiciones"]["pendiente"], 2)

    def test_reintenta_3_veces_y_abre_el_circuito(self):
        self.app.config["SERVICIOS"]["reposicion"] = "http://127.0.0.1:9"
        intentos = []
        original = self.app.extensions["sesion_http"].get

        def contando(*args, **kwargs):
            intentos.append(1)
            return original(*args, **kwargs)

        self.app.extensions["sesion_http"].get = contando
        datos = self.get("/reposiciones?refrescar=true").get_json()
        self.assertEqual(datos["fuentesNoDisponibles"], ["reposicion"])
        self.assertEqual(len(intentos), 3)
        self.get("/reposiciones?refrescar=true")
        self.assertEqual(len(intentos), 3)
        self.app.config["SERVICIOS"]["reposicion"] = self.url
        time.sleep(0.4)
        self.assertEqual(self.get("/reposiciones?refrescar=true").get_json()["fuentesNoDisponibles"], [])

    def test_el_reporte_parcial_se_recupera_con_refrescar(self):
        self.falso.fallar.add("ventas")
        self.assertEqual(self.get("/ventas-por-canal").get_json()["fuentesNoDisponibles"], ["ventas"])
        self.falso.fallar.clear()
        self.assertTrue(self.get("/ventas-por-canal").get_json()["desdeCache"])
        r = self.get("/ventas-por-canal?refrescar=true").get_json()
        self.assertEqual(r["fuentesNoDisponibles"], [])
        self.assertEqual(r["totalVentas"], 1500000)

    def test_dashboard_completo(self):
        datos = self.get("/dashboard?localId=1", VEN).get_json()
        self.assertEqual(list(datos["metricas"]), TODAS)
        self.assertEqual(datos["metricas"]["ventas_por_canal"], {"tienda_fisica": 1000000, "tienda_web": 500000})
        self.assertEqual(datos["metricas"]["productos_baja_rotacion"][0]["nombre"], "Sal")
        self.assertEqual(datos["metricas"]["productos_agotados"], 1)
        self.assertEqual(datos["metricas"]["balance_diario"]["disponible"]["total"], 155)
        self.assertEqual(datos["metricas"]["ingresos_egresos"]["ingresos"]["total"], 175)
        self.assertEqual(datos["fuentesNoDisponibles"], [])

    def test_dashboard_solo_consulta_lo_que_la_empresa_eligio(self):
        self.falso.dashboard = {"metricas": ["valor_inventario", "inventada"], "preferencias": {}}
        datos = self.get("/dashboard").get_json()
        self.assertEqual(list(datos["metricas"]), ["valor_inventario"])
        self.assertEqual(self.llamadas_a("/api/ventas"), [])
        self.assertEqual(self.llamadas_a("/api/balance"), [])
        self.assertEqual(len(self.llamadas_a("/api/inventario/indicadores")), 1)

    def test_dashboard_usa_las_preferencias_de_configuracion(self):
        self.falso.dashboard = {
            "metricas": ["ventas_por_canal"],
            "preferencias": {"localPorDefecto": 2, "periodoPorDefecto": "hoy"},
        }
        self.get("/dashboard")
        params = self.llamadas_a("/api/ventas/resumen")[0][1]
        self.assertEqual(params["localId"], "2")
        self.assertEqual(params["fechaDesde"], params["fechaHasta"])
        self.falso.llamadas.clear()
        self.get("/dashboard?localId=1")
        self.assertEqual(self.llamadas_a("/api/ventas/resumen")[0][1]["localId"], "1")

    def test_dashboard_sin_configuracion_muestra_todas_las_metricas(self):
        self.falso.fallar.add("configuracion")
        datos = self.get("/dashboard").get_json()
        self.assertEqual(list(datos["metricas"]), TODAS)
        self.assertEqual(datos["fuentesNoDisponibles"], ["configuracion"])

    def test_inventario_consultado_una_sola_vez_en_el_dashboard(self):
        self.get("/dashboard")
        self.assertEqual(len(self.llamadas_a("/api/inventario/indicadores")), 1)

    def test_reporte_de_local(self):
        datos = self.get("/locales/1?fechaDesde=2026-11-01&fechaHasta=2026-11-19").get_json()
        self.assertEqual(datos["localId"], 1)
        self.assertEqual(datos["ventas"], {"totalVentas": 1500000, "cantidadVentas": 12})
        self.assertEqual(datos["inventario"], {"valorTotal": 9000000, "productosAgotados": 1})
        self.assertEqual(datos["balance"], {"ingresos": 220, "egresos": 30, "disponible": 190})
        self.assertEqual(datos["fuentesNoDisponibles"], [])
        self.assertEqual(self.llamadas_a("/api/balance/reporte")[0][1]["localId"], "1")

    def test_reporte_de_local_inexistente_da_404(self):
        r = self.get("/locales/99")
        self.assertEqual((r.status_code, r.get_json()["error"]), (404, "LOCAL_NO_ENCONTRADO"))
        self.assertEqual(self.get("/locales/99").status_code, 404)

    def test_reporte_de_local_con_configuracion_caida_sale_parcial(self):
        self.falso.fallar.add("configuracion")
        datos = self.get("/locales/1").get_json()
        self.assertEqual(datos["localId"], 1)
        self.assertEqual(datos["fuentesNoDisponibles"], ["configuracion"])
        self.assertEqual(datos["ventas"]["totalVentas"], 1500000)

    def test_si_la_base_de_la_cache_falla_el_reporte_igual_sale(self):
        self.app.config["DB"] = {"driver": "sqlite", "path": "/no/existe/cache.db"}
        r = self.get("/reposiciones")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()["desdeCache"])


if __name__ == "__main__":
    unittest.main()
