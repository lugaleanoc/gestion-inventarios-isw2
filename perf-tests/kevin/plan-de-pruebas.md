# Plan de pruebas de rendimiento — Kevvin Hernandez (Gateway, Proveedores y Reportes)

Herramienta: Locust. Métricas: tiempo de respuesta (promedio, p95 y máximo), throughput (req/s) y tasa de error. Criterio de éxito (RNF06): p95 menor a 2000 ms y errores menores al 1 %.

| Escenario | Usuarios simultáneos | Usuarios nuevos/s | Representa |
|---|---|---|---|
| Normal | 20 | 5 | Un día común de la empresa |
| Pico | 100 | 25 | Hora de más ventas |
| Estrés | 300 | 50 | Buscar dónde empieza a fallar |

Cada usuario simulado espera entre 0,5 y 1,5 s entre peticiones. Cada prueba dura 1 minuto.

## Pruebas de Kevvin Hernandez (Gateway, Proveedores y Reportes)

| Prueba | Endpoint | Escenario |
|---|---|---|
| P01 | POST /api/auth/login | Normal (20 usuarios) |
| P02 | POST /api/auth/login | Pico (100 usuarios) |
| P03 | POST /api/auth/login | Estrés (300 usuarios) |
| P04 | GET /api/proveedores/por-producto/{id} | Normal (20 usuarios) |
| P05 | GET /api/proveedores/por-producto/{id} | Pico (100 usuarios) |
| P06 | GET /api/proveedores/por-producto/{id} | Estrés (300 usuarios) |
| P07 | POST /api/proveedores | Normal (20 usuarios) |
| P08 | POST /api/proveedores | Pico (100 usuarios) |
| P09 | POST /api/proveedores | Estrés (300 usuarios) |
| P10 | GET /api/reportes/dashboard | Normal (20 usuarios) |
| P11 | GET /api/reportes/dashboard | Pico (100 usuarios) |
| P12 | GET /api/reportes/dashboard | Estrés (300 usuarios) |
| P13 | GET /api/reportes/ventas-por-canal?refrescar=true | Normal (20 usuarios) |
| P14 | GET /api/reportes/ventas-por-canal?refrescar=true | Pico (100 usuarios) |
| P15 | GET /api/reportes/ventas-por-canal?refrescar=true | Estrés (300 usuarios) |

Por qué estos 5 endpoints: el inicio de sesión es la puerta de entrada de todo el sistema (Gateway); la consulta de proveedores por producto es la que más usan Reposición e Inventario; la creación de proveedores es la escritura de Proveedores; el dashboard es la consulta más pedida de Reportes; y el reporte con `refrescar=true` obliga a Reportes a consultar a Ventas sin caché.

## Modos de ejecución

- **Vía Gateway** (por defecto): el usuario simulado inicia sesión y manda el token. Mide el recorrido completo.
- **Directo** (`--modo directo`, pruebas P04 a P15): se llama al servicio con los headers `X-Empresa-Id`, `X-Usuario-Id` y `X-Rol`, sin login. Como en Docker solo el Gateway publica puerto, se abren 8002 y 8003 solo durante la prueba con `docker-compose.pruebas.yml`.

## Cómo ejecutarlas

1. Levantar el sistema con Docker Compose y confirmar que el Gateway responde en `http://localhost:8080/health`.
2. `pip install locust`
3. Desde esta carpeta:
   - Todas, vía Gateway: `python run_pruebas.py`
   - Algunas: `python run_pruebas.py p01 p05 p11`
   - Solo el servicio, sin login (P04–P15): primero `docker compose -f docker-compose.yml -f perf-tests/kevin/docker-compose.pruebas.yml up -d` desde la raíz del repositorio y luego `python run_pruebas.py p04 p05 p06 p07 p08 p09 p10 p11 p12 p13 p14 p15 --modo directo`
   - Ensayo rápido: añadir `--duracion 10s`
4. `python resumir_resultados.py` imprime la tabla de resultados; con `--latex` sale lista para Overleaf.

Cada prueba deja en `resultados/` un CSV (`pNN_stats.csv`) y un HTML con las gráficas (`pNN.html`). Mínimo 8 pruebas ejecutadas; los resultados del informe son los de las ejecuciones reales.

## Notas

- La primera vez, el usuario simulado registra la empresa de pruebas `locust@jak.co` (cambiable con `JAK_CORREO`, `JAK_CONTRASENA` y `JAK_NIT`). En modo directo la empresa es la 1 (`JAK_EMPRESA_ID`).
- Con direcciones distintas: `URL_PROVEEDORES` y `URL_REPORTES`.
- P07 a P09 crean un proveedor en cada petición: después de correrlas conviene reiniciar la base de pruebas.
