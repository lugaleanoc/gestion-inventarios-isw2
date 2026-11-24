# Microservicio de Ventas

Registra las ventas de los locales físicos y de la tienda web, con su canal y
su medio de pago (RF15, RF16, RF17). Responsable: Jasmin.

Contrato: `docs/ventas-openapi.yaml` (copia de `docs/api/ventas-openapi.yaml`, v1.2.0).
Swagger: `http://localhost:8004/docs/` con el compose de pruebas.

## Endpoints

| Método | Ruta | Quién puede |
|--------|------|-------------|
| GET | `/health` | público |
| POST | `/api/ventas` | administrador, vendedor, tienda_web (solo canal `tienda_web`) |
| GET | `/api/ventas` | administrador, vendedor · interno: reportes (paginado) |
| GET | `/api/ventas/{ventaId}` | administrador, vendedor · interno: reportes |
| GET | `/api/ventas/resumen` | administrador · interno: reportes |
| POST | `/api/ventas/{ventaId}/reintento-balance` | administrador |

## Flujo de `POST /api/ventas` (`app/rutas/ventas.py`)

```
1. Valida los datos. tienda_web solo puede usar el canal tienda_web (si no, 403).
2. ¿Vino bodegaId? No -> GET /api/inventario/bodegas?localId=...  y toma la primera.
3. Guarda la venta con estado "en_proceso" (así ya tiene ventaId).
4. POST /api/inventario/stock/descuentos  ("todo o nada"; Inventario devuelve el precio)
      409            -> venta "rechazada", responde 409 STOCK_INSUFICIENTE
      sin respuesta  -> venta "rechazada", responde 503 SERVICIO_NO_DISPONIBLE
5. Guarda ítems y total, marca "confirmada" y llama a
   POST /api/balance/movimientos/ventas
      201 o 409      -> estadoBalance = "registrado"
      sin respuesta  -> estadoBalance = "pendiente" (la venta igual queda confirmada)
```

- El cliente **nunca** envía precios: si los envía, 400.
- Cada llamada a otro servicio (`app/clientes.py`) espera máximo **3 s** y se
  intenta **hasta 3 veces**; cada fallo queda en el log. Reintentar es seguro
  porque Inventario y Balance no repiten nada para el mismo `ventaId`.
- Una venta `pendiente` se puede reenviar a Balance con
  `POST /api/ventas/{id}/reintento-balance`.

## Inventario real y simulado (mock)

En `docker-compose.yml` Ventas llama al Inventario real
(`USAR_MOCK_INVENTARIO: "false"`): cada venta descuenta el stock en
`inventario-service` (RF17) y, si el producto queda en el mínimo, Inventario
dispara la solicitud de reposición automática (RF18).

El modo simulado (`USAR_MOCK_INVENTARIO=true`) queda solo para las pruebas de
rendimiento: `docker-compose.pruebas.yml` lo activa para medir Ventas y Balance
sin depender de Inventario. En ese modo Ventas no llama a Inventario:

- todas las bodegas son la **1**;
- el precio de todo producto es `MOCK_PRECIO` (10.000);
- si se piden más de `MOCK_STOCK_DISPONIBLE` (100) unidades responde
  `409 STOCK_INSUFICIENTE`, para poder probar el rechazo.

## Cómo correrlo y probarlo

```bash
# Desde la raíz del repositorio (8004 = Ventas)
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build

curl -X POST http://localhost:8004/api/ventas \
  -H "X-Empresa-Id: 1" -H "X-Usuario-Id: 12" -H "X-Rol: vendedor" \
  -H "Content-Type: application/json" \
  -d '{"localId": 1, "canal": "tienda_fisica", "medioPago": "efectivo",
       "items": [{"productoId": 105, "cantidad": 2}]}'

docker compose logs -f ventas

# Prueba de humo (SQLite en memoria, sin Docker)
cd services/ventas && pip install -r requirements.txt && python pruebas/prueba_humo.py
```
