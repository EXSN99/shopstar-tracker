"""Comprobación integral Neon: conexión SSL, esquema y escritura temporal.
Nunca imprime credenciales ni la cadena de conexión.
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from db import connection, init_db  # noqa: E402

def main():
    load_dotenv(ROOT / ".env.local", override=False)
    load_dotenv(ROOT / ".env", override=False)
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise SystemExit("ERROR: falta DATABASE_URL; configúralo como secreto o en .env.local")

    print("1/4 Conexión a Neon PostgreSQL…", flush=True)
    with connection(db_url) as conn:
        info = conn.execute("SELECT current_database() AS database_name, current_user AS db_role").fetchone()
        print(f"   OK: base={info['database_name']}, rol={info['db_role']}", flush=True)

    print("2/4 Creación/verificación del esquema…", flush=True)
    init_db(db_url)
    with connection(db_url) as conn:
        tables = conn.execute(
            """SELECT relname FROM pg_class
               WHERE oid IN (to_regclass('public.products'),
                             to_regclass('public.scrape_runs'),
                             to_regclass('public.price_history'))"""
        ).fetchall()
        actual = {row["relname"] for row in tables}
        required = {"products", "scrape_runs", "price_history"}
        if actual != required:
            raise RuntimeError(f"Faltan tablas: {sorted(required-actual)}")
        print(f"   OK: {', '.join(sorted(actual))}", flush=True)

    print("3/4 Escritura y lectura temporal (sin dejar registros)…", flush=True)
    with connection(db_url) as conn:
        conn.execute("CREATE TEMP TABLE shopstar_neon_check (item TEXT NOT NULL) ON COMMIT DROP")
        conn.execute("INSERT INTO shopstar_neon_check (item) VALUES (%s)", ("OK",))
        row = conn.execute("SELECT item FROM shopstar_neon_check").fetchone()
        assert row["item"] == "OK", "Falló lectura después de escritura"
        print("   OK: INSERT/SELECT en tabla temporal", flush=True)

    print("4/4 Resultado: PASS - Neon accesible, esquema creado y escritura funcional", flush=True)

if __name__ == "__main__":
    main()
