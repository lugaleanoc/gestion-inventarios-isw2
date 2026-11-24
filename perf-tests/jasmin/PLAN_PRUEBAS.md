# Pruebas de rendimiento — Jasmin

Requisitos: RNF11 (15 pruebas por integrante) y RNF06 (consultas en menos de
2 s bajo una carga concurrente definida por el equipo). Herramienta: Locust.

Servicios probados: Configuración, Ventas y Balance Diario (los tres de Jasmin).

## 1. Diseño: 5 endpoints × 3 escenarios = 15 pruebas

### Endpoints

| Id | Endpoint | Microservicio | Quién lo llama | Por qué se eligió |
|----|----------|---------------|----------------|-------------------|
| E1 | `GET /api/configuracion/stock-minimo/{id}` | Configuración | Inventario (interna) | La consulta más frecuente: Inventario la hace en cada movimiento de stock. Los productos 1-10 tienen valor propio y los 11-20 usan el de la empresa, así se prueban los dos caminos |
| E2 | `PUT /api/configuracion/stock-minimo/{id}` | Configuración | Administrador | Escritura en MySQL: se compara con la lectura E1 |
| E3 | `POST /api/ventas` | Ventas → Inventario (mock) → Balance | Vendedor | La operación más completa: guarda la venta, descuenta stock y registra el ingreso en Balance. Mide la comunicación REST entre servicios. **Solo cuenta como éxito si la venta queda con `estadoBalance = "registrado"`** |
| E4 | `GET /api/ventas/resumen` | Ventas | Reportes (interna) | Consulta agregada (`SUM … GROUP BY`) sobre todas las ventas del mes; se vuelve más pesada a medida que E3 crea ventas |
| E5 | `GET /api/balance/diario` | Balance Diario | Vendedor | Suma todos los movimientos del día por medio de pago |

### Escenarios

| Escenario | Usuarios simultáneos | Usuarios nuevos/s | Representa |
|-----------|----------------------|-------------------|------------|
| Normal    | 20  | 5  | Un día común de la empresa |
| Pico      | 100 | 25 | Hora de más ventas |
| Estrés    | 300 | 50 | Buscar dónde empieza a fallar |

Cada usuario simulado espera entre 0,5 y 1,5 s entre peticiones. Duración:
1 minuto por prueba.

| Prueba | E1 | E2 | E3 | E4 | E5 |
|--------|----|----|----|----|----|
| Normal | P01 | P04 | P07 | P10 | P13 |
| Pico   | P02 | P05 | P08 | P11 | P14 |
| Estrés | P03 | P06 | P09 | P12 | P15 |

E3 corre antes que E4 y E5 a propósito: así, cuando se consultan el resumen y
el balance, ya hay ventas y movimientos que sumar.

### Métricas

- **Tiempo de respuesta:** promedio, percentil 95 (p95) y máximo, en ms.
- **Throughput:** peticiones por segundo (req/s).
- **Tasa de error:** % de peticiones fallidas (5xx, sin respuesta o, en E3,
  ventas que no quedaron `registrado`).

**Criterio de éxito (RNF06):** p95 < 2000 ms y errores < 1 %.

Se usa el p95 y no el promedio porque el promedio esconde las peticiones
lentas. Un p95 de 70 ms quiere decir que el 95 % de las peticiones tardó
70 ms o menos.

### Condiciones

- Sin API Gateway, para medir una pieza a la vez: Locust llama directo a cada servicio
  y envía en cada petición los headers que pondría el Gateway
  (`X-Empresa-Id`, `X-Usuario-Id`, `X-Rol`) o los de una llamada interna
  (`X-Servicio-Origen`, `X-Empresa-Id`).
- Puertos de `docker-compose.pruebas.yml`: Configuración 8003, Ventas 8004,
  Balance 8005.
- Inventario en modo simulado (`USAR_MOCK_INVENTARIO=true`): bodega 1 y precio
  fijo. Así E3 mide Ventas y Balance sin depender de otro servicio.
- Cada servicio corre con gunicorn y 2 workers, con un solo MySQL compartido
  (una base por servicio).

## 2. Cómo ejecutarlas

Los comandos son iguales en Windows (PowerShell o CMD), Mac y Linux.

```bash
# 1. Levantar los servicios con los puertos de prueba (desde la raíz del repositorio).
#    "down -v" borra los datos anteriores para empezar limpio.
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml down -v
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build

# 2. Instalar Locust y cargar los datos de prueba (una vez)
cd perf-tests/jasmin
pip install -r requirements.txt
python datos_prueba.py

# 3. Correr las 15 pruebas (~15 min) y ver la tabla
python ejecutar_pruebas.py

# Solo algunas, o más cortas:
python ejecutar_pruebas.py E3 --duracion 20s

# Una sola, con la interfaz web de Locust (http://localhost:8089):
python -m locust -f locustfile.py E3RegistrarVenta
```

