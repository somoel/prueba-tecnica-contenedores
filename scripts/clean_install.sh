#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="${1:-demurrage_clean}"
DEMO="${2:-no}"

# Base de datos limpia.
"$ROOT/scripts/pg.py" psql "DROP DATABASE IF EXISTS ${DB};"
"$ROOT/scripts/pg.py" psql "CREATE DATABASE ${DB} OWNER odoo;"

LOG="$(mktemp /tmp/opencode/clean_install.XXXXXX.log)"
mkdir -p /tmp/opencode

ARGS=(
  --addons-path="$ROOT/.odoo/odoo/addons,$ROOT"
  --db_host="$ROOT/.pgdata" --db_port=5432 --db_user=odoo --db_password=odoo
  -d "$DB" -i container_demurrage
)

if [[ "$DEMO" != "demo" && "$DEMO" != "yes" && "$DEMO" != "true" ]]; then
  ARGS+=(--without-demo=all)
fi

ARGS+=(--stop-after-init --log-level=info)

if ! "$ROOT/.venv/bin/python" "$ROOT/.odoo/odoo/odoo-bin" "${ARGS[@]}" "$@" >"$LOG" 2>&1; then
  echo "La instalación falló. Log: $LOG" >&2
  tail -n 40 "$LOG" >&2
  exit 1
fi

if grep -q "CRITICAL" "$LOG"; then
  echo "Se encontró CRITICAL en el log. Log: $LOG" >&2
  grep -n "CRITICAL" "$LOG" >&2
  exit 1
fi

echo "Instalación limpia completada correctamente (base: ${DB}). Log: ${LOG}"
