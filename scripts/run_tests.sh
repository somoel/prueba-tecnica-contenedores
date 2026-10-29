#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB="demurrage_test"

# Base de datos limpia para las pruebas.
"$ROOT/scripts/pg.py" psql "DROP DATABASE IF EXISTS ${DB};"
"$ROOT/scripts/pg.py" psql "CREATE DATABASE ${DB} OWNER odoo;"

exec "$ROOT/.venv/bin/python" "$ROOT/.odoo/odoo/odoo-bin" \
  --addons-path="$ROOT/.odoo/odoo/addons,$ROOT" \
  --db_host="$ROOT/.pgdata" --db_port=5432 --db_user=odoo --db_password=odoo \
  -d "$DB" -i container_demurrage --without-demo=all --test-enable \
  --test-tags=/container_demurrage --stop-after-init --log-level=test \
  "$@"
