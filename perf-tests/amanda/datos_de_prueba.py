"""Siembra datos de prueba en Inventario antes de medir.

Medir sobre una base vacia no sirve: cualquier consulta es instantanea
porque no hay nada que buscar. Este script crea una categoria, dos bodegas
y varios productos con existencias, para que las consultas tengan que
trabajar de verdad.

Uso (con los servicios ya levantados):

    python datos_de_prueba.py                 # 500 productos
    python datos_de_prueba.py --productos 2000

Al final guarda datos_sembrados.json con los ids creados, que es lo que
lee el locustfile para saber a que productos pedirle el stock.
"""

import argparse
import json
import random
import sys
import time

import requests

# Cabeceras que normalmente pondria el API Gateway. Como el Gateway es de
# Kevin y aqui medimos solo nuestros servicios, se mandan a mano.
ADMIN = {
    "X-Empresa-Id": "1",
    "X-Usuario-Id": "1",
    "X-Rol": "administrador",
    "Content-Type": "application/json",
}

CATEGORIAS = ["Cuadernos", "Lapices", "Papeleria", "Escolar", "Oficina"]
PALABRAS = ["argollado", "cosido", "rayado", "cuadriculado", "ejecutivo",
            "economico", "grande", "pequeno", "profesional", "escolar"]


def pedir(metodo, url, **kwargs):
    """Hace una peticion y corta el script con un mensaje claro si falla."""
    try:
        r = requests.request(metodo, url, timeout=15, **kwargs)
    except requests.RequestException as exc:
        print("\nNo se pudo conectar a {}".format(url))
        print("Revisa que los servicios esten arriba:  docker compose ps")
        print("Detalle: {}".format(exc))
        sys.exit(1)
    return r


def sembrar(inventario, cantidad_productos):
    """Crea la categoria, las bodegas y los productos con stock."""
    print("Sembrando datos en {} ...".format(inventario))

    # --- Categoria ---
    r = pedir("POST", inventario + "/api/inventario/categorias",
              headers=ADMIN, json={"nombre": "Pruebas de rendimiento"})
    if r.status_code == 201:
        categoria_id = r.json()["categoriaId"]
    else:
        # 409 = ya existe de una corrida anterior; se busca cual es.
        listado = pedir("GET", inventario + "/api/inventario/categorias", headers=ADMIN).json()
        categoria_id = next(c["categoriaId"] for c in listado
                            if c["nombre"] == "Pruebas de rendimiento")
    print("  categoria  {}".format(categoria_id))

    # --- Bodegas ---
    # Dos bodegas para poder medir tambien traslados y stock repartido.
    bodegas = []
    for nombre in ("Bodega pruebas 1", "Bodega pruebas 2"):
        r = pedir("POST", inventario + "/api/inventario/bodegas",
                  headers=ADMIN, json={"nombre": nombre, "localId": 1})
        if r.status_code == 201:
            bodegas.append(r.json()["bodegaId"])
        else:
            listado = pedir("GET", inventario + "/api/inventario/bodegas",
                            headers=ADMIN).json()
            bodegas.append(next(b["bodegaId"] for b in listado if b["nombre"] == nombre))
    print("  bodegas    {}".format(bodegas))

    # --- Productos ---
    productos = []
    inicio = time.time()
    for i in range(cantidad_productos):
        codigo = "PERF-{:05d}".format(i)
        nombre = "Cuaderno {} {}".format(random.choice(PALABRAS), random.choice(PALABRAS))
        r = pedir("POST", inventario + "/api/inventario/productos", headers=ADMIN, json={
            "codigo": codigo,
            "nombre": nombre,
            "descripcion": "Producto creado para las pruebas de rendimiento",
            "categoriaId": categoria_id,
            "unidadMedida": "unidad",
            "precio": round(random.uniform(1000, 90000), 2),
        })
        if r.status_code == 201:
            productos.append(r.json()["productoId"])
        elif r.status_code == 409:
            # Ya existia: se busca su id para poder usarlo igual.
            encontrado = pedir("GET", inventario + "/api/inventario/productos",
                               headers=ADMIN, params={"q": codigo}).json()
            if encontrado["datos"]:
                productos.append(encontrado["datos"][0]["productoId"])
        else:
            print("  aviso: el producto {} respondio {}".format(codigo, r.status_code))

        if (i + 1) % 100 == 0:
            print("  productos  {}/{}".format(i + 1, cantidad_productos))

    # --- Stock ---
    # Se carga mucho stock a proposito: las pruebas de escritura descuentan
    # miles de unidades y no deben fallar por quedarse sin existencias.
    # Si fallaran por eso, estariamos midiendo errores de negocio y no
    # rendimiento.
    print("  cargando existencias ...")
    for n, producto_id in enumerate(productos, start=1):
        pedir("POST", inventario + "/api/inventario/movimientos", headers=ADMIN, json={
            "tipo": "entrada",
            "productoId": producto_id,
            "bodegaId": bodegas[0],
            "cantidad": 1000000,
            "motivo": "Carga inicial para pruebas de rendimiento",
        })
        if n % 100 == 0:
            print("  existencias {}/{}".format(n, len(productos)))

    datos = {
        "inventario": inventario,
        "categoriaId": categoria_id,
        "bodegas": bodegas,
        "productos": productos,
    }
    with open("datos_sembrados.json", "w", encoding="utf-8") as archivo:
        json.dump(datos, archivo, indent=2)

    print("\nListo: {} productos en {:.0f} segundos.".format(
        len(productos), time.time() - inicio))
    print("Ids guardados en datos_sembrados.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventario", default="http://localhost:8001",
                        help="URL del servicio de Inventario")
    parser.add_argument("--productos", type=int, default=500,
                        help="cuantos productos crear")
    args = parser.parse_args()
    sembrar(args.inventario.rstrip("/"), args.productos)
