#!/home/chamber/projects/prueba-tecnica-contenedores/.venv/bin/python
"""Utilidad de desarrollo para PostgreSQL embebido con pgserver.

Comandos:
  start   Arranca el servidor (idempotente) y crea el rol ``odoo`` si no existe.
  status  Muestra si responde y su URI.
  psql    Ejecuta SQL recibido como argumento o por stdin.
"""

import argparse
import os
import sys
from pathlib import Path

import pgserver
import psycopg2

ROOT = Path(__file__).resolve().parent.parent
PGDATA = ROOT / ".pgdata"


def get_server():
    return pgserver.get_server(PGDATA, cleanup_mode=None)


def ensure_role():
    server = get_server()
    uri = server.get_uri(database="postgres")
    conn = psycopg2.connect(uri)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DO $$ BEGIN "
                "IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'odoo') THEN "
                "CREATE ROLE odoo LOGIN SUPERUSER CREATEDB PASSWORD 'odoo'; "
                "END IF; "
                "END $$;"
            )
    finally:
        conn.close()


def cmd_start(_args):
    server = get_server()
    ensure_role()
    print(f"PostgreSQL en ejecución. URI: {server.get_uri()}")


def cmd_status(_args):
    try:
        server = get_server()
        uri = server.get_uri(database="postgres")
        conn = psycopg2.connect(uri)
        conn.close()
        print(f"PostgreSQL responde. URI: {server.get_uri()}")
    except Exception as exc:  # pragma: no cover - diagnóstico de entorno
        print(f"PostgreSQL NO responde: {exc}")
        sys.exit(1)


def read_sql(args):
    if args.sql:
        return " ".join(args.sql)
    data = sys.stdin.read()
    if not data.strip():
        print("No se recibió SQL (argumento o stdin).", file=sys.stderr)
        sys.exit(2)
    return data


def cmd_psql(args):
    sql = read_sql(args)
    server = get_server()
    db = getattr(args, "db", None) or "demurrage_clean"
    uri = server.get_uri(database=db)
    conn = psycopg2.connect(uri)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description is not None:
                cols = [d[0] for d in cur.description]
                print("\t".join(cols))
                for row in cur.fetchall():
                    print("\t".join(str(v) for v in row))
            else:
                print(f"OK ({cur.rowcount} filas afectadas)")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="PostgreSQL embebido con pgserver")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("start", help="Arranca PostgreSQL (idempotente)")
    sub.add_parser("status", help="Estado de PostgreSQL")
    psql = sub.add_parser("psql", help="Ejecuta SQL")
    psql.add_argument("sql", nargs="*", help="Sentencia SQL")
    psql.add_argument("--db", "-d", default=None, help="Base de datos a usar (por defecto demurrage_clean)")
    args = parser.parse_args()

    if args.command == "start":
        cmd_start(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "psql":
        cmd_psql(args)


if __name__ == "__main__":
    main()
