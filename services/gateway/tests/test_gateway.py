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

CONTRASENA = "Clave1234"
logging.getLogger("werkzeug").setLevel(logging.ERROR)


def crear_upstream_falso():
    falso = Flask(__name__)
    falso.empresas = 0
    falso.llamadas_empresa = []

    @falso.post("/api/configuracion/empresas")
    def crear_empresa():
        datos = request.get_json()
        falso.llamadas_empresa.append(dict(request.headers))
        if datos["nit"] == "DUP":
            return jsonify({"error": "NIT_DUPLICADO", "detalle": "x"}), 409
        if datos["nit"] == "FALLA":
            return jsonify({"error": "ERROR_INTERNO", "detalle": "x"}), 500
        falso.empresas += 1
        return jsonify({"empresaId": 100 + falso.empresas, "nombre": datos["nombre"], "nit": datos["nit"]}), 201

    @falso.route("/api/<path:ruta>", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def eco(ruta):
        return (
            jsonify(
                {
                    "metodo": request.method,
                    "ruta": request.path,
                    "query": request.query_string.decode(),
                    "cuerpo": request.get_json(silent=True),
                    "empresa": request.headers.get("X-Empresa-Id"),
                    "usuario": request.headers.get("X-Usuario-Id"),
                    "rol": request.headers.get("X-Rol"),
                    "origen": request.headers.get("X-Servicio-Origen"),
                    "autorizacion": request.headers.get("Authorization"),
                }
            ),
            202 if request.args.get("quiero202") else 200,
        )

    servidor = make_server("127.0.0.1", 0, falso, threaded=True)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()
    return falso, servidor


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.falso, cls.servidor = crear_upstream_falso()
        cls.url_falso = f"http://127.0.0.1:{cls.servidor.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()

    def setUp(self):
        descriptor, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        cfg_bd = {"driver": "sqlite", "path": self.ruta}
        crear_tablas(cfg_bd)
        servicios = {
            nombre: self.url_falso
            for nombre in ("configuracion", "inventario", "proveedores", "ventas", "reposicion", "balance", "reportes")
        }
        self.app = create_app(
            {
                "DB": cfg_bd,
                "SERVICIOS": servicios,
                "JWT_SECRET": "secreto-de-pruebas",
                "EXPONER_CODIGO_RECUPERACION": True,
                "TIMEOUT_CONEXION": 1,
                "TIMEOUT_LECTURA": 3,
                "REINTENTO_ESPERA": 0,
                "CIRCUITO_SEGUNDOS": 0.3,
            }
        )
        self.cli = self.app.test_client()
        self.falso.llamadas_empresa.clear()
        self.falso.empresas = 0

    def tearDown(self):
        os.remove(self.ruta)

    def registrar(self, nit="900", correo="admin@empresa.co", contrasena=CONTRASENA):
        return self.cli.post(
            "/api/empresas/registro",
            json={
                "nombreEmpresa": "Mi Empresa",
                "nit": nit,
                "administrador": {"nombre": "Ana Admin", "correo": correo, "contrasena": contrasena},
            },
        )

    def login(self, correo="admin@empresa.co", contrasena=CONTRASENA):
        return self.cli.post("/api/auth/login", json={"correo": correo, "contrasena": contrasena})

    def sesion(self, nit="900", correo="admin@empresa.co"):
        self.registrar(nit, correo)
        return self.login(correo).get_json()

    def auth(self, token):
        return {"Authorization": f"Bearer {token}"}

    def admin_headers(self, nit="900", correo="admin@empresa.co"):
        return self.auth(self.sesion(nit, correo)["token"])

    def crear_usuario(self, headers, correo="vende@empresa.co", rol="vendedor"):
        return self.cli.post(
            "/api/usuarios",
            json={"nombre": "Vera Vendedora", "correo": correo, "contrasena": CONTRASENA, "rol": rol},
            headers=headers,
        )


class PruebasRegistroYLogin(Base):
    def test_health(self):
        self.assertEqual(self.cli.get("/health").get_json()["estado"], "ok")

    def test_registro_crea_empresa_y_administrador(self):
        r = self.registrar()
        self.assertEqual(r.status_code, 201)
        datos = r.get_json()
        self.assertEqual(set(datos), {"empresaId", "usuarioId"})
        self.assertEqual(datos["empresaId"], 101)
        self.assertEqual(self.login().get_json()["usuario"]["rol"], "administrador")
        self.assertNotIn("contrasena", str(datos))
        self.assertEqual(self.falso.llamadas_empresa[-1]["X-Servicio-Origen"], "gateway")

    def test_registro_nit_duplicado_da_409(self):
        r = self.registrar(nit="DUP")
        self.assertEqual(r.status_code, 409)
        self.assertEqual(r.get_json()["error"], "REGISTRO_DUPLICADO")
        self.assertEqual(self.login().status_code, 401)

    def test_registro_correo_duplicado_da_409_sin_llamar_a_configuracion(self):
        self.registrar()
        self.falso.llamadas_empresa.clear()
        self.assertEqual(self.registrar(nit="otro").status_code, 409)
        self.assertEqual(self.falso.llamadas_empresa, [])

    def test_registro_valida_datos(self):
        casos = [
            {},
            {"nombreEmpresa": "A", "nit": "1"},
            {"nombreEmpresa": "A", "nit": "1", "administrador": {"nombre": "x", "correo": "malo", "contrasena": CONTRASENA}},
            {"nombreEmpresa": "A", "nit": "1", "administrador": {"nombre": "x", "correo": "a@b.co", "contrasena": "corta1"}},
            {"nombreEmpresa": "A", "nit": "1", "administrador": {"nombre": "x", "correo": "a@b.co", "contrasena": "sinnumeros"}},
        ]
        for cuerpo in casos:
            with self.subTest(cuerpo=cuerpo):
                r = self.cli.post("/api/empresas/registro", json=cuerpo)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(set(r.get_json()), {"error", "detalle"})

    def test_registro_con_configuracion_caida_da_503(self):
        self.app.config["SERVICIOS"]["configuracion"] = "http://127.0.0.1:9"
        r = self.registrar()
        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.get_json()["error"], "SERVICIO_NO_DISPONIBLE")
        self.assertEqual(self.login().status_code, 401)

    def test_registro_con_configuracion_fallando_da_503(self):
        self.assertEqual(self.registrar(nit="FALLA").status_code, 503)

    def test_login_correcto_devuelve_sesion(self):
        self.registrar()
        r = self.login("ADMIN@empresa.co")
        self.assertEqual(r.status_code, 200)
        datos = r.get_json()
        self.assertEqual(set(datos), {"token", "expiraEn", "usuario"})
        self.assertEqual(datos["usuario"]["correo"], "admin@empresa.co")
        self.assertEqual(datos["expiraEn"], 480 * 60)

    def test_login_incorrecto_da_401(self):
        self.registrar()
        for correo, clave in (("admin@empresa.co", "Equivocada1"), ("nadie@empresa.co", CONTRASENA)):
            r = self.login(correo, clave)
            self.assertEqual(r.status_code, 401)
            self.assertEqual(r.get_json()["error"], "CREDENCIALES_INVALIDAS")
        self.assertEqual(self.cli.post("/api/auth/login", json={"correo": "a@b.co"}).status_code, 400)

    def test_token_ausente_invalido_y_expirado(self):
        r = self.cli.get("/api/usuarios")
        self.assertEqual((r.status_code, r.get_json()["error"]), (401, "TOKEN_AUSENTE"))
        r = self.cli.get("/api/usuarios", headers=self.auth("abc.def.ghi"))
        self.assertEqual((r.status_code, r.get_json()["error"]), (401, "TOKEN_INVALIDO"))
        token = self.sesion()["token"]
        alterado = token[:-3] + ("AAA" if not token.endswith("AAA") else "BBB")
        self.assertEqual(self.cli.get("/api/usuarios", headers=self.auth(alterado)).status_code, 401)
        self.app.config["JWT_EXPIRA_MINUTOS"] = -5
        self.registrar(nit="2", correo="otro@empresa.co")
        expirado = self.login("otro@empresa.co").get_json()["token"]
        r = self.cli.get("/api/usuarios", headers=self.auth(expirado))
        self.assertEqual((r.status_code, r.get_json()["error"]), (401, "TOKEN_EXPIRADO"))

    def test_logout_revoca_el_token(self):
        cab = self.admin_headers()
        self.assertEqual(self.cli.get("/api/usuarios", headers=cab).status_code, 200)
        self.assertEqual(self.cli.post("/api/auth/logout", headers=cab).status_code, 204)
        self.assertEqual(self.cli.get("/api/usuarios", headers=cab).status_code, 401)
        self.assertEqual(self.cli.post("/api/auth/logout").status_code, 401)


