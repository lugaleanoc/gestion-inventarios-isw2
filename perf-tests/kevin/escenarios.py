TIPOS = {
    "normal": {"nombre": "Normal", "usuarios": 20, "rampa": 5, "duracion": "60s"},
    "pico": {"nombre": "Pico", "usuarios": 100, "rampa": 25, "duracion": "60s"},
    "estres": {"nombre": "Estrés", "usuarios": 300, "rampa": 50, "duracion": "60s"},
}

ENDPOINTS = [
    ("login", "Gateway", "POST", "/api/auth/login", "Inicio de sesión (contraseña y emisión de JWT)"),
    ("por_producto", "Proveedores", "GET", "/api/proveedores/por-producto/{id}", "Consulta que usan Reposición e Inventario"),
    ("crear_proveedor", "Proveedores", "POST", "/api/proveedores", "Escritura: creación de proveedores"),
    ("dashboard", "Reportes", "GET", "/api/reportes/dashboard", "Dashboard consolidado (con caché)"),
    ("sin_cache", "Reportes", "GET", "/api/reportes/ventas-por-canal?refrescar=true", "Reporte sin caché, consultando a Ventas"),
]

PRUEBAS = {}
for i, (tarea, servicio, metodo, endpoint, mide) in enumerate(ENDPOINTS):
    for j, escenario in enumerate(("normal", "pico", "estres")):
        PRUEBAS[f"p{i * 3 + j + 1:02d}"] = {
            "tarea": tarea, "escenario": escenario, "servicio": servicio,
            "metodo": metodo, "endpoint": endpoint, "mide": mide,
        }
