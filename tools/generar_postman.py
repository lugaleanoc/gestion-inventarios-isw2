import json
import os
import re

SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "postman", "JAK_Inventory.postman_collection.json")


def pedido(nombre, metodo, ruta, cuerpo=None, esperado=200, publico=False, guardar=None, extra_tests=None):
    ruta_limpia, _, consulta = ruta.partition("?")
    camino = [parte for parte in ruta_limpia.split("/") if parte]
    url = {
        "raw": "{{base_url}}" + ruta,
        "host": ["{{base_url}}"],
        "path": camino,
    }
    if consulta:
        url["query"] = [
            {"key": par.split("=", 1)[0], "value": par.split("=", 1)[1] if "=" in par else ""}
            for par in consulta.split("&")
        ]
    codigo = [f'pm.test("Responde {esperado}", function () {{ pm.response.to.have.status({esperado}); }});']
    if guardar:
        codigo.append("let datos = {};")
        codigo.append("try { datos = pm.response.json(); } catch (e) {}")
        for variable, campo in guardar.items():
            codigo.append(
                f'try {{ const valor = datos.{campo}; if (valor !== undefined) {{ pm.collectionVariables.set("{variable}", valor); }} }} catch (e) {{}}'
            )
    codigo += extra_tests or []
    item = {
        "name": nombre,
        "event": [{"listen": "test", "script": {"type": "text/javascript", "exec": codigo}}],
        "request": {
            "method": metodo,
            "header": [{"key": "Content-Type", "value": "application/json"}] if cuerpo is not None else [],
            "url": url,
        },
    }
    if cuerpo is not None:
        bruto = json.dumps(cuerpo, indent=2, ensure_ascii=False)
        bruto = re.sub(r'"\{\{(productoId|localId|bodegaId|categoriaId|solicitudId|ordenId|proveedorId)\}\}"', r"{{\1}}", bruto)
        item["request"]["body"] = {
            "mode": "raw",
            "raw": bruto,
            "options": {"raw": {"language": "json"}},
        }
    if publico:
        item["request"]["auth"] = {"type": "noauth"}
    return item


def carpeta(nombre, items, descripcion=""):
    return {"name": nombre, "description": descripcion, "item": items}


ADMIN_REGISTRO = {
    "nombreEmpresa": "Empresa Demo",
    "nit": "900123456-7",
    "administrador": {"nombre": "Ana Administradora", "correo": "{{correo}}", "contrasena": "{{contrasena}}"},
}

PROVEEDOR = {
    "nombre": "Distribuidora Andina",
    "nit": "800123456-1",
    "contacto": {"nombre": "Laura Gómez", "telefono": "3001234567", "correo": "ventas@andina.co"},
    "condiciones": {"plazoEntregaDias": 5, "formaPago": "30 días", "pedidoMinimo": 150000},
}

guardar_sesion = {"token": "token"}