class PruebasContrasenas(Base):
    def test_recuperacion_y_restablecimiento(self):
        self.registrar()
        r = self.cli.post("/api/auth/recuperacion", json={"correo": "admin@empresa.co"})
        self.assertEqual(r.status_code, 202)
        codigo = r.get_json()["codigoRecuperacion"]
        malo = self.cli.post("/api/auth/restablecimiento", json={"codigoRecuperacion": "NOEXISTE", "nuevaContrasena": "Nueva1234"})
        self.assertEqual((malo.status_code, malo.get_json()["error"]), (400, "CODIGO_INVALIDO"))
        debil = self.cli.post("/api/auth/restablecimiento", json={"codigoRecuperacion": codigo, "nuevaContrasena": "corta"})
        self.assertEqual((debil.status_code, debil.get_json()["error"]), (400, "CONTRASENA_DEBIL"))
        ok = self.cli.post("/api/auth/restablecimiento", json={"codigoRecuperacion": codigo.lower(), "nuevaContrasena": "Nueva1234"})
        self.assertEqual(ok.status_code, 204)
        self.assertEqual(self.login().status_code, 401)
        self.assertEqual(self.login(contrasena="Nueva1234").status_code, 200)
        reuso = self.cli.post("/api/auth/restablecimiento", json={"codigoRecuperacion": codigo, "nuevaContrasena": "Otra12345"})
        self.assertEqual(reuso.status_code, 400)

    def test_recuperacion_no_revela_si_el_correo_existe(self):
        r = self.cli.post("/api/auth/recuperacion", json={"correo": "nadie@empresa.co"})
        self.assertEqual(r.status_code, 202)
        self.assertNotIn("codigoRecuperacion", r.get_json())

    def test_codigo_vencido(self):
        self.registrar()
        self.app.config["CODIGO_RECUPERACION_MINUTOS"] = -1
        codigo = self.cli.post("/api/auth/recuperacion", json={"correo": "admin@empresa.co"}).get_json()["codigoRecuperacion"]
        r = self.cli.post("/api/auth/restablecimiento", json={"codigoRecuperacion": codigo, "nuevaContrasena": "Nueva1234"})
        self.assertEqual(r.status_code, 400)

    def test_cambio_de_contrasena(self):
        cab = self.admin_headers()
        malo = self.cli.put("/api/auth/contrasena", json={"contrasenaActual": "Mala12345", "nuevaContrasena": "Nueva1234"}, headers=cab)
        self.assertEqual((malo.status_code, malo.get_json()["error"]), (401, "CREDENCIALES_INVALIDAS"))
        debil = self.cli.put("/api/auth/contrasena", json={"contrasenaActual": CONTRASENA, "nuevaContrasena": "corta"}, headers=cab)
        self.assertEqual(debil.status_code, 400)
        ok = self.cli.put("/api/auth/contrasena", json={"contrasenaActual": CONTRASENA, "nuevaContrasena": "Nueva1234"}, headers=cab)
        self.assertEqual(ok.status_code, 204)
        self.assertEqual(self.login(contrasena="Nueva1234").status_code, 200)
        self.assertEqual(self.cli.put("/api/auth/contrasena", json={}).status_code, 401)


