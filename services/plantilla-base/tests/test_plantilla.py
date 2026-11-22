import os
import tempfile
import unittest

from app import create_app
from app.db import crear_tablas

ADM = {"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "administrador"}
VEN = {"X-Empresa-Id": "1", "X-Usuario-Id": "2", "X-Rol": "vendedor"}
INTERNO = {"X-Servicio-Origen": "reportes", "X-Empresa-Id": "1"}
INTERNO_NO_PERMITIDO = {"X-Servicio-Origen": "ventas", "X-Empresa-Id": "1"}


class PruebasPlantilla(unittest.TestCase):
    def setUp(self):
        descriptor, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        cfg = {"driver": "sqlite", "path": self.ruta}
        crear_tablas(cfg)
        self.cli = create_app({"DB": cfg}).test_client()

    def tearDown(self):
        os.remove(self.ruta)

    def test_health(self):
        self.assertEqual(self.cli.get("/health").status_code, 200)

    def test_sin_headers_401_y_rol_incorrecto_403(self):
        r = self.cli.get("/api/plantilla/")
        self.assertEqual((r.status_code, r.get_json()["error"]), (401, "FALTAN_HEADERS"))
        r = self.cli.post("/api/plantilla/", json={"nombre": "x"}, headers=VEN)
        self.assertEqual((r.status_code, r.get_json()["error"]), (403, "SIN_PERMISO"))

    def test_crear_y_listar_con_paginacion(self):
        for i in range(3):
            self.assertEqual(self.cli.post("/api/plantilla/", json={"nombre": f"E{i}"}, headers=ADM).status_code, 201)
        datos = self.cli.get("/api/plantilla/?porPagina=2", headers=VEN).get_json()
        self.assertEqual(len(datos["datos"]), 2)
        self.assertEqual(datos["paginacion"]["totalPaginas"], 2)

    def test_validacion_y_formato_de_error(self):
        r = self.cli.post("/api/plantilla/", json={}, headers=ADM)
        self.assertEqual(r.status_code, 400)
        self.assertEqual(set(r.get_json()), {"error", "detalle"})

    def test_llamada_interna_solo_lectura(self):
        self.assertEqual(self.cli.get("/api/plantilla/", headers=INTERNO).status_code, 200)
        self.assertEqual(self.cli.post("/api/plantilla/", json={"nombre": "x"}, headers=INTERNO).status_code, 403)
        self.assertEqual(self.cli.get("/api/plantilla/", headers=INTERNO_NO_PERMITIDO).status_code, 403)


if __name__ == "__main__":
    unittest.main()