items = [
    carpeta(
        "00 Salud",
        [pedido("Gateway /health", "GET", "/health", publico=True)],
    ),
    carpeta(
        "01 Gateway · Autenticación",
        [
            pedido("Registrar empresa", "POST", "/api/empresas/registro", ADMIN_REGISTRO, 201, True),
            pedido("Login", "POST", "/api/auth/login", {"correo": "{{correo}}", "contrasena": "{{contrasena}}"}, 200, True, guardar_sesion),
            pedido("Login con contraseña incorrecta (401)", "POST", "/api/auth/login", {"correo": "{{correo}}", "contrasena": "Incorrecta1"}, 401, True),
            pedido("Cambiar contraseña", "PUT", "/api/auth/contrasena", {"contrasenaActual": "{{contrasena}}", "nuevaContrasena": "{{contrasena}}"}, 204),
            pedido("Solicitar recuperación", "POST", "/api/auth/recuperacion", {"correo": "{{correo}}"}, 202, True, {"codigoRecuperacion": "codigoRecuperacion"}),
            pedido("Restablecer contraseña", "POST", "/api/auth/restablecimiento", {"codigoRecuperacion": "{{codigoRecuperacion}}", "nuevaContrasena": "{{contrasena}}"}, 204, True),
        ],
        "Orden sugerido: registrar empresa y login. El logout está en la carpeta 08, al final, porque invalida el token.",
    ),
    carpeta(
        "02 Gateway · Usuarios",
        [
            pedido("Listar usuarios", "GET", "/api/usuarios?pagina=1&porPagina=20"),
            pedido("Crear usuario vendedor", "POST", "/api/usuarios", {"nombre": "Vera Vendedora", "correo": "vera@demo.co", "contrasena": "Clave12345", "rol": "vendedor"}, 201, False, {"usuarioId": "usuarioId"}),
            pedido("Consultar usuario", "GET", "/api/usuarios/{{usuarioId}}"),
            pedido("Actualizar usuario", "PUT", "/api/usuarios/{{usuarioId}}", {"rol": "encargado_bodega"}),
            pedido("Dar de baja usuario", "DELETE", "/api/usuarios/{{usuarioId}}"),
        ],
    ),
    carpeta(
        "03 Gateway · Tiendas web",
        [
            pedido("Listar tiendas web", "GET", "/api/tiendas-web"),
            pedido("Registrar tienda web", "POST", "/api/tiendas-web", {"nombre": "Tienda online"}, 201, False, {"tiendaId": "tiendaId", "clienteId": "clienteId", "claveSecreta": "claveSecreta"}),
            pedido("Token de tienda web", "POST", "/api/auth/token-tienda", {"clienteId": "{{clienteId}}", "claveSecreta": "{{claveSecreta}}"}, 200, True),
            pedido("Dar de baja tienda web", "DELETE", "/api/tiendas-web/{{tiendaId}}"),
        ],
    ),
    carpeta(
        "04 Gateway · Rutas internas (deben dar 403)",
        [
            pedido("POST inventario/stock/descuentos", "POST", "/api/inventario/stock/descuentos", {"ventaId": 1, "items": []}, 403),
            pedido("POST inventario/stock/entradas", "POST", "/api/inventario/stock/entradas", {"ordenId": 1, "items": []}, 403),
            pedido("POST reposicion/solicitudes/automaticas", "POST", "/api/reposicion/solicitudes/automaticas", {"productoId": 1, "stockActual": 0}, 403),
            pedido("POST balance/movimientos/ventas", "POST", "/api/balance/movimientos/ventas", {"ventaId": 1}, 403),
            pedido("POST configuracion/empresas", "POST", "/api/configuracion/empresas", {"nombre": "X", "nit": "1"}, 403),
        ],
        "Para la demo: con el token ya iniciado, cualquiera de estas peticiones debe responder 403 SIN_PERMISO.",
    ),
    carpeta(
        "05 Proveedores",
        [
            pedido("Listar proveedores", "GET", "/api/proveedores?activo=true&pagina=1&porPagina=20"),
            pedido("Crear proveedor", "POST", "/api/proveedores", PROVEEDOR, 201, False, {"proveedorId": "proveedorId"}),
            pedido("Consultar proveedor", "GET", "/api/proveedores/{{proveedorId}}"),
            pedido("Actualizar proveedor", "PUT", "/api/proveedores/{{proveedorId}}", PROVEEDOR),
            pedido("Asociar producto", "POST", "/api/proveedores/{{proveedorId}}/productos", {"productoId": "{{productoId}}", "precioCompra": 2500, "principal": True}, 201),
            pedido("Productos del proveedor", "GET", "/api/proveedores/{{proveedorId}}/productos"),
            pedido("Proveedores de un producto", "GET", "/api/proveedores/por-producto/{{productoId}}"),
            pedido("Quitar producto del proveedor", "DELETE", "/api/proveedores/{{proveedorId}}/productos/{{productoId}}"),
            pedido("Dar de baja proveedor", "DELETE", "/api/proveedores/{{proveedorId}}"),
        ],
    ),
    carpeta(
        "06 Reportes",
        [
            pedido("Dashboard", "GET", "/api/reportes/dashboard"),
            pedido("Dashboard de un local, sin caché", "GET", "/api/reportes/dashboard?localId={{localId}}&refrescar=true"),
            pedido("Ventas por canal", "GET", "/api/reportes/ventas-por-canal?fechaDesde=2026-11-01&fechaHasta=2026-11-30"),
            pedido("Inventario", "GET", "/api/reportes/inventario"),
            pedido("Productos agotados", "GET", "/api/reportes/productos-agotados"),
            pedido("Reposiciones", "GET", "/api/reportes/reposiciones"),
            pedido("Balance", "GET", "/api/reportes/balance?fechaDesde=2026-11-01&fechaHasta=2026-11-30"),
            pedido("Reporte de un local", "GET", "/api/reportes/locales/{{localId}}"),
        ],
        "Para mostrar el reporte parcial: apagar Balance Diario y pedir Balance o Dashboard con refrescar=true. La respuesta trae fuentesNoDisponibles: [\"balance\"].",
    ),
    carpeta(
        "07 Demo · flujo completo (servicios de Amanda y Jasmin)",
        [
            pedido("1. Crear local", "POST", "/api/configuracion/locales", {"nombre": "Sede Centro", "direccion": "Calle 20 # 21-10", "ciudad": "Manizales"}, 201, False, {"localId": "localId"}),
            pedido("2. Stock mínimo de un producto", "PUT", "/api/configuracion/stock-minimo/{{productoId}}", {"stockMinimo": 10}),
            pedido("3. Crear categoría", "POST", "/api/inventario/categorias", {"nombre": "Abarrotes"}, 201, False, {"categoriaId": "categoriaId"}),
            pedido("4. Crear bodega", "POST", "/api/inventario/bodegas", {"nombre": "Bodega principal", "localId": "{{localId}}"}, 201, False, {"bodegaId": "bodegaId"}),
            pedido("5. Crear producto", "POST", "/api/inventario/productos", {"codigo": "ARR-001", "nombre": "Arroz 500 g", "categoriaId": "{{categoriaId}}", "unidadMedida": "unidad", "precio": 3200, "proveedorId": "{{proveedorId}}"}, 201, False, {"productoId": "productoId"}),
            pedido("6. Registrar entrada de stock", "POST", "/api/inventario/movimientos", {"tipo": "entrada", "productoId": "{{productoId}}", "bodegaId": "{{bodegaId}}", "cantidad": 50, "motivo": "Compra inicial"}, 201),
            pedido("7. Ver kardex", "GET", "/api/inventario/movimientos?productoId={{productoId}}"),
            pedido("8. Registrar venta", "POST", "/api/ventas", {"localId": "{{localId}}", "bodegaId": "{{bodegaId}}", "canal": "tienda_fisica", "medioPago": "efectivo", "items": [{"productoId": "{{productoId}}", "cantidad": 45}]}, 201, False, {"ventaId": "ventaId"}),
            pedido("9. Balance del día", "GET", "/api/balance/diario?localId={{localId}}"),
            pedido("10. Alertas de inventario", "GET", "/api/inventario/alertas"),
            pedido("11. Solicitudes de reposición", "GET", "/api/reposicion/solicitudes?estado=pendiente", None, 200, False, {"solicitudId": "datos[0].solicitudId"}),
            pedido("12. Aprobar solicitud", "POST", "/api/reposicion/solicitudes/{{solicitudId}}/aprobacion", {}),
            pedido("13. Emitir orden", "POST", "/api/reposicion/ordenes", {"solicitudId": "{{solicitudId}}"}, 201, False, {"ordenId": "ordenId"}),
            pedido("14. Recibir mercancía", "POST", "/api/reposicion/ordenes/{{ordenId}}/recepcion", {"bodegaId": "{{bodegaId}}", "cantidadRecibida": 50}),
        ],
        "Sigue el guion de la demo. Los cuerpos salen de los contratos de la Entrega 2; si algún servicio cambió un campo, ajusta aquí.",
    ),
]

