from datetime import date

from flask import Flask, jsonify, request

app = Flask(__name__)
app.json.sort_keys = False
app.json.ensure_ascii = False

ORIGENES = {"gateway", "reportes", "ventas", "reposicion", "inventario", "proveedores", "configuracion", "balance"}
METRICAS = [
    "ventas_por_canal",
    "productos_baja_rotacion",
    "productos_agotados",
    "estado_reposiciones",
    "balance_diario",
    "ingresos_egresos",
    "valor_inventario",
]
estado = {"empresas": {}, "caidos": set()}


def totales(efectivo, tarjeta, qr):
    return {"efectivo": efectivo, "tarjeta": tarjeta, "qr": qr, "total": efectivo + tarjeta + qr}


@app.before_request
def controlar():
    if request.path == "/health" or request.path.startswith("/__"):
        return None
    if request.headers.get("X-Servicio-Origen") not in ORIGENES:
        return jsonify({"error": "SIN_PERMISO", "detalle": "Falta X-Servicio-Origen"}), 403
    partes = request.path.split("/")
    if len(partes) > 2 and partes[2] in estado["caidos"]:
        return jsonify({"error": "SERVICIO_NO_DISPONIBLE", "detalle": "Servicio simulado como caído"}), 503
    return None


@app.get("/health")
def health():
    return jsonify({"estado": "ok", "servicio": "mock-servicios"})


@app.post("/__caidos/<servicio>")
def apagar(servicio):
    estado["caidos"].add(servicio)
    return jsonify({"caidos": sorted(estado["caidos"])})


@app.delete("/__caidos/<servicio>")
def encender(servicio):
    estado["caidos"].discard(servicio)
    return jsonify({"caidos": sorted(estado["caidos"])})


@app.post("/api/configuracion/empresas")
def crear_empresa():
    datos = request.get_json(silent=True) or {}
    nit = datos.get("nit")
    if nit in estado["empresas"]:
        return jsonify({"error": "NIT_DUPLICADO", "detalle": "Ya existe una empresa con ese NIT"}), 409
    empresa_id = len(estado["empresas"]) + 1
    empresa = {
        "empresaId": empresa_id,
        "nombre": datos.get("nombre"),
        "nit": nit,
        "stockMinimoPorDefecto": 5,
        "activa": True,
        "fechaCreacion": date.today().isoformat(),
    }
    estado["empresas"][nit] = empresa
    return jsonify(empresa), 201


@app.get("/api/configuracion/dashboard")
def config_dashboard():
    return jsonify({"metricas": METRICAS, "preferencias": {"localPorDefecto": 1, "periodoPorDefecto": "ultimos_30_dias"}})


@app.get("/api/configuracion/locales")
def locales():
    return jsonify([{"localId": i, "nombre": f"Local {i}", "activo": True} for i in (1, 2)])


@app.get("/api/configuracion/locales/<int:local_id>")
def local(local_id):
    if local_id not in (1, 2):
        return jsonify({"error": "LOCAL_NO_ENCONTRADO", "detalle": "No existe el local"}), 404
    return jsonify({"localId": local_id, "nombre": f"Local {local_id}", "direccion": "Calle 1", "ciudad": "Manizales", "activo": True})


@app.get("/api/ventas/resumen")
def ventas_resumen():
    return jsonify(
        {
            "fechaDesde": request.args.get("fechaDesde"),
            "fechaHasta": request.args.get("fechaHasta"),
            "localId": request.args.get("localId", type=int),
            "totalVentas": 2350000,
            "cantidadVentas": 31,
            "porCanal": {"tienda_fisica": 1800000, "tienda_web": 550000},
            "porMedioPago": {"efectivo": 900000, "tarjeta": 1100000, "qr": 350000},
        }
    )


@app.get("/api/inventario/indicadores")
def indicadores():
    return jsonify(
        {
            "valorTotal": 18400000,
            "cantidadProductos": 64,
            "productosAgotados": [{"productoId": 7, "nombre": "Aceite 1L", "stockTotal": 0}],
            "productosBajoMinimo": [{"productoId": 3, "nombre": "Arroz 500g", "stockTotal": 2}],
            "mayorRotacion": [{"productoId": 1, "nombre": "Leche 1L", "unidadesSalidas": 120}],
            "menorRotacion": [{"productoId": 12, "nombre": "Sal marina", "unidadesSalidas": 1}],
        }
    )


@app.get("/api/reposicion/resumen")
def reposicion_resumen():
    return jsonify({"pendiente": 2, "aprobada": 1, "rechazada": 0, "en_orden": 1, "recibida": 3})


@app.get("/api/balance/diario")
def balance_diario():
    return jsonify(
        {
            "localId": request.args.get("localId", type=int),
            "fecha": request.args.get("fecha"),
            "ingresos": totales(400000, 350000, 90000),
            "egresos": totales(120000, 0, 0),
            "ajustes": totales(0, 0, 0),
            "disponible": totales(280000, 350000, 90000),
            "ventasPorCanal": {"tienda_fisica": 740000, "tienda_web": 100000},
        }
    )


@app.get("/api/balance/reporte")
def balance_reporte():
    return jsonify(
        {
            "fechaDesde": request.args.get("fechaDesde"),
            "fechaHasta": request.args.get("fechaHasta"),
            "balances": [
                {"localId": 1, "fecha": "2026-11-18", "ingresos": totales(350000, 300000, 80000), "egresos": totales(100000, 0, 0), "disponible": totales(250000, 300000, 80000)},
                {"localId": 1, "fecha": "2026-11-19", "ingresos": totales(400000, 350000, 90000), "egresos": totales(120000, 0, 0), "disponible": totales(280000, 350000, 90000)},
            ],
            "totales": totales(0, 0, 0),
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
