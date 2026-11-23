#!/usr/bin/env bash
TMP="${TMPDIR:-/tmp}/jak-local"
for archivo in "$TMP"/*.pid; do
  [ -f "$archivo" ] && kill "$(cat "$archivo")" 2>/dev/null
done
rm -f "$TMP"/*.pid
echo "Servicios locales apagados"
