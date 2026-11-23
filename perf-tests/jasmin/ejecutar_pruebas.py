"""Corre las pruebas de rendimiento con Locust (sin interfaz) y muestra la tabla de resultados.

Esta escrito en Python (no en .sh) para que funcione igual en Windows, Mac y Linux.

    python ejecutar_pruebas.py                     # las 15 pruebas, 1 minuto cada una (~15 min)
    python ejecutar_pruebas.py E1 E3               # solo algunos endpoints
    python ejecutar_pruebas.py --duracion 20s      # pruebas mas cortas
    python ejecutar_pruebas.py E3 --duracion 30s   # se pueden combinar

Antes hay que tener los servicios arriba y haber corrido  python datos_prueba.py.

Cada prueba guarda sus CSV en resultados/ con el nombre
P07_E3RegistrarVenta_normal_stats.csv. Al final se ejecuta resumir.py, que
imprime la tabla para PLAN_PRUEBAS.md.
"""

import argparse
import os
import subprocess
import sys

import requests

CARPETA = os.path.dirname(os.path.abspath(__file__))

# Orden de los endpoints = orden de las pruebas (P01-P03 son E1, P04-P06 son E2, ...).
# E3 va antes de E4 y E5 para que, cuando se consulten el resumen y el balance, ya haya ventas.
ENDPOINTS = [
    "E1ConsultarStockMinimo",
    "E2DefinirStockMinimo",
    "E3RegistrarVenta",
    "E4ResumenVentas",
    "E5BalanceDiario",
]

# Escenario: (nombre, usuarios simultaneos, usuarios nuevos por segundo)
ESCENARIOS = [
    ("normal", 20, 5),
    ("pico", 100, 25),
    ("estres", 300, 50),
]

SERVICIOS = {
    "Configuracion": os.getenv("CONFIGURACION_URL", "http://localhost:8003"),
    "Ventas": os.getenv("VENTAS_URL", "http://localhost:8004"),
    "Balance Diario": os.getenv("BALANCE_URL", "http://localhost:8005"),
}


def servicios_arriba():
    """Revisa /health de los tres servicios antes de empezar."""
    todo_bien = True
    for nombre, url in SERVICIOS.items():
        try:
            ok = requests.get(url + "/health", timeout=3).status_code == 200
        except requests.RequestException:
            ok = False
        print("  {:<15} {:<25} {}".format(nombre, url, "OK" if ok else "NO RESPONDE"))
        todo_bien = todo_bien and ok
    return todo_bien


def main():
    parser = argparse.ArgumentParser(description="Pruebas de rendimiento (15 = 5 endpoints x 3 escenarios)")
    parser.add_argument("endpoints", nargs="*", help="Prefijos de los endpoints a correr, por ejemplo E1 E3")
    parser.add_argument("--duracion", default=os.getenv("DURACION", "1m"),
                        help="Duracion de cada prueba (por ejemplo 20s o 1m). Por defecto 1m")
    args = parser.parse_args()

    print("Revisando los servicios...")
    if not servicios_arriba():
        sys.exit("\nLevanta los servicios con:\n"
                 "  docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build")
    if not os.path.exists(os.path.join(CARPETA, "datos_prueba.json")):
        sys.exit("\nFalta datos_prueba.json: corre primero  python datos_prueba.py")

    os.makedirs(os.path.join(CARPETA, "resultados"), exist_ok=True)

    numero = 0
    for clase in ENDPOINTS:
        for escenario, usuarios, por_segundo in ESCENARIOS:
            numero += 1
            if args.endpoints and not any(clase.startswith(e) for e in args.endpoints):
                continue
            prueba = "P{:02d}".format(numero)
            print("\n=== {} {} {} ({} usuarios, {}) ===".format(
                prueba, clase, escenario, usuarios, args.duracion), flush=True)
            # sys.executable -m locust: usa el mismo Python que corre este
            # script, asi no importa si "locust" esta en el PATH (Windows).
            subprocess.run([
                sys.executable, "-m", "locust",
                "-f", os.path.join(CARPETA, "locustfile.py"), clase,
                "--headless",
                "--users", str(usuarios),
                "--spawn-rate", str(por_segundo),
                "--run-time", args.duracion,
                "--csv", os.path.join(CARPETA, "resultados", "{}_{}_{}".format(prueba, clase, escenario)),
                "--only-summary",
            ], cwd=CARPETA)  # si una prueba tiene errores, igual se sigue con la siguiente

    print("\n=== Resumen (copiar en PLAN_PRUEBAS.md) ===\n")
    subprocess.run([sys.executable, os.path.join(CARPETA, "resumir.py")], cwd=CARPETA)


if __name__ == "__main__":
    main()
