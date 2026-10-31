"""GitHub Actions: extraer, guardar historial persistente y exportar respaldo."""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import pandas as pd
from playwright.sync_api import sync_playwright
from db import finish_run, init_db, save_batch, start_run
from metrics import canonical_url, failed_scrape_record
from shopstar_scraper import discover_urls, extract_product

COLUMNS = ["url","product_name","seller","price_current","price_previous","price_discount_pct",
           "miles_current","miles_previous","miles_per_sol","miles_discount_pct","miles_offer",
           "offer_level","score","status","notes","captured_at"]

def write_exports(records,output_dir):
    out=Path(output_dir)
    out.mkdir(parents=True,exist_ok=True)
    df=pd.DataFrame(records,columns=COLUMNS).sort_values(
        ["miles_offer","score","miles_per_sol"],ascending=[False,False,True],na_position="last"
    ).reset_index(drop=True)
    df.insert(0,"rank",range(1,len(df)+1))
    df.to_csv(out/"shopstar_analysis.csv",index=False,encoding="utf-8-sig")
    with pd.ExcelWriter(out/"shopstar_analysis.xlsx",engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="Analisis")
        df[df.miles_per_sol.le(20)&df.status.eq("OK")].to_excel(writer,index=False,sheet_name="Mejores_Millas")
        df[df.status.isin(["PARTIAL","ERROR"])].to_excel(writer,index=False,sheet_name="Revisar")

def run(args,db_url):
    init_db(db_url)
    run_id=start_run(db_url)
    discovered=0
    records=[]
    pending=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            try:
                context=browser.new_context(viewport={"width":1440,"height":1000},
                                            locale="es-PE",timezone_id="America/Lima")
                page=context.new_page()
                page.set_default_timeout(5000)
                if args.input:
                    df_in=pd.read_csv(args.input)
                    if "url" not in df_in.columns:
                        raise ValueError("El CSV de entrada requiere columna url")
                    urls=df_in.url.dropna().astype(str).tolist()
                else:
                    urls=discover_urls(page,args.max_pages)
                urls=list(dict.fromkeys(canonical_url(u) for u in urls))
                discovered=len(urls)
                if args.limit>0:
                    urls=urls[:args.limit]
                if not urls:
                    raise RuntimeError("No se descubrieron URLs, se evita una corrida vacía")
                print(f"Run ID: {run_id} | URLs descubiertas: {discovered} | a procesar: {len(urls)}",flush=True)
                for i,url in enumerate(urls,1):
                    print(f"[{i}/{len(urls)}] {url}",flush=True)
                    try:
                        item=extract_product(page,url)
                    except Exception as exc:
                        item=failed_scrape_record(url,exc,datetime.now(ZoneInfo("America/Lima")).isoformat(timespec="seconds"))
                        print(f"ERROR: {item['notes']}",flush=True)
                    captured=item.get("captured_at")
                    if captured:
                        dt=datetime.fromisoformat(captured)
                        if dt.tzinfo is None:
                            dt=dt.replace(tzinfo=ZoneInfo("America/Lima"))
                        item["captured_at"]=dt.isoformat(timespec="seconds")
                    records.append(item)
                    pending.append(item)
                    if len(pending)>=args.batch_size:
                        save_batch(db_url,run_id,pending)
                        pending=[]
                if pending:
                    save_batch(db_url,run_id,pending)
            finally:
                browser.close()
        write_exports(records,args.output_dir)
        if not any(x["status"]=="OK" for x in records):
            status="FAILED"
        elif any(x["status"]!="OK" for x in records):
            status="PARTIAL"
        else:
            status="COMPLETED"
        finish_run(db_url,run_id,status,discovered)
        print(f"Finalizado {status}; {len(records)} productos; run_id={run_id}",flush=True)
        if status=="FAILED":
            raise RuntimeError("No se obtuvo ningún producto completo; revisar selectores o bloqueos")
    except Exception as exc:
        try:
            finish_run(db_url,run_id,"FAILED",discovered,f"{type(exc).__name__}: {str(exc)[:400]}")
        except Exception:
            print("No se pudo actualizar el estado de fallo en PostgreSQL",file=sys.stderr)
        raise

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--max-pages",type=int,default=50)
    ap.add_argument("--limit",type=int,default=0)
    ap.add_argument("--batch-size",type=int,default=20)
    ap.add_argument("--input",default="")
    ap.add_argument("--output-dir",default="output")
    args=ap.parse_args()
    if args.batch_size<1 or args.max_pages<1 or args.limit<0:
        ap.error("Parámetros fuera de rango")
    load_dotenv(".env.local", override=False)
    load_dotenv(".env", override=False)
    db_url=os.getenv("DATABASE_URL","")
    if not db_url:
        ap.error("Falta DATABASE_URL en el entorno")
    run(args,db_url)

if __name__=="__main__":
    main()
