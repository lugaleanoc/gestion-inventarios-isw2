FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY init_db.py wsgi.py ./

RUN useradd --create-home aplicacion && chown -R aplicacion:aplicacion /srv
USER aplicacion

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=2).status == 200 else 1)"

CMD ["sh", "-c", "python init_db.py && exec gunicorn -b 0.0.0.0:8000 -w 2 --threads 4 --timeout 60 --access-logfile - wsgi:app"]
