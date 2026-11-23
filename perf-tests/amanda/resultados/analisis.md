# Análisis de los resultados

Ejecución del 23 de noviembre de 2026. Las 15 pruebas se ejecutaron
completas sobre Inventario y Reposición, con 500 productos sembrados.

---

## 1. Veredicto frente a los criterios

**Las 15 pruebas cumplen.** Cero errores en las tres cargas, incluida la de
estrés: 115.000 peticiones y ninguna falló.

El criterio del RNF06 es responder las consultas en menos de 2 segundos. El
peor p95 de todas las pruebas fue **150 ms**, en el descuento de stock bajo
estrés. Son **13 veces mejor** que el límite exigido.

| Escenario | Peor p95 | Errores |
|---|---:|---:|
| Carga normal (10 usuarios) | 23 ms | 0 % |
| Carga pico (50 usuarios) | 20 ms | 0 % |
| Estrés (150 usuarios) | 150 ms | 0 % |

---

## 2. Hallazgo principal: las escrituras se degradan, las lecturas no

Es el resultado más claro de toda la prueba, y **confirma lo que habíamos
predicho en el plan antes de medir**.

| Endpoint | Tipo | p95 normal | p95 pico | p95 estrés | Cambio |
|---|---|---:|---:|---:|---|
| E1 consulta de stock | lectura | 14 ms | 14 ms | 12 ms | plano |
| E2 búsqueda | lectura | 17 ms | 18 ms | 16 ms | plano |
| E4 resumen | lectura | 12 ms | 12 ms | 10 ms | plano |
| **E3 descuento de stock** | **escritura** | 23 ms | 20 ms | **150 ms** | **× 6,5** |
| **E5 solicitud automática** | **escritura** | 17 ms | 15 ms | **37 ms** | **× 2,2** |

Los tres endpoints de lectura ni se enteraron de que pasaron de 10 a 150
usuarios. Los dos de escritura sí, y el que más sufre es justamente el que
bloquea filas: `POST /stock/descuentos`.

**Por qué pasa.** Una lectura no estorba a otra: diez usuarios pueden
consultar el mismo producto al tiempo sin problema. Una escritura sí: el
descuento de stock bloquea la fila con `SELECT ... FOR UPDATE` para que dos
ventas simultáneas no dejen el inventario en negativo. Mientras una
petición tiene la fila, las demás que quieren ese producto esperan turno.
Con 150 usuarios peleando por 500 productos, esa fila se forma.

**Ese bloqueo no es un defecto, es la protección funcionando.** El precio
de que el stock nunca quede negativo es que las escrituras hagan fila. La
prueba lo que hace es ponerle número a ese precio: 150 ms en el peor 5 %.

---

## 3. Segundo hallazgo: la cola aparece en el 0,1 % de las peticiones

Mirando más allá del p95, aparece algo que el promedio y el p95 esconden:

| Endpoint | Tipo | p99 | p99,9 | Máximo |
|---|---|---:|---:|---:|
| E1 | lectura | 20 ms | 40 ms | 52 ms |
| E2 | lectura | 28 ms | 54 ms | 80 ms |
| E4 | lectura | 15 ms | 32 ms | 41 ms |
| **E3** | **escritura** | 450 ms | **3.500 ms** | 3.527 ms |
| **E5** | **escritura** | 130 ms | **3.400 ms** | 3.478 ms |

Las lecturas nunca pasaron de 80 ms, ni en el peor caso de 26.000
peticiones. Las dos escrituras tuvieron una cola larga: una de cada mil
peticiones tardó más de 3 segundos, y esas **sí superan el límite de 2
segundos del RNF06**.

Son el 0,1 % de las peticiones y solo bajo una carga que está por encima de
lo esperado, así que el requerimiento se considera cumplido. Pero es el
dato honesto y conviene decirlo: *el sistema cumple, con una cola de 0,1 %
de peticiones lentas en las escrituras bajo estrés*.

**La causa más probable: el contenedor atiende una petición a la vez.**

Los contenedores arrancan con `gunicorn -w 1`, o sea **un solo proceso
trabajador**. Gunicorn, en su modo normal, atiende una petición a la vez por
proceso: las demás esperan en fila antes de entrar.

Con eso, los números cuadran casi exactamente:

| | Trabajo real por petición | Peticiones por segundo | Qué tan ocupado está el proceso |
|---|---:|---:|---:|
| E1 lectura | ~4 ms | 146,1/s | **58 %** |
| E3 escritura | ~7 ms | 134,1/s | **94 %** |

Una escritura cuesta casi el doble que una lectura, porque además de
consultar tiene que actualizar el saldo e insertar la fila del kardex. Ese
"casi el doble" es lo que lleva al proceso del 58 % al 94 % de ocupación.

Y ahí está la clave: **una fila de espera no crece de forma proporcional, se
dispara cerca del 100 %**. Es lo mismo que en un banco: con las ventanillas
al 60 % apenas se espera, y al 95 % la fila da la vuelta. Pasar de 58 % a
94 % no duplica la espera, la multiplica.