items.append(
    carpeta(
        "08 Cerrar sesión",
        [pedido("Logout", "POST", "/api/auth/logout", None, 204)],
        "Invalida el token actual. Después hay que volver a hacer Login.",
    )
)

coleccion = {
    "info": {
        "name": "JAK Inventory · Entrega 3",
        "description": "Todas las peticiones entran por el API Gateway. Primero: Registrar empresa y Login (guarda el token solo).",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "auth": {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]},
    "item": items,
    "variable": [
        {"key": "base_url", "value": "http://localhost:8080"},
        {"key": "correo", "value": "admin@demo.co"},
        {"key": "contrasena", "value": "Clave12345"},
        {"key": "token", "value": ""},
        {"key": "productoId", "value": "1"},
        {"key": "localId", "value": "1"},
        {"key": "proveedorId", "value": ""},
        {"key": "usuarioId", "value": ""},
        {"key": "tiendaId", "value": ""},
        {"key": "clienteId", "value": ""},
        {"key": "claveSecreta", "value": ""},
        {"key": "codigoRecuperacion", "value": ""},
        {"key": "categoriaId", "value": ""},
        {"key": "bodegaId", "value": ""},
        {"key": "ventaId", "value": ""},
        {"key": "solicitudId", "value": ""},
        {"key": "ordenId", "value": ""},
    ],
}

os.makedirs(os.path.dirname(SALIDA), exist_ok=True)
with open(SALIDA, "w", encoding="utf-8") as archivo:
    json.dump(coleccion, archivo, indent=2, ensure_ascii=False)
print("Colección escrita con", sum(len(c["item"]) for c in items), "peticiones")
