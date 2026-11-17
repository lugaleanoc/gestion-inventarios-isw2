"""Punto de entrada del servicio de Reposicion.

Gunicorn busca aqui la variable `app`:  gunicorn wsgi:app
"""

from app import crear_app

app = crear_app()

if __name__ == "__main__":
    import os

    app.run(host="0.0.0.0", port=int(os.getenv("PUERTO", 8000)), debug=True)