class PruebasUsuarios(Base):
    def test_crud_de_usuarios(self):
        cab = self.admin_headers()
        r = self.crear_usuario(cab)
        self.assertEqual(r.status_code, 201)
        usuario = r.get_json()
        self.assertEqual((usuario["rol"], usuario["empresaId"], usuario["activo"]), ("vendedor", 101, True))
        uid = usuario["usuarioId"]
        self.assertEqual(self.cli.get(f"/api/usuarios/{uid}", headers=cab).status_code, 200)
        r = self.cli.put(f"/api/usuarios/{uid}", json={"rol": "encargado_bodega"}, headers=cab)
        self.assertEqual(r.get_json()["rol"], "encargado_bodega")
        self.assertEqual(r.get_json()["nombre"], "Vera Vendedora")
        r = self.cli.delete(f"/api/usuarios/{uid}", headers=cab)
        self.assertFalse(r.get_json()["activo"])
        self.assertEqual(self.cli.get("/api/usuarios/999", headers=cab).status_code, 404)

    def test_correo_duplicado_y_validaciones(self):
        cab = self.admin_headers()
        self.crear_usuario(cab)
        self.assertEqual(self.crear_usuario(cab).status_code, 409)
        for cuerpo in (
            {"nombre": "x", "correo": "a@b.co", "contrasena": CONTRASENA, "rol": "tienda_web"},
            {"nombre": "x", "correo": "a@b.co", "contrasena": CONTRASENA, "rol": "otro"},
            {"nombre": "x", "correo": "a@b.co", "contrasena": "corta", "rol": "vendedor"},
            {"nombre": "x", "correo": "malo", "contrasena": CONTRASENA, "rol": "vendedor"},
        ):
            with self.subTest(cuerpo=cuerpo):
                self.assertEqual(self.cli.post("/api/usuarios", json=cuerpo, headers=cab).status_code, 400)

    def test_listado_con_filtros_y_paginacion(self):
        cab = self.admin_headers()
        for i in range(4):
            self.crear_usuario(cab, correo=f"u{i}@empresa.co", rol="vendedor" if i < 3 else "encargado_bodega")
        r = self.cli.get("/api/usuarios?rol=vendedor&pagina=2&porPagina=2", headers=cab).get_json()
        self.assertEqual(r["paginacion"], {"pagina": 2, "porPagina": 2, "total": 3})
        self.assertEqual(len(r["datos"]), 1)
        self.assertEqual(self.cli.get("/api/usuarios?rol=raro", headers=cab).status_code, 400)
        todos = self.cli.get("/api/usuarios?activo=true", headers=cab).get_json()
        self.assertEqual(todos["paginacion"]["total"], 5)
        uid = self.cli.get("/api/usuarios?rol=encargado_bodega", headers=cab).get_json()["datos"][0]["usuarioId"]
        self.cli.delete(f"/api/usuarios/{uid}", headers=cab)
        self.assertEqual(self.cli.get("/api/usuarios", headers=cab).get_json()["paginacion"]["total"], 4)
        self.assertEqual(self.cli.get("/api/usuarios?activo=false", headers=cab).get_json()["paginacion"]["total"], 1)

    def test_solo_administrador_gestiona_usuarios(self):
        cab = self.admin_headers()
        self.crear_usuario(cab)
        token = self.login("vende@empresa.co").get_json()["token"]
        for metodo, ruta in (("get", "/api/usuarios"), ("post", "/api/usuarios"), ("get", "/api/tiendas-web")):
            r = getattr(self.cli, metodo)(ruta, json={}, headers=self.auth(token))
            self.assertEqual(r.status_code, 403)

    def test_aislamiento_entre_empresas(self):
        cab1 = self.admin_headers(nit="1", correo="a1@x.co")
        cab2 = self.admin_headers(nit="2", correo="a2@x.co")
        uid = self.crear_usuario(cab1).get_json()["usuarioId"]
        self.assertEqual(self.cli.get(f"/api/usuarios/{uid}", headers=cab2).status_code, 404)
        self.assertEqual(self.cli.get("/api/usuarios", headers=cab2).get_json()["paginacion"]["total"], 1)

    def test_no_puede_darse_de_baja_a_si_mismo(self):
        ses = self.sesion()
        r = self.cli.delete(f"/api/usuarios/{ses['usuario']['usuarioId']}", headers=self.auth(ses["token"]))
        self.assertEqual((r.status_code, r.get_json()["error"]), (409, "USUARIO_PROPIO"))

    def test_usuario_dado_de_baja_pierde_acceso_y_cambio_de_rol_aplica_de_inmediato(self):
        cab = self.admin_headers()
        uid = self.crear_usuario(cab).get_json()["usuarioId"]
        token = self.login("vende@empresa.co").get_json()["token"]
        self.cli.put(f"/api/usuarios/{uid}", json={"rol": "administrador"}, headers=cab)
        self.assertEqual(self.cli.get("/api/usuarios", headers=self.auth(token)).status_code, 200)
        self.cli.delete(f"/api/usuarios/{uid}", headers=cab)
        self.assertEqual(self.cli.get("/api/usuarios", headers=self.auth(token)).status_code, 401)
        self.assertEqual(self.login("vende@empresa.co").status_code, 401)


