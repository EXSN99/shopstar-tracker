"""Reglas de negocio independientes del navegador y del almacenamiento."""
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit

RATIO_UMBRAL = 20.0

# Las fichas del Excel real usan /<slug>/p, no basta con buscar "/p".
# El slug NO requiere un ID numérico (hay productos genuinos sin ID al final).
PRODUCT_PATH_RE = re.compile(r"^/[^/?#]+/p/?$", re.IGNORECASE)


def is_product_url(raw_url: str) -> bool:
    """Valida dominio Shopstar y ruta completa de ficha de producto."""
    try:
        parts = urlsplit(str(raw_url).strip())
        return (
            parts.scheme.lower() in ("http", "https")
            and parts.hostname in ("shopstar.pe", "www.shopstar.pe")
            and parts.username is None
            and parts.password is None
            and (parts.port is None or parts.port in (80, 443))
            and PRODUCT_PATH_RE.fullmatch(parts.path) is not None
        )
    except (ValueError, AttributeError):
        return False


def canonical_url(raw_url: str) -> str:
    """URL canónica. Rechaza categorías, promociones, búsquedas y rutas ajenas."""
    if not is_product_url(raw_url):
        raise ValueError("No es una URL de ficha de producto de Shopstar")
    parts = urlsplit(str(raw_url).strip())
    return urlunsplit(("https", "www.shopstar.pe", parts.path.rstrip("/"), "", ""))


def filter_product_urls(urls):
    """Devuelve (URLs únicas válidas, URLs rechazadas) sin contaminar la ingesta."""
    accepted, rejected, seen = [], [], set()
    for raw in urls:
        try:
            normalized = canonical_url(raw)
        except ValueError:
            rejected.append(str(raw))
            continue
        if normalized not in seen:
            seen.add(normalized)
            accepted.append(normalized)
    return accepted, rejected

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
