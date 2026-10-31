"""Dashboard de histórico de precios y millas: solo lectura de PostgreSQL."""
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from db import list_runs, comparison_for_run, product_history, runs_trend
from metrics import RATIO_UMBRAL, calc_change_pct

load_dotenv(".env.local", override=False)
load_dotenv(".env", override=False)

st.set_page_config(page_title="Shopstar | Observatorio de ofertas", page_icon="📉", layout="wide")
LIMA=ZoneInfo("America/Lima")

def db_url():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    try:
        return st.secrets.get("DATABASE_URL","")
    except (FileNotFoundError,KeyError):
        return ""

@st.cache_data(ttl=300,show_spinner=False)
def get_runs(url):
    return list_runs(url)

@st.cache_data(ttl=300,show_spinner=False)
def get_snapshot(url,run_id,days):
    return comparison_for_run(url,run_id,days)

@st.cache_data(ttl=300,show_spinner=False)
def get_history(url,pid):
    return product_history(url,pid)

@st.cache_data(ttl=300,show_spinner=False)
def get_trend(url):
    return runs_trend(url)

def lima_time(ts):
    return ts.astimezone(LIMA).strftime("%d/%m/%Y %H:%M") if isinstance(ts,datetime) else str(ts)

st.title("🛍️ Shopstar — observatorio de ofertas")
st.caption("Seguimiento de precios y millas · históricos en hora de Perú")
url=db_url()
if not url:
    st.error("Falta DATABASE_URL. Configúrala en los Secrets de Streamlit Community Cloud.")
    st.stop()
try:
    runs=get_runs(url)
except Exception:
    st.error("No se puede conectar a Neon/PostgreSQL o no existen las tablas. Ejecuta primero una extracción.")
    st.stop()
valid=[r for r in runs if r["status"] in ("COMPLETED","PARTIAL") and r["processed_count"]>0]
if not valid:
    st.info("Todavía no hay capturas exitosas. Configura DATABASE_URL en GitHub Actions y ejecuta el workflow.")
    st.stop()

with st.sidebar:
    st.header("Opciones")
    selected=st.selectbox("Captura",valid,format_func=lambda r: f"{lima_time(r['started_at'])} · {r['processed_count']} productos")
    days=st.select_slider("Histórico de referencia (días)",options=[7,14,30,60,90],value=30)
    only_good=st.checkbox("Solo buen ratio de millas",value=False)
    only_rising=st.checkbox("Solo precios que aumentaron ≥10%",value=False)
    exclude_rising=st.checkbox("Excluir precios que aumentaron ≥10%",value=False)
    search=st.text_input("Buscar producto o vendedor")
    st.button("Actualizar",on_click=st.cache_data.clear,use_container_width=True)

try:
    rows=get_snapshot(url,str(selected["run_id"]),days)
except Exception:
    st.error("Error consultando la captura seleccionada.")
    st.stop()
if not rows:
    st.warning("No hay registros para esta captura.")
    st.stop()
df=pd.DataFrame(rows)
for k in ("price_current","price_previous","miles_current","miles_previous","miles_per_sol",
          "observed_prior_price","observed_min_price"):
    df[k]=pd.to_numeric(df[k],errors="coerce")
df["variacion_anterior_%"]=df.apply(lambda r:calc_change_pct(r["price_current"],r["observed_prior_price"]),axis=1)
df["variacion_minimo_%"]=df.apply(lambda r:calc_change_pct(r["price_current"],r["observed_min_price"]),axis=1)
df["buen_ratio"]=df.status.eq("OK")&df.miles_per_sol.le(RATIO_UMBRAL)
df["subio_precio"]=df.status.eq("OK")&df["variacion_minimo_%"].ge(10)
c1,c2,c3,c4=st.columns(4)
c1.metric("Productos",len(df))
c2.metric("Extracciones OK",int(df.status.eq("OK").sum()))
c3.metric("Buen ratio",int(df.buen_ratio.sum()))
c4.metric("Precio ≥10% sobre mínimo",int(df.subio_precio.sum()))
st.caption(f"Captura {lima_time(selected['started_at'])}. El mínimo solo considera precios previos observados en {days} días.")

