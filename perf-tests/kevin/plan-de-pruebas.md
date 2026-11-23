# Plan de pruebas de rendimiento — Kevin (Gateway, Proveedores y Reportes)

Herramienta: Locust. Las pruebas T01–T06 entran siempre por el API Gateway. Las pruebas T07–T15 (Proveedores y Reportes) se pueden ejecutar de dos maneras:

- **Vía Gateway** (por defecto): el usuario virtual inicia sesión y manda el token. Mide el recorrido completo (Gateway + servicio).
- **Directo** (`--modo directo`): se llama al servicio enviando los headers `X-Empresa-Id`, `X-Usuario-Id` y `X-Rol`, sin login. Mide solo el servicio. Como en Docker únicamente el Gateway publica puerto, se abre el del servicio solo para la prueba con `docker-compose.pruebas.yml` (puertos 8002 y 8003).

## Escenarios

| Escenario | Usuarios simulados | Nuevos por segundo | Duración | Para qué |
|---|---|---|---|---|
| Carga normal | 20 | 5 | 30s | Uso habitual del sistema |
| Pico de carga | 100 | 20 | 30s | Muchos usuarios a la vez, como un cierre de caja o una promoción |
| Estrés | 200 | 40 | 60s | Más carga de la esperada, para ver dónde empieza a degradarse |

## Métricas y criterio

Se miden el tiempo de respuesta (promedio, mediana y percentil 95), el throughput (peticiones por segundo) y la tasa de error. Criterio de aceptación (RNF06): p95 menor a 2 segundos y menos de 1% de errores. En las pruebas de estrés el criterio también se reporta, pero el objetivo es ver el límite del sistema.

## Las 15 pruebas

| Prueba | Servicio | Endpoint | Escenario | Usuarios | Qué mide |
|---|---|---|---|---|---|
| T01 | Gateway | POST /api/auth/login | Estrés | 200 | Inicio de sesión (verificación de contraseña y emisión de JWT) |
| T02 | Gateway | POST /api/empresas/registro | Carga normal | 20 | Registro de empresa (llama a Configuración) |
| T03 | Gateway | POST /api/auth/token-tienda | Pico de carga | 100 | Emisión de token para una tienda web |
| T04 | Gateway | GET /api/usuarios | Carga normal | 20 | Listado paginado de usuarios |
| T05 | Gateway | POST /api/usuarios | Carga normal | 20 | Creación de usuarios |
| T06 | Gateway | GET /api/tiendas-web | Carga normal | 20 | Listado de tiendas web |
| T07 | Proveedores | GET /api/proveedores | Pico de carga | 100 | Listado con filtros y paginación |
| T08 | Proveedores | POST /api/proveedores | Carga normal | 20 | Creación de proveedores |
| T09 | Proveedores | GET /api/proveedores/{id} | Carga normal | 20 | Consulta de un proveedor |
| T10 | Proveedores | PUT /api/proveedores/{id} | Carga normal | 20 | Actualización de un proveedor |
| T11 | Proveedores | POST /api/proveedores/{id}/productos | Carga normal | 20 | Asociación de productos a un proveedor |
| T12 | Proveedores | GET /api/proveedores/por-producto/{id} | Pico de carga | 100 | Consulta que usan Reposición e Inventario |
| T13 | Reportes | GET /api/reportes/dashboard | Pico de carga | 100 | Dashboard respondido desde la caché |
| T14 | Reportes | GET /api/reportes/ventas-por-canal?refrescar=true | Estrés | 200 | Reporte sin caché, consultando a Ventas |
| T15 | Mixto | GET proveedores + reportes/inventario + reportes/dashboard | Carga normal | 20 | Recorrido combinado de un usuario |

## Cómo ejecutarlas

1. Levantar el sistema con Docker Compose y confirmar que el Gateway responde: `curl localhost:8080/health`.
2. Instalar Locust: `pip install locust`.
3. Desde esta carpeta:
   - Todas, vía Gateway: `python run_pruebas.py`
   - Algunas: `python run_pruebas.py t01 t07 t13`
   - Solo el servicio, sin login (T07–T15): primero `docker compose -f docker-compose.yml -f perf-tests/kevin/docker-compose.pruebas.yml up -d` desde la raíz del repo y luego `python run_pruebas.py t07 t08 t09 t10 t11 t12 t13 t14 t15 --modo directo`
   - Ensayo rápido: añadir `--duracion 10s`
4. `python resumir_resultados.py` imprime la tabla de resultados (Markdown); con `--latex` sale lista para pegar en Overleaf.

Cada prueba deja en `resultados/` un CSV (`tNN_stats.csv`, `tNN_failures.csv`, `tNN_stats_history.csv`) y un HTML con las gráficas (`tNN.html`). Los requisitos son 15 pruebas definidas y mínimo 8 ejecutadas; los resultados que van al informe son los que arrojen las ejecuciones reales.

## Notas

- La primera vez, el usuario virtual registra la empresa de pruebas `locust@jak.co` (cambiable con `JAK_CORREO`, `JAK_CONTRASENA` y `JAK_NIT`). En modo directo la empresa es la 1 (`JAK_EMPRESA_ID`).
- Con direcciones distintas: `URL_PROVEEDORES` y `URL_REPORTES` (por defecto `http://localhost:8002` y `http://localhost:8003`).
- T02, T05 y T08 crean datos nuevos en cada petición: después de correrlas conviene reiniciar las bases de datos de prueba.
- Cada usuario virtual crea al iniciar un proveedor propio (y una tienda web si la prueba la necesita).
