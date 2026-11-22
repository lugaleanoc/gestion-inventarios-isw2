import os
import tempfile
import unittest

from app import create_app
from app.db import crear_tablas

ADM = {"X-Empresa-Id": "1", "X-Usuario-Id": "10", "X-Rol": "administrador"}
BOD = {"X-Empresa-Id": "1", "X-Usuario-Id": "11", "X-Rol": "encargado_bodega"}
VEN = {"X-Empresa-Id": "1", "X-Usuario-Id": "12", "X-Rol": "vendedor"}
ADM_EMPRESA_2 = {"X-Empresa-Id": "2", "X-Usuario-Id": "20", "X-Rol": "administrador"}
INTERNO = {"X-Servicio-Origen": "reposicion", "X-Empresa-Id": "1"}

BASE = "/api/proveedores"


def proveedor(nombre="Distribuidora Andina", nit="900123456-7", **extra):
    cuerpo = {
        "nombre": nombre,
        "nit": nit,
        "contacto": {"nombre": "Laura", "telefono": "3001234567", "correo": "laura@andina.co"},
        "condiciones": {"plazoEntregaDias": 5, "formaPago": "30 días", "pedidoMinimo": 150000},
    }
    cuerpo.update(extra)
    return cuerpo


class PruebasProveedores(unittest.TestCase):
    def setUp(self):
        descriptor, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        cfg = {"driver": "sqlite", "path": self.ruta}
        crear_tablas(cfg)
        self.app = create_app({"DB": cfg})
        self.cli = self.app.test_client()

    def tearDown(self):
        os.remove(self.ruta)

    def crear(self, cuerpo=None, headers=ADM):
        return self.cli.post(BASE + "/", json=cuerpo or proveedor(), headers=headers)

    def test_health_es_publico(self):
        r = self.cli.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json()["estado"], "ok")

    def test_sin_headers_da_401(self):
        r = self.cli.get(BASE + "/")
        self.assertEqual(r.status_code, 401)
        self.assertEqual(set(r.get_json()), {"error", "detalle"})
        self.assertEqual(r.get_json()["error"], "FALTAN_HEADERS")
        sin_rol = self.cli.get(BASE + "/", headers={"X-Empresa-Id": "1"})
        self.assertEqual((sin_rol.status_code, sin_rol.get_json()["error"]), (401, "FALTAN_HEADERS"))

    def test_rol_sin_permiso_da_403(self):
        r = self.crear(headers=VEN)
        self.assertEqual((r.status_code, r.get_json()["error"]), (403, "SIN_PERMISO"))
        creado = self.crear().get_json()
        self.assertEqual(self.cli.delete(f"{BASE}/{creado['proveedorId']}", headers=BOD).status_code, 403)

    def test_vendedor_puede_consultar(self):
        self.crear()
        r = self.cli.get(BASE + "/", headers=VEN)
        self.assertEqual(r.status_code, 200)

    def test_crear_devuelve_201_y_el_proveedor(self):
        r = self.crear()
        self.assertEqual(r.status_code, 201)
        datos = r.get_json()
        self.assertEqual(datos["nombre"], "Distribuidora Andina")
        self.assertEqual(datos["empresaId"], 1)
        self.assertTrue(datos["activo"])
        self.assertEqual(datos["contacto"]["correo"], "laura@andina.co")
        self.assertEqual(datos["condiciones"]["plazoEntregaDias"], 5)
        self.assertEqual(datos["condiciones"]["pedidoMinimo"], 150000)

    def test_crear_con_solo_campos_obligatorios(self):
        r = self.crear({"nombre": "Mínimo", "nit": "1"})
        self.assertEqual(r.status_code, 201)
        self.assertIsNone(r.get_json()["contacto"]["nombre"])

    def test_validaciones_dan_400(self):
        casos = [
            {"nit": "1"},
            {"nombre": "  ", "nit": "1"},
            {"nombre": "A"},
            {"nombre": "A", "nit": 5},
            proveedor(contacto={"correo": "no-es-correo"}),
            proveedor(condiciones={"plazoEntregaDias": -1}),
            proveedor(condiciones={"plazoEntregaDias": "tres"}),
            proveedor(condiciones={"pedidoMinimo": -5}),
            proveedor(contacto="texto"),
        ]
        for cuerpo in casos:
            with self.subTest(cuerpo=cuerpo):
                r = self.crear(cuerpo)
                self.assertEqual(r.status_code, 400)
                self.assertEqual(r.get_json()["error"], "DATOS_INVALIDOS")

    def test_cuerpo_que_no_es_json_da_400(self):
        r = self.cli.post(BASE + "/", data="hola", headers=ADM)
        self.assertEqual(r.status_code, 400)

    def test_nit_duplicado_da_409_solo_dentro_de_la_empresa(self):
        self.crear()
        self.assertEqual(self.crear().status_code, 409)
        self.assertEqual(self.crear(headers=ADM_EMPRESA_2).status_code, 201)

    def test_obtener_y_404(self):
        creado = self.crear().get_json()
        self.assertEqual(self.cli.get(f"{BASE}/{creado['proveedorId']}", headers=ADM).status_code, 200)
        r = self.cli.get(BASE + "/999", headers=ADM)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error"], "PROVEEDOR_NO_ENCONTRADO")

    def test_aislamiento_entre_empresas(self):
        creado = self.crear().get_json()
        self.assertEqual(self.cli.get(f"{BASE}/{creado['proveedorId']}", headers=ADM_EMPRESA_2).status_code, 404)
        self.assertEqual(self.cli.get(BASE + "/", headers=ADM_EMPRESA_2).get_json()["paginacion"]["total"], 0)

    def test_actualizar_reemplaza_los_datos(self):
        pid = self.crear().get_json()["proveedorId"]
        r = self.cli.put(f"{BASE}/{pid}", json={"nombre": "Nuevo nombre", "nit": "900123456-7"}, headers=BOD)
        self.assertEqual(r.status_code, 200)
        datos = r.get_json()
        self.assertEqual(datos["nombre"], "Nuevo nombre")
        self.assertIsNone(datos["contacto"]["nombre"])
        self.assertEqual(self.cli.put(BASE + "/999", json=proveedor(), headers=ADM).status_code, 404)

    def test_actualizar_con_nit_de_otro_da_409(self):
        self.crear(proveedor(nit="111"))
        pid = self.crear(proveedor(nombre="Otro", nit="222")).get_json()["proveedorId"]
        r = self.cli.put(f"{BASE}/{pid}", json=proveedor(nit="111"), headers=ADM)
        self.assertEqual(r.status_code, 409)

    def test_baja_logica_solo_administrador(self):
        pid = self.crear().get_json()["proveedorId"]
        r = self.cli.delete(f"{BASE}/{pid}", headers=ADM)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()["activo"])
        self.assertEqual(self.cli.get(f"{BASE}/{pid}", headers=ADM).status_code, 200)
        self.assertEqual(self.cli.delete(BASE + "/999", headers=ADM).status_code, 404)

    def test_listado_filtros_y_paginacion(self):
        for i in range(5):
            self.crear(proveedor(nombre=f"Proveedor {i}", nit=f"NIT{i}"))
        pid = self.cli.get(BASE + "/?q=Proveedor 3", headers=ADM).get_json()["datos"][0]["proveedorId"]
        self.cli.delete(f"{BASE}/{pid}", headers=ADM)
        r = self.cli.get(BASE + "/?pagina=2&porPagina=2", headers=ADM).get_json()
        self.assertEqual(len(r["datos"]), 2)
        self.assertEqual(r["paginacion"], {"pagina": 2, "porPagina": 2, "total": 5, "totalPaginas": 3})
        activos = self.cli.get(BASE + "/?activo=true", headers=ADM).get_json()["paginacion"]["total"]
        inactivos = self.cli.get(BASE + "/?activo=false", headers=ADM).get_json()["paginacion"]["total"]
        self.assertEqual((activos, inactivos), (4, 1))
        por_nit = self.cli.get(BASE + "/?q=NIT2", headers=ADM).get_json()
        self.assertEqual(por_nit["paginacion"]["total"], 1)

    def test_por_pagina_maximo_100_y_parametros_invalidos(self):
        r = self.cli.get(BASE + "/?porPagina=500", headers=ADM).get_json()
        self.assertEqual(r["paginacion"]["porPagina"], 100)
        self.assertEqual(self.cli.get(BASE + "/?pagina=0", headers=ADM).status_code, 400)
        self.assertEqual(self.cli.get(BASE + "/?activo=quizas", headers=ADM).status_code, 400)

    def test_ruta_sin_barra_final_funciona(self):
        self.assertEqual(self.cli.get(BASE, headers=ADM).status_code, 200)

    def test_asociar_producto(self):
        pid = self.crear().get_json()["proveedorId"]
        r = self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 7, "precioCompra": 4500.5}, headers=BOD)
        self.assertEqual(r.status_code, 201)
        datos = r.get_json()
        self.assertEqual(datos["productoId"], 7)
        self.assertTrue(datos["principal"])
        self.assertEqual(datos["precioCompra"], 4500.5)
        self.assertEqual(
            self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 7}, headers=ADM).status_code, 409
        )
        self.assertEqual(self.cli.post(f"{BASE}/999/productos", json={"productoId": 7}, headers=ADM).status_code, 404)
        self.assertEqual(self.cli.post(f"{BASE}/{pid}/productos", json={}, headers=ADM).status_code, 400)
        self.assertEqual(
            self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 8}, headers=VEN).status_code, 403
        )

    def test_solo_un_proveedor_principal_por_producto(self):
        a = self.crear(proveedor(nit="A")).get_json()["proveedorId"]
        b = self.crear(proveedor(nombre="B", nit="B")).get_json()["proveedorId"]
        self.assertTrue(self.cli.post(f"{BASE}/{a}/productos", json={"productoId": 1}, headers=ADM).get_json()["principal"])
        self.assertFalse(self.cli.post(f"{BASE}/{b}/productos", json={"productoId": 1}, headers=ADM).get_json()["principal"])
        c = self.crear(proveedor(nombre="C", nit="C")).get_json()["proveedorId"]
        self.assertTrue(
            self.cli.post(f"{BASE}/{c}/productos", json={"productoId": 1, "principal": True}, headers=ADM).get_json()["principal"]
        )
        quien = self.cli.get(f"{BASE}/por-producto/1", headers=ADM).get_json()
        self.assertEqual([p["principal"] for p in quien], [True, False, False])
        self.assertEqual(quien[0]["proveedorId"], c)

    def test_listar_y_quitar_asociaciones(self):
        pid = self.crear().get_json()["proveedorId"]
        for producto in (3, 1, 2):
            self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": producto}, headers=ADM)
        lista = self.cli.get(f"{BASE}/{pid}/productos", headers=ADM).get_json()
        self.assertEqual([a["productoId"] for a in lista], [1, 2, 3])
        r = self.cli.delete(f"{BASE}/{pid}/productos/2", headers=BOD)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.get_json()["activo"])
        self.assertEqual(len(self.cli.get(f"{BASE}/{pid}/productos", headers=ADM).get_json()), 2)
        self.assertEqual(self.cli.delete(f"{BASE}/{pid}/productos/99", headers=ADM).status_code, 404)
        self.assertEqual(self.cli.get(f"{BASE}/999/productos", headers=ADM).status_code, 404)

    def test_reasociar_un_producto_dado_de_baja(self):
        pid = self.crear().get_json()["proveedorId"]
        self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 5, "precioCompra": 10}, headers=ADM)
        self.cli.delete(f"{BASE}/{pid}/productos/5", headers=ADM)
        r = self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 5, "precioCompra": 20}, headers=ADM)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.get_json()["activo"])
        self.assertEqual(r.get_json()["precioCompra"], 20)

    def test_proveedor_dado_de_baja_no_acepta_asociaciones_ni_sale_por_producto(self):
        pid = self.crear().get_json()["proveedorId"]
        self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 5}, headers=ADM)
        self.cli.delete(f"{BASE}/{pid}", headers=ADM)
        self.assertEqual(self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 6}, headers=ADM).status_code, 409)
        r = self.cli.get(f"{BASE}/por-producto/5", headers=ADM)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.get_json()["error"], "PRODUCTO_SIN_PROVEEDORES")

    def test_por_producto_incluye_datos_del_proveedor_y_de_la_asociacion(self):
        pid = self.crear().get_json()["proveedorId"]
        self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 9, "precioCompra": 1200}, headers=ADM)
        datos = self.cli.get(f"{BASE}/por-producto/9", headers=ADM).get_json()
        self.assertEqual(len(datos), 1)
        self.assertEqual(datos[0]["nombre"], "Distribuidora Andina")
        self.assertEqual(datos[0]["precioCompra"], 1200)
        self.assertTrue(datos[0]["principal"])
        self.assertEqual(self.cli.get(f"{BASE}/por-producto/9", headers=ADM_EMPRESA_2).status_code, 404)

    def test_llamada_interna_de_otro_servicio(self):
        pid = self.crear().get_json()["proveedorId"]
        self.cli.post(f"{BASE}/{pid}/productos", json={"productoId": 4}, headers=ADM)
        self.assertEqual(self.cli.get(f"{BASE}/por-producto/4", headers=INTERNO).status_code, 200)
        self.assertEqual(self.cli.get(f"{BASE}/{pid}", headers=INTERNO).status_code, 200)
        self.assertEqual(self.cli.get(BASE + "/", headers={**INTERNO, "X-Servicio-Origen": "inventario-service"}).status_code, 200)

    def test_llamada_interna_no_puede_escribir_ni_usar_origen_falso(self):
        self.assertEqual(self.cli.post(BASE + "/", json=proveedor(), headers=INTERNO).status_code, 403)
        falso = {**INTERNO, "X-Servicio-Origen": "desconocido"}
        self.assertEqual(self.cli.get(BASE + "/", headers=falso).status_code, 403)
        sin_empresa = {"X-Servicio-Origen": "reposicion"}
        r = self.cli.get(BASE + "/", headers=sin_empresa)
        self.assertEqual((r.status_code, r.get_json()["error"]), (401, "FALTAN_HEADERS"))
        self.assertEqual(self.cli.get(BASE + "/", headers=falso).get_json()["error"], "SIN_PERMISO")

    def test_solo_reposicion_e_inventario_pueden_consultar(self):
        pid = self.crear().get_json()["proveedorId"]
        for origen in ("reposicion", "inventario", "inventario-service"):
            with self.subTest(origen=origen):
                cab = {**INTERNO, "X-Servicio-Origen": origen}
                self.assertEqual(self.cli.get(f"{BASE}/{pid}", headers=cab).status_code, 200)
        for origen in ("ventas", "reportes", "gateway", "balance", "configuracion"):
            with self.subTest(origen=origen):
                cab = {**INTERNO, "X-Servicio-Origen": origen}
                r = self.cli.get(f"{BASE}/{pid}", headers=cab)
                self.assertEqual((r.status_code, r.get_json()["error"]), (403, "SIN_PERMISO"))

    def test_errores_de_ruta_y_metodo_usan_el_formato_comun(self):
        r = self.cli.get("/api/nada")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(set(r.get_json()), {"error", "detalle"})
        r = self.cli.patch(BASE + "/", headers=ADM)
        self.assertEqual(r.status_code, 405)
        self.assertEqual(set(r.get_json()), {"error", "detalle"})


if __name__ == "__main__":
    unittest.main()
