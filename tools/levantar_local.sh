#!/usr/bin/env bash
set -e
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
TMP="${TMPDIR:-/tmp}/jak-local"
mkdir -p "$TMP"
export DB_DRIVER=sqlite JWT_SECRET=secreto-local EXPONER_CODIGO_RECUPERACION=true
export CONFIGURACION_URL=http://127.0.0.1:18000 INVENTARIO_URL=http://127.0.0.1:18000
export VENTAS_URL=http://127.0.0.1:18000 REPOSICION_URL=http://127.0.0.1:18000 BALANCE_URL=http://127.0.0.1:18000
export PROVEEDORES_URL=http://127.0.0.1:18002 REPORTES_URL=http://127.0.0.1:18003

rm -f "$TMP"/*.db "$TMP"/*.pid

arrancar() {
  local nombre="$1" carpeta="$2" puerto="$3" modulo="${4:-wsgi}"
  (
    cd "$carpeta"
    if [ -f init_db.py ]; then DB_PATH="$TMP/$nombre.db" python3 init_db.py >/dev/null; fi
    DB_PATH="$TMP/$nombre.db" exec python3 -m flask --app "$modulo" run -p "$puerto"
  ) >"$TMP/$nombre.log" 2>&1 </dev/null &
  echo $! >"$TMP/$nombre.pid"
}

arrancar mock "$RAIZ/tools/mock-servicios" 18000 app
arrancar proveedores "$RAIZ/services/proveedores" 18002
arrancar reportes "$RAIZ/services/reportes" 18003
arrancar gateway "$RAIZ/services/gateway" 18080

sleep 3
echo "Gateway en http://127.0.0.1:18080  (mock 18000, proveedores 18002, reportes 18003)"
echo "Prueba completa: python3 tools/smoke_test.py --mock http://127.0.0.1:18000 --proveedores http://127.0.0.1:18002 --reportes http://127.0.0.1:18003"
echo "Para apagar: tools/apagar_local.sh"
