"""Shopstar | Panel visual de precios, millas y calidad de ofertas."""
from datetime import datetime
from zoneinfo import ZoneInfo
import os

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from db import comparison_for_run, list_runs, product_history, runs_trend
from metrics import RATIO_UMBRAL, calc_change_pct

load_dotenv(".env.local", override=False)
load_dotenv(".env", override=False)
st.set_page_config(page_title="Shopstar · Radar de ofertas", page_icon="🛍️", layout="wide", initial_sidebar_state="expanded")
LIMA = ZoneInfo("America/Lima")
GOOD = "#13A89E"
WARNING = "#DF9447"
NEUTRAL = "#66758F"
DANGER = "#D65960"
PRIMARY = "#4967CE"
IDEAL_RATIO = 16.7

st.markdown("""
<style>
.block-container {padding-top: 1.6rem; max-width: 1500px;}
div[data-testid="stMetric"] {border:1px solid rgba(130,144,170,.18); border-radius:13px; padding:12px 16px; background:rgba(140,150,180,.035);}
div[data-testid="stMetricLabel"] {font-size:.87rem;}
div[data-testid="stMetricValue"] {font-size:1.7rem;}
</style>
""", unsafe_allow_html=True)


def connection_url():
    # No mostrar la cadena ni incluirla en logs.
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    try:
        return st.secrets.get("DATABASE_URL", "")
    except (FileNotFoundError, KeyError):
        return ""


@st.cache_data(ttl=300, show_spinner=False)
def fetch_runs(url):
    return list_runs(url)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_snapshot(url, run_id, days):
    return comparison_for_run(url, run_id, days)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_product_history(url, product_id):
    return product_history(url, product_id)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_run_trend(url):
    return runs_trend(url)


def local_time(value):
    if value is None or pd.isna(value):
        return "—"
    return value.astimezone(LIMA).strftime("%d/%m/%Y %H:%M")


def money(value):
    return f"S/ {value:,.2f}" if pd.notna(value) else "—"


def integer(value):
    return f"{value:,.0f}" if pd.notna(value) else "—"


def short_label(value, length=57):
    value = str(value or "Sin nombre")
    return value if len(value) <= length else value[:length-1] + "…"


def chart_layout(fig, height=390, ytitle=None, xtitle=None):
    fig.update_layout(
        template="plotly_white", height=height,
        margin=dict(l=5, r=12, t=20, b=15),
        font=dict(family="sans-serif", size=12),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
        plot_bgcolor="rgba(0,0,0,0)",
    )
    if ytitle is not None:
        fig.update_yaxes(title_text=ytitle, gridcolor="#E9EDF3", zeroline=False)
    if xtitle is not None:
        fig.update_xaxes(title_text=xtitle, gridcolor="#E9EDF3", zeroline=False)
    return fig


st.title("🛍️ Shopstar | Radar de ofertas")
st.caption("Precios reales observados, puntos/millas de campaña y señales de inflación de precios · Perú")

url = connection_url()
if not url:
    st.error("Falta configurar DATABASE_URL en los Secrets de la aplicación Streamlit.")
    st.stop()

try:
    runs = fetch_runs(url)
except Exception:
    st.error("No se pudieron obtener las ejecuciones de PostgreSQL. Comprueba los Secrets, permisos y conexión a Neon.")
    st.stop()

valid_runs = [r for r in runs if r["status"] in ("COMPLETED", "PARTIAL") and r["processed_count"]]
if not valid_runs:
    st.info("Aún no hay una captura de productos completa. Ejecuta Extraer Shopstar desde GitHub Actions.")
    st.stop()