class PruebasTiendasWeb(Base):
    def test_ciclo_completo_de_tienda_web(self):
        cab = self.admin_headers()
        r = self.cli.post("/api/tiendas-web", json={"nombre": "Tienda online"}, headers=cab)
        self.assertEqual(r.status_code, 201)
        tienda = r.get_json()
        self.assertEqual(set(tienda), {"tiendaId", "nombre", "clienteId", "activo", "claveSecreta"})
        listado = self.cli.get("/api/tiendas-web", headers=cab).get_json()
        self.assertEqual(len(listado), 1)
        self.assertNotIn("claveSecreta", listado[0])
        t = self.cli.post("/api/auth/token-tienda", json={"clienteId": tienda["clienteId"], "claveSecreta": tienda["claveSecreta"]})
        self.assertEqual(t.status_code, 200)
        eco = self.cli.post("/api/ventas", json={"x": 1}, headers=self.auth(t.get_json()["token"])).get_json()
        self.assertEqual(eco["rol"], "tienda_web")
        self.assertEqual(eco["empresa"], "101")
        self.assertEqual(self.cli.get("/api/usuarios", headers=self.auth(t.get_json()["token"])).status_code, 403)
        mala = self.cli.post("/api/auth/token-tienda", json={"clienteId": tienda["clienteId"], "claveSecreta": "no"})
        self.assertEqual(mala.status_code, 401)
        baja = self.cli.delete(f"/api/tiendas-web/{tienda['tiendaId']}", headers=cab)
        self.assertFalse(baja.get_json()["activo"])
        self.assertEqual(self.cli.get("/api/ventas", headers=self.auth(t.get_json()["token"])).status_code, 401)
        self.assertEqual(
            self.cli.post("/api/auth/token-tienda", json={"clienteId": tienda["clienteId"], "claveSecreta": tienda["claveSecreta"]}).status_code,
            401,
        )
        self.assertEqual(self.cli.delete("/api/tiendas-web/999", headers=cab).status_code, 404)


