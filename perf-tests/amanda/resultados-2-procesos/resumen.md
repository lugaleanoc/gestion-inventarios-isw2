# Resultados de las pruebas de rendimiento

Pruebas: 15 de 15 ejecutadas.

Metricas: **p95** es el tiempo que no superan el 95 % de las
peticiones (mejor medida que el promedio, porque el promedio
esconde los casos lentos). **Throughput** son peticiones
atendidas por segundo. **Error** es el porcentaje que fallo.

## Carga normal (10 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-normal | Consulta de stock de un producto (Inventario, lectura) | 1161 | 9.7/s | 6 ms | 13 ms | 15 ms | 0.00 % | CUMPLE |
| E2-normal | Busqueda de productos por texto (Inventario, lectura) | 1157 | 9.7/s | 14 ms | 15 ms | 18 ms | 0.00 % | CUMPLE |
| E3-normal | Descuento de stock por venta (Inventario, escritura) | 1148 | 9.7/s | 10 ms | 22 ms | 25 ms | 0.00 % | CUMPLE |
| E4-normal | Resumen de reposicion (Reposicion, lectura) | 1174 | 9.9/s | 5 ms | 11 ms | 12 ms | 0.00 % | CUMPLE |
| E5-normal | Solicitud automatica (Reposicion, escritura) | 1162 | 9.8/s | 12 ms | 16 ms | 22 ms | 0.00 % | CUMPLE |

## Carga pico (50 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-pico | Consulta de stock de un producto (Inventario, lectura) | 5850 | 49.1/s | 5 ms | 13 ms | 16 ms | 0.00 % | CUMPLE |
| E2-pico | Busqueda de productos por texto (Inventario, lectura) | 5878 | 49.3/s | 9 ms | 16 ms | 20 ms | 0.00 % | CUMPLE |
| E3-pico | Descuento de stock por venta (Inventario, escritura) | 5761 | 48.3/s | 9 ms | 23 ms | 140 ms | 0.00 % | CUMPLE |
| E4-pico | Resumen de reposicion (Reposicion, lectura) | 5869 | 49.3/s | 4 ms | 11 ms | 13 ms | 0.00 % | CUMPLE |
| E5-pico | Solicitud automatica (Reposicion, escritura) | 5837 | 49.0/s | 6 ms | 14 ms | 19 ms | 0.00 % | CUMPLE |

## Estres (150 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-estres | Consulta de stock de un producto (Inventario, lectura) | 26160 | 146.0/s | 4 ms | 11 ms | 16 ms | 0.00 % | Aguanto |
| E2-estres | Busqueda de productos por texto (Inventario, lectura) | 26087 | 145.6/s | 6 ms | 13 ms | 25 ms | 0.00 % | Aguanto |
| E3-estres | Descuento de stock por venta (Inventario, escritura) | 24688 | 137.6/s | 16 ms | 220 ms | 1500 ms | 0.00 % | Aguanto |
| E4-estres | Resumen de reposicion (Reposicion, lectura) | 26260 | 146.4/s | 4 ms | 10 ms | 25 ms | 0.00 % | Aguanto |
| E5-estres | Solicitud automatica (Reposicion, escritura) | 25784 | 143.9/s | 7 ms | 15 ms | 44 ms | 0.00 % | Aguanto |

## Como se degrada cada endpoint

| Endpoint | p95 normal | p95 pico | p95 estres | Error en estres |
| --- | ---: | ---: | ---: | ---: |
| E1 | 13 ms | 13 ms | 11 ms | 0.00 % |
| E2 | 15 ms | 16 ms | 13 ms | 0.00 % |
| E3 | 22 ms | 23 ms | 220 ms | 0.00 % |
| E4 | 11 ms | 11 ms | 10 ms | 0.00 % |
| E5 | 16 ms | 14 ms | 15 ms | 0.00 % |
