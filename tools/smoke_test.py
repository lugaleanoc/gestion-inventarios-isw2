import argparse
import sys
import time

import requests

parser = argparse.ArgumentParser()
parser.add_argument("--gateway", default="http://127.0.0.1:18080")
parser.add_argument("--mock", default=None)
parser.add_argument("--proveedores", default=None, help="URL directa de Proveedores (solo si está expuesto)")
parser.add_argument("--reportes", default=None, help="URL directa de Reportes (solo si está expuesto)")
args = parser.parse_args()

G = args.gateway.rstrip("/")
fallos = []


def verificar(nombre, condicion, detalle=""):
    print(("OK    " if condicion else "FALLA ") + nombre + ("" if condicion else f"  -> {detalle}"))
    if not condicion:
        fallos.append(nombre)


def auth(token):
    return {"Authorization": f"Bearer {token}"}


sufijo = str(int(time.time()))
correo = f"admin{sufijo}@jak.co"
clave = "Clave1234"

r = requests.get(f"{G}/health", timeout=10)
verificar("Gateway responde /health", r.status_code == 200, r.text)

r = requests.post(
    f"{G}/api/empresas/registro",
    json={"nombreEmpresa": "Empresa Demo", "nit": f"900{sufijo}", "administrador": {"nombre": "Ana", "correo": correo, "contrasena": clave}},
    timeout=20,
)
verificar("Registro de empresa (201)", r.status_code == 201 and set(r.json()) == {"empresaId", "usuarioId"}, r.text)

r = requests.post(f"{G}/api/auth/login", json={"correo": correo, "contrasena": clave}, timeout=20)
verificar("Login (200)", r.status_code == 200, r.text)
token = r.json()["token"]
verificar("expiraEn viene en segundos", isinstance(r.json()["expiraEn"], int), r.text)
admin = auth(token)

r = requests.post(f"{G}/api/auth/login", json={"correo": correo, "contrasena": "Mala12345"}, timeout=20)
verificar("Login con clave mala (401)", r.status_code == 401, r.text)

r = requests.get(f"{G}/api/proveedores", timeout=10)
verificar("Sin token (401)", r.status_code == 401, r.text)

r = requests.post(f"{G}/api/inventario/stock/descuentos", json={}, headers=admin, timeout=10)
verificar("Ruta interna con token válido (403)", r.status_code == 403 and r.json().get("error") == "SIN_PERMISO", r.text)

r = requests.post(
    f"{G}/api/proveedores",
    json={"nombre": "Distribuidora Andina", "nit": f"800{sufijo}", "contacto": {"correo": "ventas@andina.co"}, "condiciones": {"plazoEntregaDias": 3}},
    headers=admin,
    timeout=20,
)
verificar("Crear proveedor (201)", r.status_code == 201, r.text)
pid = r.json().get("proveedorId")

r = requests.post(f"{G}/api/proveedores/{pid}/productos", json={"productoId": 5, "precioCompra": 2500, "principal": False}, headers=admin, timeout=20)
verificar("Asociar producto (201)", r.status_code == 201 and r.json()["principal"] is False, r.text)

r = requests.get(f"{G}/api/proveedores/por-producto/5", headers=admin, timeout=20)
verificar("Proveedores por producto", r.status_code == 200 and r.json()[0]["proveedorId"] == pid, r.text)

r = requests.get(f"{G}/api/proveedores?q=Andina&activo=true", headers=admin, timeout=20)
verificar("Listar proveedores con filtros", r.status_code == 200 and r.json()["paginacion"]["total"] == 1, r.text)

r = requests.post(f"{G}/api/usuarios", json={"nombre": "Vera", "correo": f"vera{sufijo}@jak.co", "contrasena": clave, "rol": "vendedor"}, headers=admin, timeout=20)
verificar("Crear usuario vendedor (201)", r.status_code == 201, r.text)
r = requests.post(f"{G}/api/auth/login", json={"correo": f"vera{sufijo}@jak.co", "contrasena": clave}, timeout=20)
vendedor = auth(r.json()["token"])
r = requests.post(f"{G}/api/proveedores", json={"nombre": "X", "nit": "1"}, headers=vendedor, timeout=20)
verificar("Vendedor no crea proveedores (403)", r.status_code == 403, r.text)
r = requests.get(f"{G}/api/proveedores", headers=vendedor, timeout=20)
verificar("Vendedor sí consulta proveedores (200)", r.status_code == 200, r.text)

r = requests.post(f"{G}/api/tiendas-web", json={"nombre": "Tienda online"}, headers=admin, timeout=20)
verificar("Registrar tienda web (201)", r.status_code == 201, r.text)
tienda = r.json()
r = requests.post(f"{G}/api/auth/token-tienda", json={"clienteId": tienda["clienteId"], "claveSecreta": tienda["claveSecreta"]}, timeout=20)
verificar("Token de tienda web (200)", r.status_code == 200, r.text)

for ruta in ("dashboard", "ventas-por-canal", "inventario", "productos-agotados", "reposiciones", "balance", "locales/1"):
    r = requests.get(f"{G}/api/reportes/{ruta}", headers=admin, timeout=30)
    verificar(f"Reporte {ruta} (200)", r.status_code == 200 and "generadoEn" in r.json(), r.text[:200])

