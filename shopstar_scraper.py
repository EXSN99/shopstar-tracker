import os
from sqlalchemy import create_engine
import argparse
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
from playwright.sync_api import sync_playwright

BASE = "https://www.shopstar.pe"
CAMPAIGN = f"{BASE}/bombas-millas"
MILES_RE = re.compile(r"([\d\.,]+)\s*Millas", re.I)
PRICE_RE = re.compile(r"S/\s*([\d\.,]+)", re.I)


def parse_number(value):
    if value is None:
        return None
    s = str(value).replace("\xa0", " ").strip()
    m = re.search(r"([\d][\d\.,]*)", s)
    if not m:
        return None
    x = m.group(1)
    if "," in x and "." in x:
        x = x.replace(",", "")
    elif "," in x and len(x.rsplit(",", 1)[-1]) == 2:
        x = x.replace(",", ".")
    else:
        x = x.replace(",", "")
    try:
        return float(x)
    except ValueError:
        return None


def regex_values(pattern, text):
    out = []
    for m in pattern.finditer(text or ""):
        n = parse_number(m.group(1))
        if n is not None and n not in out:
            out.append(n)
    return out


def close_popups(page):
    labels = ["Cerrar", "CERRAR", "×", "No, gracias", "Ahora no"]
    for label in labels:
        try:
            page.get_by_role("button", name=label).first.click(timeout=500)
        except Exception:
            pass


def render_campaign_page(page, url):
    print(f"  Abriendo {url}", flush=True)
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1200)
    close_popups(page)
    # Moderate scroll to trigger lazy-loaded cards without long waits.
    for _ in range(4):
        try:
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(200)
        except Exception:
            break


def campaign_product_urls(page, url):
    render_campaign_page(page, url)
    urls = []
    links = page.locator("a[href]")
    count = min(links.count(), 5000)
    for i in range(count):
        try:
            href = links.nth(i).get_attribute("href") or ""
            full = urljoin(BASE, href)
            parsed = full.split("#", 1)[0]
            if not parsed.startswith(BASE + "/"):
                continue
            path = parsed[len(BASE):]
            if "/p" not in path:
                continue
            if parsed.startswith(CAMPAIGN):
                continue
            if parsed not in urls:
                urls.append(parsed)
        except Exception:
            continue
    return urls


def discover_urls(page, max_pages=50):
    all_urls = []
    for page_num in range(1, max_pages + 1):
        url = CAMPAIGN if page_num == 1 else f"{CAMPAIGN}?page={page_num}"
        try:
            found = campaign_product_urls(page, url)
        except Exception as e:
            print(f"  ERROR página {page_num}: {e}", flush=True)
            break
        before = len(all_urls)
        for u in found:
            if u not in all_urls:
                all_urls.append(u)
        print(f"Page {page_num}: {len(found)} links | {before} -> {len(all_urls)} únicos", flush=True)
        if page_num > 1 and len(all_urls) == before:
            print(f"Page {page_num} sin productos nuevos. Fin de paginación.", flush=True)
            break
    return all_urls