with st.sidebar:
    st.header("🔎 Filtros")
    selected = st.selectbox(
        "Fecha de captura", valid_runs,
        format_func=lambda r: f"{local_time(r['started_at'])} · {r['processed_count']} productos",
    )
    window = st.select_slider("Comparar con el mínimo observado de", [7, 14, 30, 60, 90], value=30,
                              format_func=lambda value: f"{value} días")
    search = st.text_input("Buscar producto o vendedor", placeholder="Electrolux, Oster, JBL…")
    sellers = []
    only_good = st.toggle("Solo buenas ofertas (≤20 millas/S/)", value=False)
    hide_rising = st.toggle("Ocultar aumentos ≥10% vs mínimo", value=False)
    include_partial = st.toggle("Incluir extracciones parciales", value=False)
    if st.button("↻ Actualizar datos", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Extracción automática: 08:17 y 20:17 (America/Lima). Los gráficos se actualizan al existir nuevas capturas.")

try:
    records = fetch_snapshot(url, str(selected["run_id"]), window)
except Exception:
    st.error("No fue posible consultar la captura seleccionada.")
    st.stop()
if not records:
    st.warning("La captura elegida no contiene registros.")
    st.stop()

df = pd.DataFrame(records)
numeric = ["price_current", "price_previous", "miles_current", "miles_previous",
           "miles_per_sol", "observed_prior_price", "observed_prior_miles",
           "observed_min_price", "historical_observations"]
for field in numeric:
    df[field] = pd.to_numeric(df[field], errors="coerce")
df["change_previous_pct"] = [
    calc_change_pct(price, old)
    for price, old in zip(df["price_current"], df["observed_prior_price"])
]
df["change_minimum_pct"] = [
    calc_change_pct(price, old)
    for price, old in zip(df["price_current"], df["observed_min_price"])
]
df["good_offer"] = df["status"].eq("OK") & df["miles_per_sol"].le(RATIO_UMBRAL)
df["price_increase"] = df["status"].eq("OK") & df["change_minimum_pct"].ge(10)
df["quality"] = df["miles_per_sol"].apply(
    lambda x: "Excelente ≤16,7" if pd.notna(x) and x <= IDEAL_RATIO
    else ("Buena ≤20" if pd.notna(x) and x <= RATIO_UMBRAL else "Fuera de objetivo")
)
df["quality"] = df["quality"].where(df["status"].eq("OK"), "Revisar")

filtered = df if include_partial else df[df["status"].eq("OK")]
if search.strip():
    needle = search.strip()
    filtered = filtered[
        filtered["product_name"].str.contains(needle, case=False, regex=False, na=False)
        | filtered["seller"].str.contains(needle, case=False, regex=False, na=False)
    ]
if only_good:
    filtered = filtered[filtered["good_offer"]]
if hide_rising:
    filtered = filtered[~filtered["price_increase"]]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Productos de la captura", len(df))
k2.metric("Ofertas ≤20", int(df["good_offer"].sum()))
k3.metric("Precio mediano", money(df.loc[df.status.eq("OK"), "price_current"].median()))
k4.metric("Con aumento ≥10%", int(df["price_increase"].sum()))
k5.metric("Registros parciales", int(df.status.eq("PARTIAL").sum()))
st.caption(
    f"Última captura seleccionada: **{local_time(selected['started_at'])} (Lima)** · "
    f"**{len(filtered)}** productos tras filtros · "
    f"Umbral bueno: **≤{RATIO_UMBRAL:g} millas/S/** (menos es mejor)."
)
if len(valid_runs) == 1:
    st.info("Ya hay datos reales, pero solo una medición por producto. Las comparaciones históricas se habilitan al acumular capturas.")
if filtered.empty:
    st.warning("Ningún producto cumple estos filtros. Desactiva el filtro de buenas ofertas o amplía la búsqueda.")

tab_overview, tab_offers, tab_history, tab_quality = st.tabs([
    "📊 Panorama", "🏷️ Ranking y productos", "📈 Historial de precios", "🧪 Ejecuciones"
])

with tab_overview:
    left, right = st.columns([1.4, 1])
    with left:
        st.subheader("Relación entre precio y millas/S/")
        scatter = filtered[(filtered["status"] == "OK") & filtered["price_current"].notna()
                           & filtered["miles_per_sol"].notna() & filtered["miles_current"].gt(0)].copy()
        if scatter.empty:
            st.info("No hay productos con precio y millas válidos para el gráfico.")
        else:
            scatter["Clasificación"] = scatter["good_offer"].map({True: "Buena ≤20", False: "Fuera de objetivo"})
            scatter["Nombre"] = scatter["product_name"].fillna("").map(lambda x: short_label(x, 80))
            fig = px.scatter(
                scatter, x="price_current", y="miles_per_sol", size="miles_current",
                color="Clasificación", hover_name="Nombre",
                hover_data={"price_current":":.2f", "miles_per_sol":":.2f", "miles_current":":.0f"},
                color_discrete_map={"Buena ≤20": GOOD, "Fuera de objetivo": NEUTRAL},
                size_max=28,
            )
            fig.add_hline(y=RATIO_UMBRAL, line_dash="dash", line_color=GOOD,
                          annotation_text="Umbral 20", annotation_position="top right")
            chart_layout(fig, ytitle="Millas por S/ (menor es mejor)", xtitle="Precio actual S/")
            st.plotly_chart(fig, use_container_width=True, key="price_vs_miles")
    with right:
        st.subheader("Distribución de ratios")
        valid_ratios = filtered[(filtered.status == "OK") & filtered.miles_per_sol.notna()].copy()
        if valid_ratios.empty:
            st.info("Sin ratios válidos.")
        else:
            bins = [-float("inf"), IDEAL_RATIO, RATIO_UMBRAL, 30, 40, float("inf")]
            labels = ["≤16,7", "16,7–20", "20–30", "30–40", ">40"]
            valid_ratios["Rango"] = pd.cut(valid_ratios.miles_per_sol, bins=bins, labels=labels)
            counts = valid_ratios["Rango"].value_counts(sort=False).reindex(labels, fill_value=0)
            fig = go.Figure(go.Bar(
                x=counts.index.astype(str), y=counts.values,
                marker_color=[GOOD, "#66BDB3", "#8A96B1", WARNING, DANGER],
                text=counts.values, textposition="outside",
                hovertemplate="%{x}: %{y} productos<extra></extra>"
            ))
            chart_layout(fig, ytitle="Productos", xtitle="Millas / S/")
            st.plotly_chart(fig, use_container_width=True, key="ratio_bins")
    st.subheader("Menor ratio = mejor relación de millas y precio")
    top = filtered[(filtered.status == "OK") & filtered.miles_per_sol.notna()].nsmallest(15, "miles_per_sol").copy()
    if not top.empty:
        top["Producto"] = top.product_name.map(lambda x: short_label(x, 45))
        top["Clasificación"] = top.good_offer.map({True: "≤20", False: ">20"})
        top = top.sort_values("miles_per_sol", ascending=False)
        fig = px.bar(top, x="miles_per_sol", y="Producto", color="Clasificación",
                     orientation="h", text="miles_per_sol",
                     color_discrete_map={"≤20": GOOD, ">20": NEUTRAL},
                     hover_data=["price_current", "miles_current"])
        fig.update_traces(texttemplate="%{text:.2f}", textposition="outside", cliponaxis=False)
        fig.add_vline(x=RATIO_UMBRAL, line_dash="dash", line_color=GOOD)
        chart_layout(fig, height=max(330, min(680, len(top) * 35 + 90)), xtitle="Millas por S/", ytitle="")
        st.plotly_chart(fig, use_container_width=True, key="top_ratio")

with tab_offers:
    st.subheader("Productos monitorizados")
    st.caption("El ranking utiliza la última captura seleccionada. Los precios tachados son valores anunciados por la tienda, no mediciones históricas.")
    ranking = filtered.sort_values("miles_per_sol", ascending=True, na_position="last")
    if not ranking.empty:
        show_columns = {
            "product_name": "Producto", "seller": "Vendedor", "price_current": "Precio S/",
            "miles_current": "Millas", "miles_per_sol": "Millas/S/",
            "price_previous": "Tachado S/", "observed_prior_price": "Anterior observado S/",
            "observed_min_price": f"Mínimo previo {window}d S/",
            "change_previous_pct": "Cambio anterior %", "change_minimum_pct": "Cambio mínimo %",
            "quality": "Categoría", "status": "Estado", "url": "Enlace",
        }
        st.dataframe(
            ranking[list(show_columns)].rename(columns=show_columns),
            use_container_width=True, hide_index=True,
            column_config={
                "Enlace": st.column_config.LinkColumn("Ver producto", display_text="Abrir"),
                "Precio S/": st.column_config.NumberColumn(format="S/ %.2f"),
                "Millas/S/": st.column_config.NumberColumn(format="%.2f"),
                "Cambio mínimo %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )
        st.download_button("⬇️ Descargar ranking CSV",
                           ranking[list(show_columns)].rename(columns=show_columns)
                           .to_csv(index=False).encode("utf-8-sig"),
                           file_name="shopstar_ranking.csv", mime="text/csv")
        st.divider()
        st.subheader("Fichas destacadas")
        for _, r in ranking.head(12).iterrows():
            with st.container(border=True):
                body, detail, action = st.columns([3.3, 1.6, 1.1])
                with body:
                    st.markdown(f"**{r['product_name'] or 'Producto sin nombre'}**")
                    st.caption(r["seller"] or "Vendedor no indicado")
                    st.caption("🟢 Buen ratio" if r["good_offer"] else "⚪ Fuera de objetivo")
                with detail:
                    st.markdown(f"**{money(r['price_current'])}**")
                    st.caption(f"{integer(r['miles_current'])} millas · {r['miles_per_sol']:.2f} millas/S/" if pd.notna(r["miles_per_sol"]) else "Ratio no disponible")
                with action:
                    st.link_button("Ver producto", r["url"], use_container_width=True)

with tab_history:
    st.subheader("Evolución real por producto")
    st.caption("Cada punto procede de una extracción. Se diferencia del precio tachado publicado en Shopstar.")
    options = df.sort_values("product_name").to_dict("records")
    item = st.selectbox("Selecciona un producto", options,
                        format_func=lambda r: f"{short_label(r['product_name'], 80)} · {r['product_id'][:8]}")
    try:
        history = fetch_product_history(url, item["product_id"])
    except Exception:
        st.error("No se pudo consultar el histórico de este producto.")
        history = []
    if history:
        hist = pd.DataFrame(history).sort_values("captured_at")
        hist["time"] = pd.to_datetime(hist.captured_at, utc=True).dt.tz_convert("America/Lima")
        for field in ["price_current", "miles_current", "miles_per_sol"]:
            hist[field] = pd.to_numeric(hist[field], errors="coerce")
        c1, c2, c3 = st.columns(3)
        last = hist.iloc[-1]
        previous = hist.iloc[-2] if len(hist) > 1 else None
        delta = calc_change_pct(last.price_current, previous.price_current) if previous is not None else None
        c1.metric("Último precio", money(last.price_current),
                  delta=f"{delta:+.1f}%" if delta is not None else None, delta_color="inverse")
        c2.metric("Mínimo observado", money(hist.price_current.min()))
        c3.metric("Capturas", len(hist))
        if len(hist) < 2:
            st.info("Solo existe una captura de este producto. Los gráficos cobrarán sentido después de la próxima ejecución.")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown("**Precio actual observado (S/)**")
            fig = px.line(hist, x="time", y="price_current", markers=True)
            chart_layout(fig, ytitle="Precio S/", xtitle="Captura (Lima)")
            st.plotly_chart(fig, use_container_width=True, key="historical_price")
        with p2:
            st.markdown("**Millas y puntos requeridos**")
            fig = px.line(hist, x="time", y="miles_current", markers=True)
            chart_layout(fig, ytitle="Millas", xtitle="Captura (Lima)")
            st.plotly_chart(fig, use_container_width=True, key="historical_miles")
        st.dataframe(hist[["time", "price_current", "miles_current", "miles_per_sol", "status"]]
                     .sort_values("time", ascending=False), hide_index=True, use_container_width=True)
        c1, c2 = st.columns([1, 1])
        with c1:
            st.download_button("⬇️ Exportar histórico del producto",
                               hist.to_csv(index=False).encode("utf-8-sig"),
                               "shopstar_historial_producto.csv", "text/csv")
        with c2:
            st.link_button("🔗 Abrir producto en Shopstar", item["url"])

with tab_quality:
    st.subheader("Salud de las extracciones")
    status_counts = pd.DataFrame([
        {"Estado": "OK", "Total": int((df.status == "OK").sum())},
        {"Estado": "PARTIAL", "Total": int((df.status == "PARTIAL").sum())},
        {"Estado": "ERROR", "Total": int((df.status == "ERROR").sum())},
    ])
    lc, rc = st.columns([1, 1])
    with lc:
        fig = px.pie(status_counts, names="Estado", values="Total", hole=.65,
                     color="Estado", color_discrete_map={"OK": GOOD, "PARTIAL": WARNING, "ERROR": DANGER})
        chart_layout(fig, 340)
        st.plotly_chart(fig, use_container_width=True, key="quality_pie")
    with rc:
        st.metric("Ejecuciones completas o parciales", len(valid_runs))
        st.metric("Productos con referencia histórica", int(df["observed_prior_price"].notna().sum()))
        st.metric("Productos con alerta de aumento", int(df["price_increase"].sum()))
        if df["observed_prior_price"].isna().all():
            st.info("No existen precios anteriores para esta captura. Esto es normal en la primera ejecución.")
    try:
        trend_rows = fetch_run_trend(url)
    except Exception:
        trend_rows = []
    if trend_rows:
        trend = pd.DataFrame(trend_rows).sort_values("started_at")
        trend["time"] = pd.to_datetime(trend.started_at, utc=True).dt.tz_convert("America/Lima")
        for field in ("good_offers", "processed", "full_records"):
            trend[field] = pd.to_numeric(trend[field], errors="coerce")
        st.subheader("Tendencia de productos procesados y buenas ofertas")
        fig = px.line(trend, x="time", y=["processed", "good_offers"], markers=True,
                      labels={"value": "Cantidad", "time": "Captura", "variable": "Métrica"})
        chart_layout(fig, ytitle="Cantidad", xtitle="Fecha (Lima)")
        st.plotly_chart(fig, use_container_width=True, key="runs_trend")
    runs_frame = pd.DataFrame(runs)
    if not runs_frame.empty:
        st.dataframe(runs_frame, hide_index=True, use_container_width=True)
    with st.expander("Definiciones y limitaciones"):
        st.markdown(
            "- **Millas/S/**: millas requeridas divididas por el precio actual. Menos es mejor; ≤20 es el umbral configurado.\n"
            "- **Mínimo observado**: menor precio en capturas anteriores dentro del periodo escogido; no equivale al precio tachado.\n"
            "- **Aumento ≥10%**: precio actual al menos 10% sobre el mínimo observado; una señal para investigar, no una acusación.\n"
            "- **PARTIAL/ERROR**: capturas incompletas o fallidas; no se incluyen como buenas ofertas.\n"
            "- **Historias**: productos identificados por URL normalizada. Cambios de URL pueden fragmentar su evolución."
        )
