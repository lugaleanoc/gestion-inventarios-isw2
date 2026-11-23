"""Carga los datos que necesitan las pruebas de rendimiento (correr UNA vez antes).

    python datos_prueba.py

Pasos:
1. Crea la empresa de pruebas en Configuracion (POST /api/configuracion/empresas
   con X-Servicio-Origen: gateway, como lo haria el API Gateway).
2. Crea el local "Sede Centro", o reutiliza el que ya exista.
3. Define stock minimo propio para los productos 1 a 10 (los productos 11 a 20
   usan el de la empresa, asi E1 prueba los dos caminos).
4. Si Inventario esta corriendo, crea categoria, bodega, 20 productos y
   existencias. Si no esta, se lo salta: Ventas trabaja en modo simulado
   (USAR_MOCK_INVENTARIO=true) y no lo necesita.
5. Guarda los ids en datos_prueba.json; locustfile.py los lee de ahi.

Se puede correr varias veces: lo que ya existe se reutiliza.
"""

import json
import os
import sys

import requests

CONFIGURACION = os.getenv("CONFIGURACION_URL", "http://localhost:8003")
# Puerto que publica Inventario en docker-compose.yml.
INVENTARIO = os.getenv("INVENTARIO_URL", "http://localhost:8001")

CARPETA = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_DATOS = os.path.join(CARPETA, "datos_prueba.json")

EMPRESA = {"nombre": "Empresa Pruebas Jasmin", "nit": "900999001-1"}
LOCAL = {"nombre": "Sede Centro", "direccion": "Cra 23 # 25-10", "ciudad": "Manizales"}
PRODUCTOS = list(range(1, 21))


def enviar(metodo, url, headers, cuerpo=None, aceptados=(200, 201)):
    """Hace la peticion y se detiene con un mensaje claro si la respuesta no es la esperada."""
    r = requests.request(metodo, url, json=cuerpo, headers=headers, timeout=10)
    if r.status_code not in aceptados:
        sys.exit("ERROR {} {} -> {} {}".format(metodo, url, r.status_code, r.text[:300]))
    return r


def esta_arriba(url):
    """True si el servicio responde /health."""
    try:
        return requests.get(url + "/health", timeout=2).status_code == 200
    except requests.RequestException:
        return False


def datos_guardados():
    """Lee datos_prueba.json de una ejecucion anterior (o {} si no existe)."""
    try:
        with open(ARCHIVO_DATOS, encoding="utf-8") as archivo:
            return json.load(archivo)
    except (OSError, ValueError):
        return {}


def crear_empresa():
    """Paso 1. Devuelve el empresaId."""
    r = enviar("POST", CONFIGURACION + "/api/configuracion/empresas",
               {"X-Servicio-Origen": "gateway"}, EMPRESA, aceptados=(201, 409))
    if r.status_code == 201:
        empresa_id = r.json()["empresaId"]
        print("Empresa creada: {}".format(empresa_id))
        return empresa_id

    # 409: la empresa ya existia. El contrato no tiene "buscar por NIT", asi
    # que se usa el id guardado la vez anterior.
    empresa_id = datos_guardados().get("empresaId")
    if empresa_id is None:
        sys.exit("La empresa con NIT {} ya existe pero no esta en datos_prueba.json. "
                 "Borra los datos con  docker compose down -v  y vuelve a empezar.".format(EMPRESA["nit"]))
    print("Empresa ya existia: {}".format(empresa_id))
    return empresa_id


def crear_local(admin):
    """Paso 2. Reutiliza el local si ya existe; devuelve el localId."""
    r = enviar("GET", CONFIGURACION + "/api/configuracion/locales", admin)
    for local in r.json():
        if local["nombre"] == LOCAL["nombre"]:
            print("Local ya existia: {}".format(local["localId"]))
            return local["localId"]
    r = enviar("POST", CONFIGURACION + "/api/configuracion/locales", admin, LOCAL)
    print("Local creado: {}".format(r.json()["localId"]))
    return r.json()["localId"]


def cargar_inventario(admin, local_id):
    """Paso 4 (opcional). Crea productos y existencias en Inventario.

    Devuelve los ids de los productos creados, o PRODUCTOS (1 a 20) si se omite.
    """
    if not esta_arriba(INVENTARIO):
        print("Inventario no esta corriendo en {}: se omite (Ventas usa el modo simulado)".format(INVENTARIO))
        return PRODUCTOS

    r = enviar("POST", INVENTARIO + "/api/inventario/categorias", admin, {"nombre": "Papeleria"},
               aceptados=(201, 409))
    categoria_id = r.json().get("categoriaId", 1)
    r = enviar("POST", INVENTARIO + "/api/inventario/bodegas", admin,
               {"nombre": "Bodega Principal", "localId": local_id}, aceptados=(201, 409))
    bodega_id = r.json().get("bodegaId", 1)

    creados = []
    for i in PRODUCTOS:
        r = enviar("POST", INVENTARIO + "/api/inventario/productos", admin, {
            "codigo": "P{:03d}".format(i), "nombre": "Producto {}".format(i),
            "categoriaId": categoria_id, "unidadMedida": "unidad", "precio": 1000 * i,
        }, aceptados=(201, 409))
        if r.status_code == 201:
            creados.append(r.json()["productoId"])
            # Mucho stock: E3 registra miles de ventas y no debe quedarse sin existencias.
            enviar("POST", INVENTARIO + "/api/inventario/movimientos", admin, {
                "tipo": "entrada", "productoId": r.json()["productoId"], "bodegaId": bodega_id,
                "cantidad": 100000, "motivo": "Carga inicial pruebas",
            }, aceptados=(200, 201))
    print("Inventario cargado: bodega {} y {} productos".format(bodega_id, len(creados)))
    # Si los productos ya existian (409), se usan los ids guardados antes.
    return creados or datos_guardados().get("productos", PRODUCTOS)


def main():
    if not esta_arriba(CONFIGURACION):
        sys.exit("Configuracion no responde en {}. Levanta los servicios con:\n"
                 "  docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build"
                 .format(CONFIGURACION))

    empresa_id = crear_empresa()
    admin = {"X-Empresa-Id": str(empresa_id), "X-Usuario-Id": "1", "X-Rol": "administrador"}
    local_id = crear_local(admin)

    # Paso 3: stock minimo propio para los productos 1 a 10.
    for producto_id in PRODUCTOS[:10]:
        enviar("PUT", CONFIGURACION + "/api/configuracion/stock-minimo/{}".format(producto_id),
               admin, {"stockMinimo": 8})
    print("Stock minimo definido para los productos 1 a 10")

    productos = cargar_inventario(admin, local_id)

    # Paso 5: guardar los ids para locustfile.py.
    with open(ARCHIVO_DATOS, "w", encoding="utf-8") as archivo:
        json.dump({"empresaId": empresa_id, "localId": local_id, "productos": productos}, archivo, indent=2)
    print("Datos de prueba listos ({})".format(os.path.basename(ARCHIVO_DATOS)))


if __name__ == "__main__":
    main()