def extract_product(page, url):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1400)
    close_popups(page)
    for _ in range(3):
        try:
            page.mouse.wheel(0, 900)
            page.wait_for_timeout(200)
        except Exception:
            break

    try:
        body = page.locator("body").inner_text(timeout=5000)
    except Exception:
        body = ""

    try:
        title = page.locator("h1").first.inner_text(timeout=2500).strip()
    except Exception:
        title = ""

    seller = ""
    m = re.search(r"Vendido por\s+([^\n]+)", body, re.I)
    if m:
        seller = m.group(1).strip()

    # -------- Millas --------
    mile_values = []
    for selector in [
        "[class*='millas'][class*='cantidad']",
        "[class*='millas']",
    ]:
        try:
            loc = page.locator(selector)
            for i in range(min(loc.count(), 30)):
                txt = loc.nth(i).inner_text(timeout=600)
                mile_values.extend(regex_values(MILES_RE, txt))
        except Exception:
            pass
        mile_values = list(dict.fromkeys(mile_values))
        if len(mile_values) >= 2:
            break

    if len(mile_values) < 2:
        mile_values = list(dict.fromkeys(regex_values(MILES_RE, body)))

    miles_current = min(mile_values[:2]) if mile_values else None
    miles_previous = max(mile_values[:2]) if len(mile_values) >= 2 else None

    # -------- Precio --------
    price_values = []
    for selector in [
        "[class*='sellingPrice']",
        "[class*='selling-price']",
        "[class*='price']",
        "[class*='Price']",
    ]:
        try:
            loc = page.locator(selector)
            for i in range(min(loc.count(), 50)):
                txt = loc.nth(i).inner_text(timeout=600)
                price_values.extend(regex_values(PRICE_RE, txt))
        except Exception:
            pass
        if price_values:
            # keep searching a little, but avoid huge DOM scans
            continue

    if not price_values:
        price_values = regex_values(PRICE_RE, body)
    price_values = list(dict.fromkeys(price_values))

    price_previous = None
    for selector in [
        "s",
        "del",
        "[class*='listPrice']",
        "[class*='list-price']",
        "[class*='previous']",
    ]:
        try:
            loc = page.locator(selector)
            for i in range(min(loc.count(), 20)):
                vals = regex_values(PRICE_RE, loc.nth(i).inner_text(timeout=600))
                if vals:
                    price_previous = vals[0]
                    break
            if price_previous is not None:
                break
        except Exception:
            pass

    price_current = None
    if price_previous is not None:
        for p in price_values:
            if abs(p - price_previous) > 1e-9:
                price_current = p
                break
    if price_current is None and price_values:
        price_current = min(price_values)

    miles_per_sol = (
        miles_current / price_current
        if miles_current is not None and price_current and price_current > 0
        else None
    )
    price_discount_pct = (
        1 - price_current / price_previous
        if price_current is not None and price_previous and price_previous > 0
        else None
    )
    miles_discount_pct = (
        1 - miles_current / miles_previous
        if miles_current is not None and miles_previous and miles_previous > 0
        else None
    )

    notes = []
    if price_current is None:
        notes.append("precio no detectado")
    if miles_current is None:
        notes.append("millas no detectadas")

    status = "OK" if not notes else "PARTIAL"
    is_good = miles_per_sol is not None and miles_per_sol < 20

    # Score only for offers; lower ratio wins, then higher real miles discount.
    score = None
    if is_good:
        score = 100 - (miles_per_sol * 5)
        if miles_discount_pct is not None:
            score += miles_discount_pct * 25
        if price_discount_pct is not None and price_discount_pct >= 0:
            score += min(10, price_discount_pct * 10)
        score = round(score, 2)

    return {
        "url": url,
        "product_name": title,
        "seller": seller,
        "price_current": price_current,
        "price_previous": price_previous,
        "price_discount_pct": price_discount_pct,
        "miles_current": miles_current,
        "miles_previous": miles_previous,
        "miles_per_sol": miles_per_sol,
        "miles_discount_pct": miles_discount_pct,
        "miles_offer": "SI" if is_good else "",
        "offer_level": "BUENA OFERTA" if is_good else "",
        "score": score,
        "status": status,
        "notes": "; ".join(notes),
        "captured_at": datetime.now().isoformat(timespec="seconds"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", default="", help="CSV existente con columna url; si se omite, descubre la campaña")
    ap.add_argument("--output-dir", default="output")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--max-pages", type=int, default=50)
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    print("Iniciando scraper unificado...", flush=True)
    print(f"Headless={not args.headed} | max_pages={args.max_pages}", flush=True)

    with sync_playwright() as p:
        print("Inicializando Chromium...", flush=True)
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            locale="es-PE",
        )
        page = context.new_page()
        page.set_default_timeout(5000)

        if args.input:
            df_in = pd.read_csv(args.input)
            urls = df_in["url"].dropna().astype(str).drop_duplicates().tolist()
            print(f"URLs cargadas desde CSV: {len(urls)}", flush=True)
        else:
            urls = discover_urls(page, args.max_pages)
            print(f"Total URLs descubiertas: {len(urls)}", flush=True)

        if args.limit > 0:
            urls = urls[:args.limit]
            print(f"Limit aplicado: {len(urls)}", flush=True)

        results = []
        total = len(urls)
        for idx, url in enumerate(urls, 1):
            print(f"[{idx:03d}/{total:03d}] {url}", flush=True)
            try:
                result = extract_product(page, url)
            except Exception as e:
                result = {
                    "url": url,
                    "product_name": "",
                    "seller": "",
                    "price_current": None,
                    "price_previous": None,
                    "price_discount_pct": None,
                    "miles_current": None,
                    "miles_previous": None,
                    "miles_per_sol": None,
                    "miles_discount_pct": None,
                    "miles_offer": "",
                    "offer_level": "",
                    "score": None,
                    "status": "ERROR",
                    "notes": str(e)[:300],
                    "captured_at": datetime.now().isoformat(timespec="seconds"),
                }
            results.append(result)

        browser.close()

    df = pd.DataFrame(results)
    df = df.sort_values(
        ["miles_offer", "score", "miles_per_sol"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)
    df.insert(0, "rank", range(1, len(df) + 1))

    best = df[(df["miles_per_sol"].notna()) & (df["miles_per_sol"] < 20)].copy()
    review = df[df["status"].isin(["PARTIAL", "ERROR"])].copy()

    # ... código anterior del dataframe ...
    df = df.sort_values(
        ["miles_offer", "score", "miles_per_sol"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)

    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        print("Conectando a PostgreSQL...", flush=True)
        # Adaptación del prefijo de conexión por si viene como 'postgres://'
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        engine = create_engine(db_url)
        # Guardamos en la tabla que creamos en Supabase
        df.to_sql("price_history", engine, if_exists="append", index=False)
        print(f"✅ {len(df)} registros guardados en PostgreSQL exitosamente.", flush=True)
    else:
        print("⚠️ No se encontró DATABASE_URL. El historial no se guardó en BD.", flush=True)

if __name__ == "__main__":
    main()