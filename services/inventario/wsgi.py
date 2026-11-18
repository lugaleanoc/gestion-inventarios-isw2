"""Punto de entrada del servicio.

Gunicorn (el servidor que corre dentro del contenedor) busca en este archivo
una variable llamada `app`. Por eso el Dockerfile dice:  gunicorn wsgi:app
"""

from app import crear_app

# crear_app() es una "fabrica": construye la aplicacion Flask ya configurada.
# Se usa una fabrica en vez de crear la app directamente para poder crear
# aplicaciones distintas en las pruebas (por ejemplo, con otra base de datos).
app = crear_app()

if __name__ == "__main__":
    # Esta rama solo se ejecuta si corremos  python wsgi.py  (desarrollo local).
    # En el contenedor nunca pasa por aqui: alli manda gunicorn.
    import os

    app.run(host="0.0.0.0", port=int(os.getenv("PUERTO", 8000)), debug=True)
