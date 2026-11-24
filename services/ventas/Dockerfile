
FROM python:3.12-slim

# Carpeta de trabajo dentro del contenedor.
WORKDIR /app

# Variables que afectan a Python dentro del contenedor:
# - PYTHONDONTWRITEBYTECODE: no genera archivos .pyc, que no sirven aqui.
# - PYTHONUNBUFFERED: hace que los logs salgan al instante y no se queden
#   en memoria, para poder verlos con docker logs (RNF10).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Se copian primero SOLO las dependencias y se instalan. Docker guarda cada
# paso en cache: mientras requirements.txt no cambie, no vuelve a instalar
# nada aunque cambie el codigo. Eso hace que reconstruir tarde segundos.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ahora si, el codigo de la aplicacion.
COPY . .

# El contenedor no corre como root: si alguien lograra entrar, tendria los
# permisos minimos. Es una buena practica basica de seguridad.
RUN useradd --create-home aplicacion && chown -R aplicacion:aplicacion /app
USER aplicacion

# Puerto acordado por el equipo para los ocho servicios.
EXPOSE 8000

# Docker usa /health para saber si el contenedor esta sano.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

# Comando con el que arranca el contenedor. Primero init_db.py crea las
# tablas en un solo proceso; si termina bien (&&), arranca gunicorn.
#   -w 2            dos procesos atendiendo peticiones
#   -b 0.0.0.0:8000 escucha en todas las interfaces, no solo dentro del contenedor
#   wsgi:app        el archivo wsgi.py y su variable app
CMD ["sh", "-c", "python init_db.py && exec gunicorn -w 2 -b 0.0.0.0:8000 --access-logfile - wsgi:app"]
