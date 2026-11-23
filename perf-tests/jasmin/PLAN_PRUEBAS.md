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

- Sin API Gateway (todavía no existe): Locust llama directo a cada servicio
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

Los CSV de cada prueba quedan en `resultados/` (no se suben a GitHub) y
`resumir.py` arma la tabla de la sección 3.

## 3. Resultados

Fecha: ____ · Equipo: ____ (CPU / RAM) · Duración: 1 min por prueba ·
Sin API Gateway · Inventario simulado.

| Prueba | Endpoint | Escenario | Peticiones | Req/s | Prom. (ms) | p95 (ms) | Max (ms) | Errores | Cumple RNF06 |
|---|---|---|---|---|---|---|---|---|---|
| P01 | E1 | normal |  |  |  |  |  |  |  |
| P02 | E1 | pico |  |  |  |  |  |  |  |
| P03 | E1 | estres |  |  |  |  |  |  |  |
| P04 | E2 | normal |  |  |  |  |  |  |  |
| P05 | E2 | pico |  |  |  |  |  |  |  |
| P06 | E2 | estres |  |  |  |  |  |  |  |
| P07 | E3 | normal |  |  |  |  |  |  |  |
| P08 | E3 | pico |  |  |  |  |  |  |  |
| P09 | E3 | estres |  |  |  |  |  |  |  |
| P10 | E4 | normal |  |  |  |  |  |  |  |
| P11 | E4 | pico |  |  |  |  |  |  |  |
| P12 | E4 | estres |  |  |  |  |  |  |  |
| P13 | E5 | normal |  |  |  |  |  |  |  |
| P14 | E5 | pico |  |  |  |  |  |  |  |
| P15 | E5 | estres |  |  |  |  |  |  |  |

### Análisis

_(Completar con los resultados: qué endpoints escalan bien, cuál es el cuello
de botella, en qué escenario empieza a fallar y por qué.)_

### Optimizaciones propuestas (comparación antes/después)

_(Completar según el análisis. Ideas a evaluar: más workers de gunicorn,
índices en MySQL, repetir las pruebas a través del API Gateway.)_