**Dos causas secundarias**, que suman pero no explican el grueso:

- **El bloqueo de la fila de stock.** Cuando varios usuarios descuentan el
  mismo producto, esperan turno. Aporta, pero con 500 productos repartidos
  al azar la coincidencia es poco frecuente.
- **El circuit breaker probando el servicio caído.** E3 y E5 son los dos
  únicos endpoints que llaman a Configuración y a Proveedores, que no están
  levantados. Cada 30 segundos el circuito se vuelve a abrir para probar, y
  la petición que hace esa prueba paga el timeout de 3 segundos. Encaja con
  que el máximo sea justo de 3,5 s y con que solo estos dos endpoints lo
  tengan.

---

## 4. Lo que esta prueba NO demostró

Esto hay que decirlo, porque un resultado donde todo pasa suele significar
que no se apretó lo suficiente.

**No se encontró el límite del sistema.** El throughput medido fue
exactamente el que la propia prueba permitía, no el que el servicio
aguanta:

| Endpoint | Usuarios | Throughput medido | Máximo posible de la prueba | % |
|---|---:|---:|---:|---:|
| E1 | 150 | 146,1/s | 148,2/s | 99 % |
| E2 | 150 | 145,6/s | 147,6/s | 99 % |
| E4 | 150 | 146,2/s | 148,5/s | 98 % |
| E5 | 150 | 141,6/s | 144,6/s | 98 % |
| E3 | 150 | 134,1/s | 130,4/s | 103 % |

Cada usuario virtual espera entre 0,5 y 1,5 segundos entre una petición y
la siguiente, así que 150 usuarios no pueden generar más de unas 148
peticiones por segundo por mucho que el servidor sea rápido. El servicio
entregó el 98-100 % de ese tope en todas las pruebas.

**Qué significa:** el cuello de botella fue la prueba, no el servicio. Si el
throughput hubiera dejado de subir estando por debajo del tope, ahí sí
habría saturación. No la hubo.

**Segunda señal de lo mismo:** las lecturas respondieron *más rápido* con
150 usuarios que con 10 (E1: 14 ms → 12 ms). Un servicio saturado nunca
mejora al cargarlo más. Lo que pasó es que la primera prueba corrió en
frío, con la caché de MySQL vacía y las conexiones sin abrir, y las
siguientes ya encontraron todo caliente.

**Tercera observación honesta:** esperábamos que la búsqueda de E2 saliera
claramente más lenta, porque `LIKE '%texto%'` obliga a recorrer la tabla
entera. Salió apenas 4 ms por encima de E1. La razón es que **500 productos
son muy pocos**: recorrer 500 filas no le cuesta nada a MySQL. El problema
del `LIKE` aparecería con 100.000 productos, no con 500.

---

## 5. Optimización propuesta y cómo validarla

La optimización se deduce directamente del diagnóstico: si el problema es
que hay **un solo proceso** atendiendo, la solución es poner más.

**Hipótesis, escrita antes de medir:** subir de 1 a 4 procesos baja la
ocupación del 94 % a cerca del 24 %, y a esa altura la fila de espera
prácticamente desaparece. El p95 de E3 bajo estrés debería caer de **150 ms
a algo entre 15 y 30 ms**, y la cola larga de 3,5 segundos debería
desaparecer o reducirse mucho.

**Experimento (unos 5 minutos):**

1. En `services/inventario/Dockerfile`, cambiar `"-w", "1"` por `"-w", "4"`.
2. `docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build inventario`
3. Repetir una sola prueba: `python ejecutar.py --prueba E3-estres` (3 minutos).
4. Comparar contra los valores de ahora: p95 150 ms, p99,9 3.500 ms, 134,1 peticiones por segundo.

**Cómo leer el resultado, pase lo que pase:**

- **Si el p95 baja a 15-30 ms**, la hipótesis se confirma: faltaban procesos.
  Optimización propuesta, medida y validada.
- **Si baja poco**, el cuello está en el bloqueo de la fila de stock o en el
  timeout del servicio caído, y agregar procesos no ayuda. También es un
  resultado válido: una optimización descartada con datos vale igual que una
  que funciona, y es más honesta que no haberla probado.

**Nota aparte:** el comentario del Dockerfile dice `-w 2 dos procesos` pero
el comando ejecuta `-w 1`. Hay que dejar los dos de acuerdo.

---

## 6. Qué queda para la Entrega 4

- **Encontrar el límite de verdad**, quitando la pausa entre peticiones o
  subiendo mucho los usuarios, hasta que aparezcan errores.
- **Repetir E2 con 100.000 productos**, que es donde el `LIKE` debería
  dolerle, y ahí sí validar el índice FULLTEXT.
- **Medir a través del API Gateway**, para saber cuánto agrega él.
- **Medir con los ocho servicios arriba**, para que E3 y E5 no paguen el
  timeout de los servicios que no existen.
