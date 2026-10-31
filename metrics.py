"""Reglas de negocio independientes del navegador y del almacenamiento."""
import hashlib
from urllib.parse import urlsplit, urlunsplit

RATIO_UMBRAL = 20.0

def canonical_url(raw_url: str) -> str:
    parts = urlsplit(str(raw_url).strip())
    if parts.scheme.lower() not in ("http", "https") or parts.hostname not in ("shopstar.pe", "www.shopstar.pe"):
        raise ValueError("URL de producto fuera del dominio shopstar.pe")
    return urlunsplit(("https", "www.shopstar.pe", parts.path.rstrip("/") or "/", "", ""))

def product_id(url: str) -> str:
    return hashlib.sha256(canonical_url(url).encode("utf-8")).hexdigest()

def is_good_offer(ratio) -> bool:
    return ratio is not None and ratio <= RATIO_UMBRAL

def calc_change_pct(current, reference):
    if current is None or reference is None or reference <= 0:
        return None
    return (current / reference - 1) * 100.0

def price_alert(current, reference_min, tolerance_pct=10) -> bool:
    change = calc_change_pct(current, reference_min)
    return change is not None and change >= tolerance_pct

def failed_scrape_record(url, error, captured_at):
    return dict(url=url, product_name="", seller="", price_current=None, price_previous=None,
                price_discount_pct=None, miles_current=None, miles_previous=None, miles_per_sol=None,
                miles_discount_pct=None, miles_offer="", offer_level="", score=None,
                status="ERROR", notes=f"{type(error).__name__}: {str(error)[:230]}",
                captured_at=captured_at)