class PruebasProxy(Base):
    def test_reenvia_con_headers_de_identidad_y_sin_los_falsos(self):
        ses = self.sesion()
        cab = {
            **self.auth(ses["token"]),
            "X-Rol": "vendedor",
            "X-Empresa-Id": "999",
            "X-Servicio-Origen": "ventas",
            "X-Usuario-Id": "999",
        }
        r = self.cli.post("/api/proveedores/?pagina=2&activo=true", json={"nombre": "Prov"}, headers=cab)
        self.assertEqual(r.status_code, 200)
        eco = r.get_json()
        self.assertEqual(eco["metodo"], "POST")
        self.assertEqual(eco["ruta"], "/api/proveedores/")
        self.assertEqual(eco["query"], "pagina=2&activo=true")
        self.assertEqual(eco["cuerpo"], {"nombre": "Prov"})
        self.assertEqual(eco["empresa"], "101")
        self.assertEqual(eco["usuario"], str(ses["usuario"]["usuarioId"]))
        self.assertEqual(eco["rol"], "administrador")
        self.assertIsNone(eco["origen"])
        self.assertIsNone(eco["autorizacion"])

    def test_pasa_codigos_de_estado_del_servicio(self):
        cab = self.admin_headers()
        self.assertEqual(self.cli.get("/api/inventario/productos?quiero202=1", headers=cab).status_code, 202)

    def test_todos_los_servicios_tienen_ruta(self):
        cab = self.admin_headers()
        for servicio in ("configuracion", "inventario", "proveedores", "ventas", "reposicion", "balance", "reportes"):
            with self.subTest(servicio=servicio):
                self.assertEqual(self.cli.get(f"/api/{servicio}/lo-que-sea", headers=cab).status_code, 200)
        self.assertEqual(self.cli.get("/api/ventas", headers=cab).get_json()["ruta"], "/api/ventas")

    def test_rutas_internas_dan_403_con_token_valido(self):
        cab = self.admin_headers()
        internas = (
            ("post", "/api/inventario/stock/descuentos"),
            ("post", "/api/inventario/stock/entradas"),
            ("post", "/api/reposicion/solicitudes/automaticas"),
            ("post", "/api/balance/movimientos/ventas"),
            ("post", "/api/configuracion/empresas"),
            ("post", "/api/inventario/stock/descuentos/"),
            ("post", "/api/inventario/stock//descuentos"),
            ("get", "/api/inventario/stock/descuentos"),
        )
        for metodo, ruta in internas:
            with self.subTest(ruta=ruta):
                r = getattr(self.cli, metodo)(ruta, json={}, headers=cab)
                self.assertEqual((r.status_code, r.get_json()["error"]), (403, "SIN_PERMISO"))
        self.assertEqual(self.cli.get("/api/inventario/stock", headers=cab).status_code, 200)

    def test_ruta_interna_sin_token_da_401(self):
        self.assertEqual(self.cli.post("/api/inventario/stock/descuentos", json={}).status_code, 401)

    def test_recorrido_de_rutas_no_permitido(self):
        cab = self.admin_headers()
        self.assertEqual(self.cli.get("/api/inventario/../configuracion/empresas", headers=cab).status_code, 400)

    def test_servicio_desconocido_da_404(self):
        cab = self.admin_headers()
        self.assertEqual(self.cli.get("/api/nada", headers=cab).status_code, 404)

    def test_servicio_caido_da_503(self):
        cab = self.admin_headers()
        self.app.config["SERVICIOS"]["ventas"] = "http://127.0.0.1:9"
        r = self.cli.get("/api/ventas", headers=cab)
        self.assertEqual((r.status_code, r.get_json()["error"]), (503, "SERVICIO_NO_DISPONIBLE"))
        self.assertEqual(self.cli.get("/api/inventario/productos", headers=cab).status_code, 200)

    def test_reintenta_y_abre_el_circuito(self):
        cab = self.admin_headers()
        self.app.config["SERVICIOS"]["ventas"] = "http://127.0.0.1:9"
        intentos = []
        original = self.app.extensions["sesion_http"].request

        def contando(*args, **kwargs):
            intentos.append(1)
            return original(*args, **kwargs)

        self.app.extensions["sesion_http"].request = contando
        self.assertEqual(self.cli.get("/api/ventas", headers=cab).status_code, 503)
        self.assertEqual(len(intentos), 3)
        self.assertEqual(self.cli.get("/api/ventas", headers=cab).status_code, 503)
        self.assertEqual(len(intentos), 3)
        self.assertEqual(self.cli.get("/api/inventario/productos", headers=cab).status_code, 200)
        self.app.config["SERVICIOS"]["ventas"] = self.url_falso
        time.sleep(0.4)
        self.assertEqual(self.cli.get("/api/ventas", headers=cab).status_code, 200)

    def test_post_caido_se_reintenta_solo_si_no_llego_a_enviarse(self):
        cab = self.admin_headers()
        self.app.config["SERVICIOS"]["ventas"] = "http://127.0.0.1:9"
        self.assertEqual(self.cli.post("/api/ventas/x", json={}, headers=cab).status_code, 503)

    def test_el_token_trae_empresa_usuario_y_rol(self):
        from app.jwt_utils import verificar

        ses = self.sesion()
        claims = verificar(ses["token"], "secreto-de-pruebas")
        self.assertEqual(claims["empresaId"], 101)
        self.assertEqual(claims["usuarioId"], ses["usuario"]["usuarioId"])
        self.assertEqual((claims["rol"], claims["tipo"]), ("administrador", "usuario"))

    def test_el_proxy_exige_token(self):
        self.assertEqual(self.cli.get("/api/proveedores").status_code, 401)

    def test_errores_usan_el_formato_comun(self):
        r = self.cli.get("/ruta/inexistente")
        self.assertEqual((r.status_code, set(r.get_json())), (404, {"error", "detalle"}))


if __name__ == "__main__":
    unittest.main()
