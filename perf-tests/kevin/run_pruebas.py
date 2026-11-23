import argparse
import os
import subprocess
import sys

from escenarios import PRUEBAS, TIPOS

CARPETA = os.path.dirname(os.path.abspath(__file__))


def main():
    parser = argparse.ArgumentParser(description="Ejecuta las pruebas de rendimiento de Kevin con Locust")
    parser.add_argument("pruebas", nargs="*", help="por ejemplo: t01 t07 t13 (por defecto, las 15)")
    parser.add_argument("--host", default=os.getenv("HOST", "http://localhost:8080"), help="URL del Gateway")
    parser.add_argument("--modo", choices=["gateway", "directo"], default=os.getenv("JAK_MODO", "gateway"))
    parser.add_argument("--duracion", default=None, help="reemplaza la duración de todos los escenarios, por ejemplo 10s")
    args = parser.parse_args()

    seleccion = [p.lower() for p in args.pruebas] or sorted(PRUEBAS)
    desconocidas = [p for p in seleccion if p not in PRUEBAS]
    if desconocidas:
        sys.exit(f"Pruebas desconocidas: {', '.join(desconocidas)}")

    os.makedirs(os.path.join(CARPETA, "resultados"), exist_ok=True)
    entorno = {**os.environ, "JAK_MODO": args.modo}
    for prueba in seleccion:
        tipo = TIPOS[PRUEBAS[prueba]["escenario"]]
        duracion = args.duracion or tipo["duracion"]
        print(f"\n=== {prueba.upper()} · {tipo['nombre']} · {tipo['usuarios']} usuarios · {duracion} ===", flush=True)
        subprocess.run(
            [
                sys.executable, "-m", "locust", "-f", "locustfile_kevin.py", "--headless",
                "--host", args.host, "-u", str(tipo["usuarios"]), "-r", str(tipo["rampa"]), "-t", duracion,
                "--tags", prueba, "--csv", f"resultados/{prueba}", "--html", f"resultados/{prueba}.html",
                "--only-summary",
            ],
            cwd=CARPETA,
            env=entorno,
        )
    subprocess.run([sys.executable, "resumir_resultados.py"], cwd=CARPETA)


if __name__ == "__main__":
    main()
