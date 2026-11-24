"""Lee los CSV que dejo Locust y arma la tabla para el informe.

    python resumen.py

Produce resultados/resumen.md con una tabla por escenario y el veredicto
de cada prueba frente a los criterios de aceptacion.

Criterios (del README de esta carpeta):
  - RNF06: las consultas responden en menos de 2 segundos (p95).
  - La tasa de error se mantiene por debajo del 1 %.
En la prueba de estres NO se exige cumplirlos: ahi el objetivo es
justamente encontrar el punto donde el servicio deja de cumplir.
"""

import csv
import glob
import os

CARPETA = os.path.dirname(os.path.abspath(__file__))
RESULTADOS = os.path.join(CARPETA, "resultados")

LIMITE_MS = 2000      # RNF06
LIMITE_ERROR = 1.0    # por ciento

NOMBRES = {
    "E1": "Consulta de stock de un producto (Inventario, lectura)",
    "E2": "Busqueda de productos por texto (Inventario, lectura)",
    "E3": "Descuento de stock por venta (Inventario, escritura)",
    "E4": "Resumen de reposicion (Reposicion, lectura)",
    "E5": "Solicitud automatica (Reposicion, escritura)",
}
ESCENARIOS = {"normal": "Carga normal (20 usuarios)",
              "pico": "Carga pico (100 usuarios)",
              "estres": "Estres (300 usuarios)"}


def numero(fila, *nombres):
    """Lee una columna del CSV probando varios nombres posibles.

    Locust ha cambiado el nombre de algunas columnas entre versiones, por
    eso se prueban varias en vez de una sola.
    """
    for nombre in nombres:
        if nombre in fila and fila[nombre] not in ("", "N/A"):
            try:
                return float(fila[nombre])
            except ValueError:
                pass
    return 0.0


def leer(archivo):
    """Saca del CSV la fila 'Aggregated', que es el total de la prueba."""
    with open(archivo, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            if fila.get("Name") == "Aggregated" or fila.get("Type") == "":
                peticiones = numero(fila, "Request Count", "Requests")
                fallos = numero(fila, "Failure Count", "Failures")
                return {
                    "peticiones": int(peticiones),
                    "fallos": int(fallos),
                    "error_pct": (fallos / peticiones * 100) if peticiones else 0.0,
                    "throughput": numero(fila, "Requests/s"),
                    "media": numero(fila, "Average Response Time"),
                    "p50": numero(fila, "50%", "Median Response Time"),
                    "p95": numero(fila, "95%"),
                    "p99": numero(fila, "99%"),
                    "maximo": numero(fila, "Max Response Time"),
                }
    return None


def veredicto(datos, escenario):
    """Decide si la prueba paso, con el criterio que corresponde."""
    if escenario == "estres":
        # En estres no se exige cumplir: se describe lo que paso.
        if datos["error_pct"] >= LIMITE_ERROR or datos["p95"] > LIMITE_MS:
            return "Limite encontrado"
        return "Aguanto"
    problemas = []
    if datos["p95"] > LIMITE_MS:
        problemas.append("p95 sobre 2 s")
    if datos["error_pct"] > LIMITE_ERROR:
        problemas.append("errores sobre 1 %")
    return "CUMPLE" if not problemas else "NO cumple: " + " y ".join(problemas)


def main():
    archivos = sorted(glob.glob(os.path.join(RESULTADOS, "*_stats.csv")))
    if not archivos:
        print("No hay resultados todavia. Corre primero:  python ejecutar.py")
        return 1

    filas = {}
    for archivo in archivos:
        identificador = os.path.basename(archivo).replace("_stats.csv", "")
        datos = leer(archivo)
        if datos and datos["peticiones"]:
            filas[identificador] = datos

    lineas = ["# Resultados de las pruebas de rendimiento", "",
              "Pruebas: {} de 15 ejecutadas.".format(len(filas)), "",
              "Metricas: **p95** es el tiempo que no superan el 95 % de las",
              "peticiones (mejor medida que el promedio, porque el promedio",
              "esconde los casos lentos). **Throughput** son peticiones",
              "atendidas por segundo. **Error** es el porcentaje que fallo.", ""]

    for escenario, titulo in ESCENARIOS.items():
        delescenario = {k: v for k, v in filas.items() if k.endswith("-" + escenario)}
        if not delescenario:
            continue
        lineas += ["## {}".format(titulo), "",
                   "| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |",
                   "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |"]
        for identificador in sorted(delescenario):
            d = delescenario[identificador]
            endpoint = identificador.split("-")[0]
            lineas.append("| {} | {} | {} | {:.1f}/s | {:.0f} ms | {:.0f} ms | {:.0f} ms | {:.2f} % | {} |".format(
                identificador, NOMBRES.get(endpoint, endpoint), d["peticiones"],
                d["throughput"], d["p50"], d["p95"], d["p99"], d["error_pct"],
                veredicto(d, escenario)))
        lineas.append("")

    # Comparacion entre escenarios: es lo que muestra como se degrada.
    lineas += ["## Como se degrada cada endpoint", "",
               "| Endpoint | p95 normal | p95 pico | p95 estres | Error en estres |",
               "| --- | ---: | ---: | ---: | ---: |"]
    for endpoint in sorted(NOMBRES):
        normal = filas.get(endpoint + "-normal")
        pico = filas.get(endpoint + "-pico")
        estres = filas.get(endpoint + "-estres")
        if not (normal or pico or estres):
            continue
        def ms(d):
            return "{:.0f} ms".format(d["p95"]) if d else "-"
        lineas.append("| {} | {} | {} | {} | {} |".format(
            endpoint, ms(normal), ms(pico), ms(estres),
            "{:.2f} %".format(estres["error_pct"]) if estres else "-"))

    salida = os.path.join(RESULTADOS, "resumen.md")
    with open(salida, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas) + "\n")

    print("\n".join(lineas))
    print("\nGuardado en {}".format(salida))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
