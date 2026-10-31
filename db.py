"""Persistencia de capturas y consultas históricas en PostgreSQL/Neon."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from zoneinfo import ZoneInfo
import psycopg
from psycopg.rows import dict_row
from metrics import canonical_url, product_id

@contextmanager
def connection(db_url):
    if not db_url or not db_url.startswith(("postgres://", "postgresql://")):
        raise RuntimeError("DATABASE_URL debe ser una cadena PostgreSQL")
    with psycopg.connect(db_url, connect_timeout=20, row_factory=dict_row) as conn:
        yield conn

def init_db(db_url):
    sql = (Path(__file__).parent / "schema.sql").read_text(encoding="utf-8")
    with connection(db_url) as conn:
        conn.execute(sql)

def start_run(db_url):
    run_id = uuid4()
    with connection(db_url) as conn:
        conn.execute("INSERT INTO scrape_runs(run_id,status) VALUES (%s,'RUNNING')", (run_id,))
    return run_id

def save_batch(db_url, run_id, records):
    if not records:
        return
    with connection(db_url) as conn:
        for r in records:
            url = canonical_url(r["url"])
            pid = product_id(url)
            captured = r.get("captured_at") or datetime.now(timezone.utc)
            if isinstance(captured, str):
                captured = datetime.fromisoformat(captured)
                if captured.tzinfo is None:
                    captured = captured.replace(tzinfo=ZoneInfo("America/Lima"))
            conn.execute("""
                INSERT INTO products(product_id, product_url, product_name, seller)
                VALUES (%s,%s,%s,%s)
                ON CONFLICT(product_id) DO UPDATE SET
                    product_url=EXCLUDED.product_url,
                    product_name=CASE WHEN EXCLUDED.product_name<>'' THEN EXCLUDED.product_name ELSE products.product_name END,
                    seller=CASE WHEN EXCLUDED.seller<>'' THEN EXCLUDED.seller ELSE products.seller END,
                    last_seen=now()
            """,(pid,url,r.get("product_name") or "",r.get("seller") or ""))
            conn.execute("""
                INSERT INTO price_history(run_id,product_id,captured_at,price_current,price_previous,
                    price_discount_pct,miles_current,miles_previous,miles_per_sol,miles_discount_pct,score,status,notes)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(run_id,product_id) DO UPDATE SET
                    captured_at=EXCLUDED.captured_at,price_current=EXCLUDED.price_current,
                    price_previous=EXCLUDED.price_previous,price_discount_pct=EXCLUDED.price_discount_pct,
                    miles_current=EXCLUDED.miles_current,miles_previous=EXCLUDED.miles_previous,
                    miles_per_sol=EXCLUDED.miles_per_sol,miles_discount_pct=EXCLUDED.miles_discount_pct,
                    score=EXCLUDED.score,status=EXCLUDED.status,notes=EXCLUDED.notes
            """,(run_id,pid,captured,r.get("price_current"),r.get("price_previous"),r.get("price_discount_pct"),
                 r.get("miles_current"),r.get("miles_previous"),r.get("miles_per_sol"),r.get("miles_discount_pct"),
                 r.get("score"),r.get("status","ERROR"),r.get("notes") or ""))

def finish_run(db_url,run_id,status,discovered_count,error_message=""):
    if status not in ("COMPLETED","PARTIAL","FAILED"):
        raise ValueError("Estado de corrida inválido")
    with connection(db_url) as conn:
        conn.execute("""
          UPDATE scrape_runs SET finished_at=now(),status=%s,discovered_count=%s,
           processed_count=(SELECT count(*) FROM price_history WHERE run_id=%s),
           ok_count=(SELECT count(*) FROM price_history WHERE run_id=%s AND status='OK'),
           partial_count=(SELECT count(*) FROM price_history WHERE run_id=%s AND status='PARTIAL'),
           error_count=(SELECT count(*) FROM price_history WHERE run_id=%s AND status='ERROR'),
           error_message=%s
          WHERE run_id=%s
        """,(status,discovered_count,run_id,run_id,run_id,run_id,error_message[:500],run_id))

def list_runs(db_url,limit=60):
    with connection(db_url) as conn:
        return conn.execute("""
            SELECT run_id,started_at,finished_at,status,discovered_count,processed_count,
                   ok_count,partial_count,error_count
            FROM scrape_runs ORDER BY started_at DESC LIMIT %s
        """,(limit,)).fetchall()

def comparison_for_run(db_url,run_id,lookback_days=30):
    with connection(db_url) as conn:
        return conn.execute("""
            SELECT p.product_id,p.product_name,p.seller,p.product_url AS url,
              h.captured_at,h.price_current,h.price_previous,h.price_discount_pct,
              h.miles_current,h.miles_previous,h.miles_per_sol,h.miles_discount_pct,
              h.score,h.status,h.notes,
              prior.price_current AS observed_prior_price,
              prior.miles_current AS observed_prior_miles,
              prior.captured_at AS observed_prior_at,
              minima.minimum_price AS observed_min_price,
              minima.observations AS historical_observations
            FROM price_history h JOIN products p ON p.product_id=h.product_id
            LEFT JOIN LATERAL (
               SELECT prev.price_current, prev.miles_current, prev.captured_at
               FROM price_history prev
               WHERE prev.product_id=h.product_id AND prev.captured_at<h.captured_at
                 AND prev.status='OK' AND prev.price_current IS NOT NULL
               ORDER BY prev.captured_at DESC LIMIT 1
            ) prior ON TRUE
            LEFT JOIN LATERAL (
               SELECT MIN(prev.price_current) AS minimum_price, COUNT(*) AS observations
               FROM price_history prev
               WHERE prev.product_id=h.product_id AND prev.captured_at<h.captured_at
                 AND prev.captured_at >= h.captured_at - make_interval(days => %s)
                 AND prev.status='OK' AND prev.price_current IS NOT NULL
            ) minima ON TRUE
            WHERE h.run_id=%s ORDER BY h.miles_per_sol ASC NULLS LAST
        """,(lookback_days,run_id)).fetchall()

def product_history(db_url,pid,limit=500):
    with connection(db_url) as conn:
        return conn.execute("""
            SELECT captured_at,price_current,price_previous,miles_current,miles_previous,
                   miles_per_sol,status,notes
            FROM price_history WHERE product_id=%s ORDER BY captured_at DESC LIMIT %s
        """,(pid,limit)).fetchall()

def runs_trend(db_url,limit=90):
    with connection(db_url) as conn:
        return conn.execute("""
            SELECT r.run_id,r.started_at,
              count(h.id) FILTER(WHERE h.status='OK') AS full_records,
              count(h.id) FILTER(WHERE h.miles_per_sol<=20 AND h.status='OK') AS good_offers,
              count(h.id) AS processed
            FROM scrape_runs r JOIN price_history h ON h.run_id=r.run_id
            WHERE r.status IN ('COMPLETED','PARTIAL')
            GROUP BY r.run_id,r.started_at ORDER BY r.started_at DESC LIMIT %s
        """,(limit,)).fetchall()
