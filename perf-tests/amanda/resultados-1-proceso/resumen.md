# Resultados de las pruebas de rendimiento

Pruebas: 15 de 15 ejecutadas.

Metricas: **p95** es el tiempo que no superan el 95 % de las
peticiones (mejor medida que el promedio, porque el promedio
esconde los casos lentos). **Throughput** son peticiones
atendidas por segundo. **Error** es el porcentaje que fallo.

## Carga normal (10 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-normal | Consulta de stock de un producto (Inventario, lectura) | 1185 | 9.9/s | 12 ms | 14 ms | 19 ms | 0.00 % | CUMPLE |
| E2-normal | Busqueda de productos por texto (Inventario, lectura) | 1170 | 9.8/s | 14 ms | 17 ms | 24 ms | 0.00 % | CUMPLE |
| E3-normal | Descuento de stock por venta (Inventario, escritura) | 1163 | 9.8/s | 17 ms | 23 ms | 26 ms | 0.00 % | CUMPLE |
| E4-normal | Resumen de reposicion (Reposicion, lectura) | 1157 | 9.7/s | 10 ms | 12 ms | 16 ms | 0.00 % | CUMPLE |
| E5-normal | Solicitud automatica (Reposicion, escritura) | 1158 | 9.7/s | 13 ms | 17 ms | 21 ms | 0.00 % | CUMPLE |

## Carga pico (50 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-pico | Consulta de stock de un producto (Inventario, lectura) | 5817 | 48.8/s | 8 ms | 14 ms | 20 ms | 0.00 % | CUMPLE |
| E2-pico | Busqueda de productos por texto (Inventario, lectura) | 5835 | 49.0/s | 9 ms | 18 ms | 25 ms | 0.00 % | CUMPLE |
| E3-pico | Descuento de stock por venta (Inventario, escritura) | 5855 | 49.2/s | 8 ms | 20 ms | 28 ms | 0.00 % | CUMPLE |
| E4-pico | Resumen de reposicion (Reposicion, lectura) | 5803 | 48.7/s | 7 ms | 12 ms | 16 ms | 0.00 % | CUMPLE |
| E5-pico | Solicitud automatica (Reposicion, escritura) | 5844 | 49.1/s | 6 ms | 15 ms | 22 ms | 0.00 % | CUMPLE |

## Estres (150 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-estres | Consulta de stock de un producto (Inventario, lectura) | 26180 | 146.1/s | 4 ms | 12 ms | 20 ms | 0.00 % | Aguanto |
| E2-estres | Busqueda de productos por texto (Inventario, lectura) | 26088 | 145.6/s | 5 ms | 16 ms | 28 ms | 0.00 % | Aguanto |
| E3-estres | Descuento de stock por venta (Inventario, escritura) | 24042 | 134.1/s | 65 ms | 150 ms | 450 ms | 0.00 % | Aguanto |
| E4-estres | Resumen de reposicion (Reposicion, lectura) | 26204 | 146.2/s | 3 ms | 10 ms | 15 ms | 0.00 % | Aguanto |
| E5-estres | Solicitud automatica (Reposicion, escritura) | 25375 | 141.6/s | 11 ms | 37 ms | 130 ms | 0.00 % | Aguanto |

## Como se degrada cada endpoint

| Endpoint | p95 normal | p95 pico | p95 estres | Error en estres |
| --- | ---: | ---: | ---: | ---: |
| E1 | 14 ms | 14 ms | 12 ms | 0.00 % |
| E2 | 17 ms | 18 ms | 16 ms | 0.00 % |
| E3 | 23 ms | 20 ms | 150 ms | 0.00 % |
| E4 | 12 ms | 12 ms | 10 ms | 0.00 % |
| E5 | 17 ms | 15 ms | 37 ms | 0.00 % |
