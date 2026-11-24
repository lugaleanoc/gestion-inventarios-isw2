# API Gateway (gateway-service)

Flask + MySQL, puerto 8000, base de datos `gateway_db`. Único punto de entrada: valida el token JWT, pone los headers de identidad y reenvía a cada servicio.

## Qué hace

- Rutas propias: `/api/auth/*` (login, logout, recuperación, restablecimiento, cambio de contraseña, token de tienda web), `/api/usuarios`, `/api/tiendas-web` y `/api/empresas/registro`.
- Rutas reenviadas: `/api/{configuracion|inventario|proveedores|ventas|reposicion|balance|reportes}/...`. Es el único que valida el token. Borra cualquier `X-Rol`, `X-Empresa-Id`, `X-Usuario-Id`, `X-Servicio-Origen` y `Authorization` que traiga el cliente, agrega `X-Empresa-Id`, `X-Usuario-Id` y `X-Rol` de la sesión, y no reenvía el token.
- Rutas internas bloqueadas con `403 SIN_PERMISO`: `POST /api/inventario/stock/descuentos`, `POST /api/inventario/stock/entradas`, `POST /api/reposicion/solicitudes/automaticas`, `POST /api/balance/movimientos/ventas`, `POST /api/configuracion/empresas`.
- Si un servicio no responde: `503 SERVICIO_NO_DISPONIBLE`.

## Probar sin Docker

    cd services/gateway
    python -m unittest discover -s tests -t .

## Con Docker Compose

Pegar `docker-compose.snippet.yml` dentro de `services:` y agregar el volumen `gateway_data:`. Es el único servicio que lleva `ports:` (8080); los demás solo se alcanzan desde la red interna de Docker.

    docker compose up --build gateway-service
    curl localhost:8080/health

## Variables de entorno

DB_HOST, DB_PORT, DB_NAME (gateway_db), DB_USER, DB_PASSWORD, JWT_SECRET, JWT_EXPIRA_MINUTOS (480), JWT_TIENDA_EXPIRA_MINUTOS (60), CODIGO_RECUPERACION_MINUTOS (15), EXPONER_CODIGO_RECUPERACION (false), TIMEOUT_CONEXION (3), TIMEOUT_LECTURA (15). Resiliencia: REINTENTOS (3), REINTENTO_ESPERA (0.2 s, se duplica en cada reintento), CIRCUITO_FALLAS (3), CIRCUITO_SEGUNDOS (5): tras 3 fallas seguidas el circuito de ese servicio se abre 5 s y responde 503 SERVICIO_NO_DISPONIBLE sin intentar. Un POST solo se reintenta si la conexión nunca se pudo abrir.
Direcciones de los servicios: CONFIGURACION_URL, INVENTARIO_URL, PROVEEDORES_URL, VENTAS_URL, REPOSICION_URL, BALANCE_URL, REPORTES_URL. Por defecto son `http://<nombre>-service:8000`; el de Balance Diario es `http://balance-service:8000`.

## Decisiones donde el contrato no decía todo

- Los roles se leen de la base de datos en cada petición, así que dar de baja a un usuario o cambiarle el rol aplica de inmediato aunque tenga un token vigente.
- Los correos son únicos en todo el sistema (el login se hace solo con el correo).
- Un administrador no puede darse de baja a sí mismo (409 USUARIO_PROPIO).
- Los usuarios solo pueden tener los roles administrador, vendedor y encargado_bodega. El rol tienda_web es solo para tokens de tienda.
- Contraseña válida: entre 8 y 128 caracteres, con al menos una letra y un número.
- El código de recuperación se escribe en el log del servicio. Con `EXPONER_CODIGO_RECUPERACION=true` (solo demo) también viene en la respuesta de `/auth/recuperacion`.
- Registro de empresa: llama a `POST /api/configuracion/empresas` solo con `X-Servicio-Origen: gateway` (todavía no existe empresa, así que no manda `X-Empresa-Id`). Respuesta 201: `{empresa, administrador}`.
- A los servicios, una tienda web les llega con `X-Rol: tienda_web` y `X-Usuario-Id` igual al id de la tienda.
