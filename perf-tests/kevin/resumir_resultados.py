import csv
import glob
import os
import sys

from escenarios import PRUEBAS, TIPOS

CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resultados")
LIMITE_P95_MS = 2000
LIMITE_ERROR = 0.01

ENCABEZADO = [
    "Prueba", "Endpoint", "Escenario", "Usuarios", "Peticiones", "Error (%)",
    "Promedio (ms)", "Mediana (ms)", "p95 (ms)", "Peticiones/s", "Cumple",
]


def leer():
    filas = []
    for ruta in sorted(glob.glob(os.path.join(CARPETA, "t*_stats.csv"))):
        clave = os.path.basename(ruta).split("_")[0].lower()
        if clave not in PRUEBAS:
            continue
        with open(ruta, newline="", encoding="utf-8") as archivo:
            for fila in csv.DictReader(archivo):
                if fila["Name"] != "Aggregated":
                    continue
                total = int(fila["Request Count"])
                fallas = int(fila["Failure Count"])
                p95 = float(fila["95%"])
                error = fallas / total if total else 1.0
                tipo = TIPOS[PRUEBAS[clave]["escenario"]]
                filas.append([
                    clave.upper(),
                    f'{PRUEBAS[clave]["metodo"]} {PRUEBAS[clave]["endpoint"]}',
                    tipo["nombre"],
                    tipo["usuarios"],
                    total,
                    round(error * 100, 2),
                    round(float(fila["Average Response Time"])),
                    round(float(fila["Median Response Time"])),
                    round(p95),
                    round(float(fila["Requests/s"]), 1),
                    "Sí" if p95 < LIMITE_P95_MS and error < LIMITE_ERROR else "No",
                ])
    return filas


def latex(texto):
    return texto.replace("\\", "\\textbackslash{}").replace("_", "\\_").replace("%", "\\%").replace("&", "\\&").replace("{", "\\{").replace("}", "\\}")


def main():
    filas = leer()
    if "--latex" in sys.argv:
        print("\\begin{longtable}{|l|p{4.2cm}|l|r|r|r|r|r|r|r|l|}")
        print("\\hline")
        print(" & ".join(f"\\textbf{{{latex(c)}}}" for c in ENCABEZADO) + " \\\\ \\hline")
        for fila in filas:
            print(" & ".join(latex(str(c)) for c in fila) + " \\\\ \\hline")
        print("\\end{longtable}")
        return
    print("| " + " | ".join(ENCABEZADO) + " |")
    print("|" + "---|" * len(ENCABEZADO))
    for fila in filas:
        print("| " + " | ".join(str(c) for c in fila) + " |")
    if not filas:
        print("| (sin resultados todavía) |" + " |" * (len(ENCABEZADO) - 1))
    print(f"\nCumple = p95 menor a {LIMITE_P95_MS} ms y menos de {LIMITE_ERROR * 100:.0f}% de errores.")


if __name__ == "__main__":
    main()
