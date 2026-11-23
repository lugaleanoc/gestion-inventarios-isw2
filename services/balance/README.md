# Microservicio de Balance Diario

Registra los ingresos y egresos de cada local, por medio de pago (efectivo,
tarjeta, QR), y calcula el balance diario (RF21, RF22, RF23). No hace
contabilidad. Responsable: Jasmin.

Contrato: `docs/balance-diario-openapi.yaml` (copia de `docs/api/balance-diario-openapi.yaml`, v1.2.0).
Swagger: `http://localhost:8005/docs/` con el compose de pruebas.

## Endpoints

| Método | Ruta | Quién puede |
|--------|------|-------------|
| GET | `/health` | público (`{"servicio": "balance-diario", "estado": "ok"}`) |
| POST | `/api/balance/movimientos` | administrador, vendedor (ingreso o egreso manual) |
| GET | `/api/balance/movimientos` | administrador, vendedor · interno: reportes (paginado) |
| POST | `/api/balance/movimientos/ventas` | **solo** `X-Servicio-Origen: ventas` |
| GET | `/api/balance/movimientos/{id}` | administrador, vendedor · interno: reportes |
| POST | `/api/balance/movimientos/{id}/ajustes` | administrador |
| GET | `/api/balance/diario?localId=&fecha=` | administrador, vendedor · interno: reportes |
| GET | `/api/balance/reporte?fechaDesde=&fechaHasta=` | administrador · interno: reportes |

## Reglas importantes

- **Los movimientos no se editan ni se borran (RNF20).** No hay PUT ni DELETE.
  Un error se corrige con un **ajuste**: un movimiento nuevo que guarda en
  `ajustaA` el id del original. El monto del ajuste puede ser negativo.
- **Idempotente por `ventaId`:** si Ventas manda dos veces el ingreso de la
  misma venta, la segunda responde `409 VENTA_YA_REGISTRADA` y no se duplica.
  Además hay una restricción `UNIQUE (empresa_id, venta_id)` en MySQL, por si
  dos reintentos llegan al mismo tiempo.
- **Fórmula del balance**, por medio de pago:
  `disponible = ingresos − egresos + ajustes`. El efectivo disponible es lo que
  debería haber en la caja.
- Las fechas se guardan en hora de Colombia (`America/Bogota`). Un ajuste
  cuenta en el balance del día en que se registra.

## Cómo correrlo y probarlo

```bash
# Desde la raíz del repositorio (8005 = Balance)
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up -d --build

curl "http://localhost:8005/api/balance/diario?localId=1&fecha=2026-11-20" \
  -H "X-Empresa-Id: 1" -H "X-Usuario-Id: 12" -H "X-Rol: vendedor"

# Prueba de humo (SQLite en memoria, sin Docker)
cd services/balance && pip install -r requirements.txt && python pruebas/prueba_humo.py
```
