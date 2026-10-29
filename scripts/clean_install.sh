#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="${1:-demurrage_clean}"
DEMO="${2:-no}"
EXTRA_ARGS=()
if [ "$#" -ge 3 ]; then
  shift 2
  EXTRA_ARGS=("$@")
fi

# Base de datos limpia.
"$ROOT/scripts/pg.py" psql --db postgres "DROP DATABASE IF EXISTS ${DB};"
"$ROOT/scripts/pg.py" psql --db postgres "CREATE DATABASE ${DB} OWNER odoo;"

mkdir -p /tmp/opencode
LOG="$(mktemp /tmp/opencode/clean_install.XXXXXX.log)"

ARGS=(
  --addons-path="$ROOT/.odoo/odoo/addons,$ROOT"
  --db_host="$ROOT/.pgdata" --db_port=5432 --db_user=odoo --db_password=odoo
  -d "$DB" -i container_demurrage
)

if [[ "$DEMO" != "demo" && "$DEMO" != "yes" && "$DEMO" != "true" ]]; then
  ARGS+=(--without-demo=all)
fi

ARGS+=(--stop-after-init --log-level=info)

if ! "$ROOT/.venv/bin/python" "$ROOT/.odoo/odoo/odoo-bin" "${ARGS[@]}" ${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"} >"$LOG" 2>&1; then
  echo "La instalación falló. Log: $LOG" >&2
  tail -n 40 "$LOG" >&2
  exit 1
fi

# Se ignoran los errores de docutils/RST de las descripciones de módulos de Odoo
# (líneas del tipo "<string>:N: (ERROR/K) ..."), que no impiden la instalación.
if grep -nE "ERROR|CRITICAL|not found" "$LOG" | grep -vE '<string>:[0-9]+: \(ERROR/[0-9]+\)' | grep -q .; then
  echo "Se encontró ERROR/CRITICAL/not found en el log. Log: $LOG" >&2
  grep -nE "ERROR|CRITICAL|not found" "$LOG" | grep -vE '<string>:[0-9]+: \(ERROR/[0-9]+\)' >&2
  exit 1
fi

echo "Instalación limpia completada correctamente (base: ${DB}). Log: ${LOG}"
