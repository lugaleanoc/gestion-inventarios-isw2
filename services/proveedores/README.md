# Proveedores (proveedores-service)

Flask + MySQL, puerto 8000, base de datos `proveedores_db`. Ruta base `/api/proveedores`, más `GET /health`.
No maneja tokens: lee la identidad de los headers que pone el Gateway.

## Cómo decide el acceso

- Llamada de un usuario (vía Gateway): headers `X-Empresa-Id`, `X-Usuario-Id`, `X-Rol`. Si falta `X-Empresa-Id` o `X-Rol`: `401 FALTAN_HEADERS`. Si el rol no puede hacer la operación: `403 SIN_PERMISO`.
- Llamada de otro servicio: `X-Servicio-Origen` y `X-Empresa-Id`. Solo `reposicion` e `inventario` pueden llamar las rutas GET (las que dicen "Todos / Interno" en el contrato). Cualquier otro origen, o cualquier origen en una ruta de escritura: `403 SIN_PERMISO`.
- Solo el Gateway está expuesto fuera de la red de Docker. Esto es seguro porque el Gateway borra el `X-Servicio-Origen` y los headers de identidad que mande un cliente.

## Probarlo

Sin Docker ni MySQL (SQLite):

    cd services/proveedores
    python -m unittest discover -s tests -t .

Con Docker Compose: pegar `docker-compose.snippet.yml` dentro de `services:` del `docker-compose.yml` y agregar el volumen `proveedores_data:`.
Este servicio no publica puerto. Se prueba por el Gateway (`http://localhost:8080/api/proveedores`, con token) o, para pruebas de carga directas, con `perf-tests/kevin/docker-compose.pruebas.yml`, que abre el 8002 solo mientras pruebas:

    docker compose -f docker-compose.yml -f perf-tests/kevin/docker-compose.pruebas.yml up -d
    curl localhost:8002/health
    curl -X POST localhost:8002/api/proveedores \
      -H "Content-Type: application/json" \
      -H "X-Empresa-Id: 1" -H "X-Usuario-Id: 1" -H "X-Rol: administrador" \
      -d '{"nombre":"Distribuidora Andina","nit":"900123456-7"}'

## Variables de entorno

DB_HOST (proveedores-db), DB_PORT (3306), DB_NAME (proveedores_db), DB_USER (proveedores), DB_PASSWORD (proveedores_pass).

## Decisiones donde el contrato no decía todo

- productoId y proveedorId son enteros.
- PUT reemplaza el proveedor completo: contacto y condiciones omitidos quedan en null.
- DELETE es baja lógica (activo=false). Es idempotente.
- Un producto tiene un solo proveedor principal por empresa. Si no se envía principal, queda en false (como dice el contrato); si se envía principal=true, los demás dejan de serlo.
- GET /por-producto/{productoId} devuelve solo proveedores y asociaciones activos, principal primero, con los campos del proveedor más principal y precioCompra. Si no hay ninguno, 404 PRODUCTO_SIN_PROVEEDORES.
- Asociar a un proveedor dado de baja devuelve 409 PROVEEDOR_INACTIVO. Volver a asociar un producto dado de baja lo reactiva.
- pagina empieza en 1, porPagina por defecto 20 y máximo 100 (si piden más, se usa 100).
