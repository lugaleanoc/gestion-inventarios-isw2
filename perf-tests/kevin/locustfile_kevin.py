import os
import time
import uuid

import requests
from locust import HttpUser, between, tag, task

CORREO = os.getenv("JAK_CORREO", "locust@jak.co")
CONTRASENA = os.getenv("JAK_CONTRASENA", "Locust12345")
NIT_EMPRESA = os.getenv("JAK_NIT", "LOCUST-900123")
MODO = os.getenv("JAK_MODO", "gateway")
URL_PROVEEDORES = os.getenv("URL_PROVEEDORES", "http://localhost:8002").rstrip("/")
URL_REPORTES = os.getenv("URL_REPORTES", "http://localhost:8003").rstrip("/")
CABECERAS_DIRECTAS = {
    "X-Empresa-Id": os.getenv("JAK_EMPRESA_ID", "1"),
    "X-Usuario-Id": os.getenv("JAK_USUARIO_ID", "1"),
    "X-Rol": "administrador",
}


class UsuarioJak(HttpUser):
    wait_time = between(0.2, 1.0)

    _token = None
    _tienda = None
    _proveedor_id = None

    @property
    def autorizacion(self):
        if self._token is None:
            self._token = self._iniciar_sesion()
        return {"Authorization": f"Bearer {self._token}"}

    @property
    def tienda(self):
        if self._tienda is None:
            r = requests.post(
                f"{self.host}/api/tiendas-web",
                json={"nombre": f"Tienda {uuid.uuid4().hex[:6]}"},
                headers=self.autorizacion,
                timeout=30,
            )
            self._tienda = r.json()
        return self._tienda

    @property
    def proveedor_id(self):
        if self._proveedor_id is None:
            base, cabeceras = self._destino("proveedores")
            sufijo = uuid.uuid4().hex[:10]
            r = requests.post(
                f"{base}/api/proveedores",
                json={"nombre": f"Proveedor base {sufijo}", "nit": f"BASE-{sufijo}"},
                headers=cabeceras,
                timeout=30,
            )
            self._proveedor_id = r.json()["proveedorId"]
            requests.post(
                f"{base}/api/proveedores/{self._proveedor_id}/productos",
                json={"productoId": 1, "precioCompra": 1000},
                headers=cabeceras,
                timeout=30,
            )
        return self._proveedor_id

    def _destino(self, servicio):
        if MODO == "directo" and servicio == "proveedores":
            return URL_PROVEEDORES, CABECERAS_DIRECTAS
        if MODO == "directo" and servicio == "reportes":
            return URL_REPORTES, CABECERAS_DIRECTAS
        return self.host, self.autorizacion

    def _iniciar_sesion(self):
        for intento in range(5):
            r = requests.post(
                f"{self.host}/api/auth/login",
                json={"correo": CORREO, "contrasena": CONTRASENA},
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()["token"]
            requests.post(
                f"{self.host}/api/empresas/registro",
                json={
                    "nombreEmpresa": "Empresa de pruebas de carga",
                    "nit": NIT_EMPRESA,
                    "administrador": {"nombre": "Usuario Locust", "correo": CORREO, "contrasena": CONTRASENA},
                },
                timeout=30,
            )
            time.sleep(0.5 * (intento + 1))
        raise RuntimeError("No se pudo iniciar sesión ni registrar la empresa de pruebas")

    def _pedir(self, metodo, ruta, nombre, esperados=(200,), publico=False, servicio="gateway", **kwargs):
        if publico:
            base, cabeceras = self.host, {}
        else:
            base, cabeceras = self._destino(servicio)
        with self.client.request(metodo, base + ruta, name=nombre, headers=cabeceras, catch_response=True, **kwargs) as r:
            if r.status_code in esperados:
                r.success()
            else:
                r.failure(f"{r.status_code}: {r.text[:120]}")
            return r

    @tag("t01")
    @task
    def t01_login(self):
        self.autorizacion
        self._pedir(
            "POST", "/api/auth/login", "T01 POST /api/auth/login",
            publico=True, json={"correo": CORREO, "contrasena": CONTRASENA},
        )

    @tag("t02")
    @task
    def t02_registro_de_empresa(self):
        sufijo = uuid.uuid4().hex[:12]
        self._pedir(
            "POST", "/api/empresas/registro", "T02 POST /api/empresas/registro",
            esperados=(201,), publico=True,
            json={
                "nombreEmpresa": f"Empresa {sufijo}",
                "nit": f"CARGA-{sufijo}",
                "administrador": {"nombre": "Admin carga", "correo": f"{sufijo}@carga.co", "contrasena": "Carga12345"},
            },
        )

    @tag("t03")
    @task
    def t03_token_de_tienda_web(self):
        self._pedir(
            "POST", "/api/auth/token-tienda", "T03 POST /api/auth/token-tienda",
            publico=True,
            json={"clienteId": self.tienda["clienteId"], "claveSecreta": self.tienda["claveSecreta"]},
        )

    @tag("t04")
    @task
    def t04_listar_usuarios(self):
        self._pedir("GET", "/api/usuarios?pagina=1&porPagina=20", "T04 GET /api/usuarios")

    @tag("t05")
    @task
    def t05_crear_usuario(self):
        sufijo = uuid.uuid4().hex[:12]
        self._pedir(
            "POST", "/api/usuarios", "T05 POST /api/usuarios", esperados=(201,),
            json={"nombre": f"Vendedor {sufijo}", "correo": f"{sufijo}@carga.co", "contrasena": "Carga12345", "rol": "vendedor"},
        )

    @tag("t06")
    @task
    def t06_listar_tiendas_web(self):
        self._pedir("GET", "/api/tiendas-web", "T06 GET /api/tiendas-web")

    @tag("t07")
    @task
    def t07_listar_proveedores(self):
        self._pedir("GET", "/api/proveedores?activo=true&pagina=1&porPagina=20", "T07 GET /api/proveedores", servicio="proveedores")

    @tag("t08")
    @task
    def t08_crear_proveedor(self):
        sufijo = uuid.uuid4().hex[:12]
        self._pedir(
            "POST", "/api/proveedores", "T08 POST /api/proveedores", esperados=(201,), servicio="proveedores",
            json={
                "nombre": f"Proveedor {sufijo}",
                "nit": f"P-{sufijo}",
                "contacto": {"nombre": "Contacto", "correo": "contacto@proveedor.co"},
                "condiciones": {"plazoEntregaDias": 3, "formaPago": "30 días"},
            },
        )

    @tag("t09")
    @task
    def t09_consultar_proveedor(self):
        self._pedir("GET", f"/api/proveedores/{self.proveedor_id}", "T09 GET /api/proveedores/{id}", servicio="proveedores")

    @tag("t10")
    @task
    def t10_actualizar_proveedor(self):
        self._pedir(
            "PUT", f"/api/proveedores/{self.proveedor_id}", "T10 PUT /api/proveedores/{id}", servicio="proveedores",
            json={"nombre": "Proveedor actualizado", "nit": f"BASE-{self.proveedor_id}-{uuid.uuid4().hex[:6]}"},
        )

    @tag("t11")
    @task
    def t11_asociar_producto(self):
        self._pedir(
            "POST", f"/api/proveedores/{self.proveedor_id}/productos", "T11 POST /api/proveedores/{id}/productos",
            esperados=(201,), servicio="proveedores",
            json={"productoId": int(uuid.uuid4().int % 1_000_000_000) + 2, "precioCompra": 2500},
        )

    @tag("t12")
    @task
    def t12_proveedores_por_producto(self):
        self._pedir("GET", "/api/proveedores/por-producto/1", "T12 GET /api/proveedores/por-producto/{id}", servicio="proveedores")

    @tag("t13")
    @task
    def t13_dashboard_con_cache(self):
        self._pedir("GET", "/api/reportes/dashboard", "T13 GET /api/reportes/dashboard", servicio="reportes")

    @tag("t14")
    @task
    def t14_reporte_sin_cache(self):
        self._pedir(
            "GET", "/api/reportes/ventas-por-canal?refrescar=true", "T14 GET /api/reportes/ventas-por-canal?refrescar=true",
            servicio="reportes",
        )

    @tag("t15")
    @task
    def t15_flujo_mixto(self):
        self._pedir("GET", "/api/proveedores?activo=true", "T15 GET proveedores", servicio="proveedores")
        self._pedir("GET", "/api/reportes/inventario", "T15 GET reportes/inventario", servicio="reportes")
        self._pedir("GET", "/api/reportes/dashboard", "T15 GET reportes/dashboard", servicio="reportes")
