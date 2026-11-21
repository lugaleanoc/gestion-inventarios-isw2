# Plantilla base de servicio Flask + MySQL

Punto de partida para cualquier microservicio del proyecto. Trae lo común: puerto 8000, `GET /health`, errores `{error, detalle}`, listas `{datos, paginacion}`, lectura de los headers del Gateway (`X-Empresa-Id`, `X-Usuario-Id`, `X-Rol`), llamadas entre servicios con `X-Servicio-Origen`, capa de base de datos (MySQL en producción, SQLite en las pruebas), Dockerfile y pruebas.

## Cómo crear un servicio nuevo

1. Copiar la carpeta: `cp -r services/plantilla-base services/<servicio>` y borrar este README.
2. Cambiar el nombre `plantilla` por el del servicio en `app/config.py` (DB_HOST, DB_USER, DB_NAME, nombre del .db), en `app/__init__.py` (nombre en `/health`) y en `app/routes.py` (prefijo `/api/<servicio>`).
3. Reemplazar la tabla de ejemplo en `app/schema.py` (hay una versión MySQL y una SQLite) por las del servicio.
4. Escribir las rutas en `app/routes.py` usando `@requiere(<roles>, <orígenes>)`, por ejemplo `@requiere(TODOS, ("reportes",))`: los roles permitidos para usuarios y la lista de servicios que pueden llamar esa ruta (vacía si es solo para usuarios). Los roles ya están definidos en `app/auth.py` (`ADM`, `ADM_BOD`, `TODOS`).
5. Ajustar las pruebas y correrlas: `python -m unittest discover -s tests -t .`
6. Probar el contenedor: `docker build -t <servicio>-service .`

## Reglas del equipo que ya cumple

- Los servicios no validan el token: confían en los headers que pone el Gateway.
- Cada servicio tiene su base de datos `<servicio>_db` y nunca consulta la de otro.
- Las llamadas entre servicios usan `X-Servicio-Origen` y `X-Empresa-Id`. Cada ruta lista qué servicios puede llamarla; otro origen responde `403 SIN_PERMISO`. Sin `X-Empresa-Id` o `X-Rol`: `401 FALTAN_HEADERS`.
- Solo el Gateway se expone fuera de la red de Docker: en el compose, ningún otro servicio lleva `ports:`.
