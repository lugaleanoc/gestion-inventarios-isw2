# Resultados de las pruebas de rendimiento

Pruebas: 15 de 15 ejecutadas.

Metricas: **p95** es el tiempo que no superan el 95 % de las
peticiones (mejor medida que el promedio, porque el promedio
esconde los casos lentos). **Throughput** son peticiones
atendidas por segundo. **Error** es el porcentaje que fallo.

## Carga normal (20 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-normal | Consulta de stock de un producto (Inventario, lectura) | 1142 | 19.3/s | 12 ms | 13 ms | 14 ms | 0.00 % | CUMPLE |
| E2-normal | Busqueda de productos por texto (Inventario, lectura) | 1138 | 19.3/s | 14 ms | 16 ms | 20 ms | 0.00 % | CUMPLE |
| E3-normal | Descuento de stock por venta (Inventario, escritura) | 1140 | 19.3/s | 11 ms | 21 ms | 24 ms | 0.00 % | CUMPLE |
| E4-normal | Resumen de reposicion (Reposicion, lectura) | 1155 | 19.6/s | 10 ms | 11 ms | 13 ms | 0.00 % | CUMPLE |
| E5-normal | Solicitud automatica (Reposicion, escritura) | 1148 | 19.5/s | 9 ms | 16 ms | 37 ms | 0.00 % | CUMPLE |

## Carga pico (100 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-pico | Consulta de stock de un producto (Inventario, lectura) | 5842 | 98.9/s | 4 ms | 13 ms | 31 ms | 0.00 % | CUMPLE |
| E2-pico | Busqueda de productos por texto (Inventario, lectura) | 5809 | 98.4/s | 5 ms | 16 ms | 31 ms | 0.00 % | CUMPLE |
| E3-pico | Descuento de stock por venta (Inventario, escritura) | 5749 | 97.3/s | 8 ms | 18 ms | 68 ms | 0.00 % | CUMPLE |
| E4-pico | Resumen de reposicion (Reposicion, lectura) | 5790 | 98.0/s | 3 ms | 11 ms | 23 ms | 0.00 % | CUMPLE |
| E5-pico | Solicitud automatica (Reposicion, escritura) | 5726 | 97.0/s | 6 ms | 13 ms | 49 ms | 0.00 % | CUMPLE |

## Estres (300 usuarios)

| Prueba | Endpoint | Peticiones | Throughput | p50 | p95 | p99 | Error | Resultado |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| E1-estres | Consulta de stock de un producto (Inventario, lectura) | 16988 | 287.5/s | 5 ms | 11 ms | 59 ms | 0.00 % | Aguanto |
| E2-estres | Busqueda de productos por texto (Inventario, lectura) | 16865 | 285.4/s | 7 ms | 22 ms | 78 ms | 0.00 % | Aguanto |
| E3-estres | Descuento de stock por venta (Inventario, escritura) | 12687 | 214.7/s | 410 ms | 490 ms | 530 ms | 0.00 % | Aguanto |
| E4-estres | Resumen de reposicion (Reposicion, lectura) | 17024 | 288.1/s | 4 ms | 7 ms | 41 ms | 0.00 % | Aguanto |
| E5-estres | Solicitud automatica (Reposicion, escritura) | 16594 | 280.8/s | 26 ms | 80 ms | 120 ms | 0.00 % | Aguanto |

## Como se degrada cada endpoint

| Endpoint | p95 normal | p95 pico | p95 estres | Error en estres |
| --- | ---: | ---: | ---: | ---: |
| E1 | 13 ms | 13 ms | 11 ms | 0.00 % |
| E2 | 16 ms | 16 ms | 22 ms | 0.00 % |
| E3 | 21 ms | 18 ms | 490 ms | 0.00 % |
| E4 | 11 ms | 11 ms | 7 ms | 0.00 % |
| E5 | 16 ms | 13 ms | 80 ms | 0.00 % |