view=df.copy()
if only_good: view=view[view.buen_ratio]
if only_rising: view=view[view.subio_precio]
if exclude_rising: view=view[~view.subio_precio]
if search.strip():
    view=view[view.product_name.str.contains(search,case=False,regex=False,na=False) |
              view.seller.str.contains(search,case=False,regex=False,na=False)]
st.subheader("Comparación de ofertas")
cols={"product_name":"Producto","seller":"Vendedor","price_current":"Precio actual S/",
      "price_previous":"Precio tachado S/","miles_current":"Millas","miles_per_sol":"Millas/S/",
      "observed_prior_price":"Precio anterior S/","observed_min_price":"Mínimo observado S/",
      "variacion_anterior_%":"Cambio vs anterior %","variacion_minimo_%":"Cambio vs mínimo %",
      "buen_ratio":"Buen ratio","subio_precio":"Subió ≥10%","status":"Estado","url":"Producto (link)"}
if view.empty:
    st.info("Sin resultados para los filtros elegidos.")
else:
    table=view.sort_values(["buen_ratio","miles_per_sol"],ascending=[False,True],na_position="last")
    table=table[list(cols)].rename(columns=cols)
    st.dataframe(table,hide_index=True,use_container_width=True,
                 column_config={"Producto (link)":st.column_config.LinkColumn("Ver en Shopstar",display_text="Abrir")})
    st.download_button("Descargar CSV",table.to_csv(index=False).encode("utf-8-sig"),
                       "shopstar_ofertas.csv","text/csv")
st.divider()
st.subheader("Histórico de un producto")
options=df.sort_values("product_name").to_dict("records")
item=st.selectbox("Producto",options,format_func=lambda r:(r["product_name"] or "Sin nombre")+" · "+r["product_id"][:8])
try:
    history=get_history(url,item["product_id"])
except Exception:
    history=[]
if history:
    hist=pd.DataFrame(history).sort_values("captured_at")
    hist["captura_lima"]=hist.captured_at.apply(lambda dt:dt.astimezone(LIMA))
    for field in ("price_current","miles_current","miles_per_sol"):
        hist[field]=pd.to_numeric(hist[field],errors="coerce")
    left,right=st.columns(2)
    with left:
        st.markdown("**Precio observado (S/)**")
        st.line_chart(hist.set_index("captura_lima")["price_current"])
    with right:
        st.markdown("**Millas observadas**")
        st.line_chart(hist.set_index("captura_lima")["miles_current"])
    st.dataframe(hist[["captura_lima","price_current","miles_current","miles_per_sol","status"]]
                 .sort_values("captura_lima",ascending=False),hide_index=True,use_container_width=True)
    st.download_button("Exportar histórico",hist.to_csv(index=False).encode("utf-8-sig"),
                       "shopstar_historico.csv","text/csv")
    st.link_button("Abrir producto",item["url"])
st.divider()
st.subheader("Histórico de ejecuciones")
try:
    trend=get_trend(url)
    if trend:
        plot=pd.DataFrame(trend).sort_values("started_at")
        plot["fecha"]=plot.started_at.apply(lambda dt:dt.astimezone(LIMA))
        st.line_chart(plot.set_index("fecha")[["good_offers","processed"]])
except Exception:
    st.info("No se pudo consultar la evolución de ejecuciones.")
with st.expander("Calidad de extracción y supuestos"):
    st.dataframe(pd.DataFrame(runs),hide_index=True,use_container_width=True)
    st.markdown("**Precio tachado:** referencia anunciada por la tienda, no precio histórico. "
                "**Mínimo observado:** precio mínimo de capturas previas. "
                "**Aumento ≥10%:** indicador informativo; no demuestra manipulación. "
                "Los cambios de HTML pueden alterar los valores extraídos. "
                "Registros de error no cuentan como ofertas.")
