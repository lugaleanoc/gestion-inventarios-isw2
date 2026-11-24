"""Ejecuta las 15 pruebas de rendimiento, una tras otra.

    python ejecutar.py                 # las 15 (unos 45 minutos)
    python ejecutar.py --solo E1       # las 3 de un endpoint
    python ejecutar.py --escenario normal
    python ejecutar.py --prueba E3-estres

Cada prueba deja sus resultados en resultados/<id>_stats.csv. Cuando
terminen todas, con  python resumen.py  se arma la tabla para el informe.

Entre prueba y prueba hace una pausa para que el servicio se recupere: sin
ella, la prueba de estres dejaria el servidor caliente y la siguiente
empezaria con desventaja.
"""

import argparse
import os
import subprocess
import sys
import time

CARPETA = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = os.path.join(CARPETA, "resultados")

# --- Los escenarios que pide el enunciado -------------------------------
# usuarios: cuantos usuarios simultaneos simula Locust
# arranque: cuantos usuarios nuevos entran por segundo (rampa)
# duracion: cuanto dura la medicion
# Niveles acordados por el equipo el 23/11: los tres integrantes miden con
# los mismos numeros para que los resultados se puedan comparar entre si.
ESCENARIOS = {
    "normal": {"usuarios": 20, "arranque": 5, "duracion": "1m",
               "descripcion": "Carga normal: un dia comun de la empresa"},
    "pico": {"usuarios": 100, "arranque": 25, "duracion": "1m",
             "descripcion": "Carga pico: hora de mas ventas"},
    "estres": {"usuarios": 300, "arranque": 50, "duracion": "1m",
               "descripcion": "Estres: buscar donde empieza a fallar"},
}

# --- Los cinco endpoints ------------------------------------------------
ENDPOINTS = {
    "E1": {"clase": "E1_StockDeProducto",
           "titulo": "Consulta de stock de un producto",
           "servicio": "Inventario", "tipo": "lectura"},
    "E2": {"clase": "E2_BusquedaDeProductos",
           "titulo": "Busqueda de productos por texto",
           "servicio": "Inventario", "tipo": "lectura"},
    "E3": {"clase": "E3_DescuentoDeStock",
           "titulo": "Descuento de stock por venta",
           "servicio": "Inventario", "tipo": "escritura"},
    "E4": {"clase": "E4_ResumenDeReposicion",
           "titulo": "Resumen de solicitudes y ordenes",
           "servicio": "Reposicion", "tipo": "lectura"},
    "E5": {"clase": "E5_SolicitudAutomatica",
           "titulo": "Creacion de solicitud automatica",
           "servicio": "Reposicion", "tipo": "escritura"},
}


def listado_de_pruebas():
    """Devuelve las 15 pruebas: cada endpoint en cada escenario."""
    pruebas = []
    for clave_endpoint in sorted(ENDPOINTS):
        for clave_escenario in ("normal", "pico", "estres"):
            pruebas.append({
                "id": "{}-{}".format(clave_endpoint, clave_escenario),
                "endpoint": clave_endpoint,
                "escenario": clave_escenario,
                **ENDPOINTS[clave_endpoint],
                **ESCENARIOS[clave_escenario],
            })
    return pruebas


def correr_una(prueba, pausa):
    """Lanza Locust para una prueba y espera a que termine."""
    print("\n" + "=" * 70)
    print("{}  {}".format(prueba["id"], prueba["titulo"]))
    print("  {} usuarios, rampa {}/s, durante {}".format(
        prueba["usuarios"], prueba["arranque"], prueba["duracion"]))
    print("  {}".format(prueba["descripcion"]))
    print("=" * 70)

    comando = [
        sys.executable, "-m", "locust",
        "-f", os.path.join(CARPETA, "locustfile.py"),
        prueba["clase"],
        "--headless",                       # sin interfaz web
        "-u", str(prueba["usuarios"]),
        "-r", str(prueba["arranque"]),
        "-t", prueba["duracion"],
        "--csv", os.path.join(RESULTADOS, prueba["id"]),
        "--csv-full-history",
        "--only-summary",
    ]

    inicio = time.time()
    resultado = subprocess.run(comando, cwd=CARPETA)
    print("  terminada en {:.0f} s (codigo {})".format(
        time.time() - inicio, resultado.returncode))

    if pausa:
        print("  pausa de {} s para que el servicio se recupere ...".format(pausa))
        time.sleep(pausa)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solo", help="un endpoint: E1 ... E5")
    parser.add_argument("--escenario", choices=list(ESCENARIOS),
                        help="un escenario: normal, pico o estres")
    parser.add_argument("--prueba", help="una sola prueba, por ejemplo E3-estres")
    parser.add_argument("--pausa", type=int, default=20,
                        help="segundos de pausa entre pruebas")
    args = parser.parse_args()

    os.makedirs(RESULTADOS, exist_ok=True)

    pruebas = listado_de_pruebas()
    if args.prueba:
        pruebas = [p for p in pruebas if p["id"] == args.prueba]
    if args.solo:
        pruebas = [p for p in pruebas if p["endpoint"] == args.solo.upper()]
    if args.escenario:
        pruebas = [p for p in pruebas if p["escenario"] == args.escenario]

    if not pruebas:
        print("Ninguna prueba coincide con lo que pediste.")
        return 1

    # Aviso temprano: sin datos sembrados los numeros no sirven.
    if not os.path.exists(os.path.join(CARPETA, "datos_sembrados.json")):
        print("\nFALTA sembrar los datos. Corre primero:")
        print("    python datos_de_prueba.py\n")
        return 1

    minutos = sum(int(p["duracion"].rstrip("m")) for p in pruebas)
    print("Se van a ejecutar {} pruebas (~{} minutos de medicion".format(
        len(pruebas), minutos), end="")
    print(" + {} minutos de pausas).".format(len(pruebas) * args.pausa // 60))

    for prueba in pruebas:
        correr_una(prueba, args.pausa if prueba is not pruebas[-1] else 0)

    print("\nTodas terminadas. Los resultados estan en resultados/")
    print("Ahora:  python resumen.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