r = requests.get(f"{G}/api/reportes/dashboard", headers=admin, timeout=30)
verificar("Dashboard sale de la caché la segunda vez", r.json().get("desdeCache") is True, r.text[:200])
r = requests.get(f"{G}/api/reportes/locales/999", headers=admin, timeout=30)
verificar("Local inexistente (404)", r.status_code == 404, r.text[:200])
r = requests.get(f"{G}/api/reportes/ventas-por-canal", headers=auth(requests.post(f"{G}/api/auth/token-tienda", json={"clienteId": tienda["clienteId"], "claveSecreta": tienda["claveSecreta"]}, timeout=20).json()["token"]), timeout=20)
verificar("Tienda web no ve ventas por canal (403)", r.status_code == 403, r.text[:200])

if args.mock:
    requests.post(f"{args.mock}/__caidos/balance", timeout=10)
    r = requests.get(f"{G}/api/reportes/balance?refrescar=true", headers=admin, timeout=30)
    verificar("Reporte parcial con Balance apagado", r.status_code == 200 and r.json()["fuentesNoDisponibles"] == ["balance"], r.text[:300])
    r = requests.get(f"{G}/api/reportes/dashboard?refrescar=true", headers=admin, timeout=30)
    parcial = r.json()
    verificar("Dashboard parcial: el resto de métricas sigue", parcial["metricas"]["balance_diario"] == {} and parcial["metricas"]["valor_inventario"] is not None, r.text[:300])
    requests.delete(f"{args.mock}/__caidos/balance", timeout=10)
    time.sleep(6)
    r = requests.get(f"{G}/api/reportes/balance?refrescar=true", headers=admin, timeout=30)
    verificar("Balance vuelve a responder completo", r.json()["fuentesNoDisponibles"] == [], r.text[:300])

r = requests.post(f"{G}/api/auth/recuperacion", json={"correo": correo}, timeout=20)
codigo = r.json().get("codigoRecuperacion")
if codigo:
    r = requests.post(f"{G}/api/auth/restablecimiento", json={"codigoRecuperacion": codigo, "nuevaContrasena": "Nueva12345"}, timeout=20)
    verificar("Restablecer contraseña (204)", r.status_code == 204, r.text)
    r = requests.post(f"{G}/api/auth/login", json={"correo": correo, "contrasena": "Nueva12345"}, timeout=20)
    verificar("Login con la contraseña nueva", r.status_code == 200, r.text)
else:
    print("OMITIDO  recuperación de contraseña (el código solo llega por logs; activa EXPONER_CODIGO_RECUPERACION)")

r = requests.post(f"{G}/api/auth/logout", headers=admin, timeout=20)
verificar("Logout (204)", r.status_code == 204, r.text)
r = requests.get(f"{G}/api/proveedores", headers=admin, timeout=20)
verificar("Token revocado (401)", r.status_code == 401, r.text)

if args.proveedores:
    P = args.proveedores.rstrip("/")
    headers_admin = {"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "administrador"}
    r = requests.get(f"{P}/api/proveedores", timeout=10)
    verificar("Directo: sin headers (401 FALTAN_HEADERS)", r.status_code == 401 and r.json().get("error") == "FALTAN_HEADERS", r.text)
    r = requests.get(f"{P}/api/proveedores", headers={"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "vendedor"}, timeout=10)
    verificar("Directo: vendedor consulta (200)", r.status_code == 200, r.text)
    r = requests.post(f"{P}/api/proveedores", json={"nombre": "X", "nit": f"D{sufijo}"}, headers={"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "vendedor"}, timeout=10)
    verificar("Directo: vendedor no crea (403 SIN_PERMISO)", r.status_code == 403 and r.json().get("error") == "SIN_PERMISO", r.text)
    r = requests.get(f"{P}/api/proveedores", headers={"X-Servicio-Origen": "reposicion", "X-Empresa-Id": "1"}, timeout=10)
    verificar("Directo: reposicion consulta (200)", r.status_code == 200, r.text)
    r = requests.get(f"{P}/api/proveedores", headers={"X-Servicio-Origen": "ventas", "X-Empresa-Id": "1"}, timeout=10)
    verificar("Directo: ventas no puede consultar (403 SIN_PERMISO)", r.status_code == 403 and r.json().get("error") == "SIN_PERMISO", r.text)
    r = requests.post(f"{P}/api/proveedores", json={"nombre": "Directo", "nit": f"DIR{sufijo}"}, headers=headers_admin, timeout=10)
    verificar("Directo: administrador crea (201)", r.status_code == 201, r.text)

if args.reportes:
    R = args.reportes.rstrip("/")
    r = requests.get(f"{R}/api/reportes/dashboard", headers={"X-Empresa-Id": "1", "X-Usuario-Id": "1", "X-Rol": "vendedor"}, timeout=30)
    verificar("Directo: dashboard con headers (200)", r.status_code == 200, r.text[:200])
    r = requests.get(f"{R}/api/reportes/dashboard", timeout=10)
    verificar("Directo: reportes sin headers (401 FALTAN_HEADERS)", r.status_code == 401 and r.json().get("error") == "FALTAN_HEADERS", r.text)
    r = requests.get(f"{R}/api/reportes/dashboard", headers={"X-Servicio-Origen": "gateway", "X-Empresa-Id": "1"}, timeout=10)
    verificar("Directo: reportes rechaza llamadas entre servicios (403 SIN_PERMISO)", r.status_code == 403 and r.json().get("error") == "SIN_PERMISO", r.text)

print()
print("RESULTADO:", "TODO BIEN" if not fallos else f"{len(fallos)} FALLAS: {fallos}")
sys.exit(1 if fallos else 0)
