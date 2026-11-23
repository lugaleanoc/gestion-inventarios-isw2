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
    wait_time = between(0.5, 1.5)

    _token = None
    _proveedor_id = None

    @property
    def autorizacion(self):
        if self._token is None:
            self._token = self._iniciar_sesion()
        return {"Authorization": f"Bearer {self._token}"}

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

    @tag("login")
    @task
    def login(self):
        self.autorizacion
        self._pedir(
            "POST", "/api/auth/login", "POST /api/auth/login",
            publico=True, json={"correo": CORREO, "contrasena": CONTRASENA},
        )

    @tag("por_producto")
    @task
    def por_producto(self):
        self.proveedor_id
        self._pedir("GET", "/api/proveedores/por-producto/1", "GET /api/proveedores/por-producto/{id}", servicio="proveedores")

    @tag("crear_proveedor")
    @task
    def crear_proveedor(self):
        sufijo = uuid.uuid4().hex[:12]
        self._pedir(
            "POST", "/api/proveedores", "POST /api/proveedores", esperados=(201,), servicio="proveedores",
            json={
                "nombre": f"Proveedor {sufijo}",
                "nit": f"P-{sufijo}",
                "contacto": {"nombre": "Contacto", "correo": "contacto@proveedor.co"},
                "condiciones": {"plazoEntregaDias": 3, "formaPago": "30 días"},
            },
        )

    @tag("dashboard")
    @task
    def dashboard(self):
        self._pedir("GET", "/api/reportes/dashboard", "GET /api/reportes/dashboard", servicio="reportes")

    @tag("sin_cache")
    @task
    def sin_cache(self):
        self._pedir(
            "GET", "/api/reportes/ventas-por-canal?refrescar=true", "GET /api/reportes/ventas-por-canal?refrescar=true",
            servicio="reportes",
        )