`datos_prueba.py` crea la empresa (como lo haría el Gateway), el local
"Sede Centro" (o reutiliza el que exista) y los stocks mínimos, y guarda los
ids en `datos_prueba.json`, que `locustfile.py` lee. Si Inventario no está
corriendo, se salta su parte.

Los CSV de cada prueba quedan en `resultados/` y `resumir.py` arma la tabla
de la sección 3.

## 3. Resultados

Fecha: 23 de noviembre de 2026 · Equipo: AMD Ryzen 7 7730U (16 hilos), 14 GB de RAM · Duración: 1 min por prueba · Sin API Gateway · Inventario simulado.

| Prueba | Endpoint | Escenario | Peticiones | Req/s | Prom. (ms) | p95 (ms) | Max (ms) | Errores | Cumple RNF06 |
|---|---|---|---|---|---|---|---|---|---|
| P01 | E1 | normal | 1156 | 19.6 | 7 | 9 | 17 | 0.0% | Sí |
| P02 | E1 | pico | 5774 | 97.8 | 7 | 10 | 61 | 0.0% | Sí |
| P03 | E1 | estres | 16899 | 286.0 | 11 | 19 | 162 | 0.0% | Sí |
| P04 | E2 | normal | 1146 | 19.4 | 15 | 18 | 51 | 0.0% | Sí |
| P05 | E2 | pico | 5735 | 97.1 | 19 | 32 | 170 | 0.0% | Sí |
| P06 | E2 | estres | 10807 | 182.9 | 576 | 730 | 896 | 0.0% | Sí |
| P07 | E3 | normal | 1103 | 18.7 | 56 | 89 | 179 | 0.0% | Sí |
| P08 | E3 | pico | 2459 | 41.6 | 1346 | 1500 | 1760 | 0.0% | Sí |
| P09 | E3 | estres | 1521 | 25.7 | 8353 | 16000 | 18412 | 0.0% | No |
| P10 | E4 | normal | 1069 | 18.1 | 94 | 34 | 5041 | 0.0% | Sí |
| P11 | E4 | pico | 5483 | 92.8 | 64 | 180 | 332 | 0.0% | Sí |
| P12 | E4 | estres | 8562 | 144.9 | 973 | 1300 | 1371 | 0.0% | Sí |
| P13 | E5 | normal | 1086 | 18.4 | 69 | 110 | 228 | 0.0% | Sí |
| P14 | E5 | pico | 3824 | 64.7 | 503 | 840 | 1726 | 0.0% | Sí |
| P15 | E5 | estres | 3810 | 64.5 | 3344 | 3900 | 4047 | 0.0% | No |

Los CSV de cada prueba están en `resultados/` (`PNN_..._stats.csv` y `_stats_history.csv`).

### Análisis

- **13 de las 15 pruebas cumplen el RNF06, y las 15 terminaron con 0 % de errores**: ninguna petición se perdió, incluso cuando el servicio se saturó.
- **E1 (lectura de configuración) escala casi perfecto:** al pasar de 20 a 300 usuarios el throughput subió de 19,6 a 286 req/s y el p95 solo pasó de 9 a 19 ms.
- **E2 (escritura) cumple, pero muestra el límite de la base:** con 300 usuarios el throughput se quedó en 183 req/s (en vez de ~290) y el p95 subió a 730 ms, porque cada petición escribe en MySQL.
- **E3 (registrar venta) es el cuello de botella.** Cada venta guarda en la base de Ventas y espera la respuesta de Balance por REST. Con 2 workers síncronos de gunicorn solo se atienden 2 ventas a la vez, así que el throughput no pasa de ~42 req/s. En pico el p95 llegó a 1.500 ms (cumple, pero cerca del límite) y en estrés la fila creció hasta un p95 de 16 s: no cumple. Aun así, todas las ventas quedaron registradas.
- **E4 (resumen de ventas) cumple en los tres escenarios** (p95 de 1.300 ms en estrés). El máximo de 5 s en P10 fue la primera petición, con el servicio recién iniciado; por eso en esa prueba el promedio quedó por encima del p95.
- **E5 (balance diario) se satura desde el escenario pico:** se queda en ~65 req/s con 100 y con 300 usuarios, y en estrés el p95 llega a 3,9 s, por lo que no cumple. La consulta suma todos los movimientos del día, y E3 acababa de crear unas 9.700 ventas, así que cada petición agrupa unas 9.700 filas.

### Optimizaciones propuestas (comparación antes/después en la Entrega 4)

- Agregar hilos a gunicorn (--threads) en Ventas y Balance, para que un worker que espera la respuesta de otro servicio no bloquee las demás peticiones.
- En Balance Diario, guardar los totales del día por local y medio de pago a medida que llegan los movimientos, en lugar de sumarlos en cada consulta, o usar una caché corta.
- Repetir E3 con el Inventario real y a través del Gateway, para medir el recorrido completo de una venta.
