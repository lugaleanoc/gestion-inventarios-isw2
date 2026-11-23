"""Lee los CSV de Locust en resultados/ e imprime una tabla en Markdown.

    python resumir.py

La tabla se copia en PLAN_PRUEBAS.md (seccion de resultados). La carpeta
resultados/ no se sube a GitHub (.gitignore); lo que queda es la tabla.
"""

import csv
import glob
import os

LIMITE_MS = 2000  # RNF06: consultas en menos de 2 segundos
CARPETA = os.path.dirname(os.path.abspath(__file__))

archivos = sorted(glob.glob(os.path.join(CARPETA, "resultados", "P*_stats.csv")))
if not archivos:
    raise SystemExit("No hay resultados todavia: corre primero  python ejecutar_pruebas.py")

print("| Prueba | Endpoint | Escenario | Peticiones | Req/s | Prom. (ms) | p95 (ms) | Max (ms) | Errores | Cumple RNF06 |")
print("|---|---|---|---|---|---|---|---|---|---|")

for ruta in archivos:
    # Nombre del archivo: P07_E3RegistrarVenta_normal_stats.csv
    prueba, clase, escenario = os.path.basename(ruta).replace("_stats.csv", "").split("_")
    with open(ruta, encoding="utf-8") as archivo:
        fila = next(f for f in csv.DictReader(archivo) if f["Name"] == "Aggregated")

    peticiones = int(fila["Request Count"])
    errores = int(fila["Failure Count"])
    p95 = float(fila["95%"] or 0)
    tasa_error = 100.0 * errores / peticiones if peticiones else 0
    # Criterio de exito: p95 menor a 2 s y menos de 1 % de errores.
    cumple = "Sí" if peticiones and p95 < LIMITE_MS and tasa_error < 1 else "No"

    print("| {} | {} | {} | {} | {:.1f} | {:.0f} | {:.0f} | {:.0f} | {:.1f}% | {} |".format(
        prueba, clase[:2], escenario, peticiones, float(fila["Requests/s"]),
        float(fila["Average Response Time"]), p95, float(fila["Max Response Time"]),
        tasa_error, cumple))
