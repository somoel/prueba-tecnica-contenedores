#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="${DB:-demurrage_dev}"
PORT="${PORT:-8069}"

echo "Odoo disponible en http://localhost:${PORT} (base: ${DB})"

exec "$ROOT/.venv/bin/python" "$ROOT/.odoo/odoo/odoo-bin" \
  --addons-path="$ROOT/.odoo/odoo/addons,$ROOT" \
  --db_host="$ROOT/.pgdata" --db_port=5432 --db_user=odoo --db_password=odoo \
  -d "$DB" --http-port="$PORT" \
  "$@"
