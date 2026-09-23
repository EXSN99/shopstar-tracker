import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine

st.set_page_config(
    page_title='Shopstar Miles & Price Tracker',
    layout='wide',
    page_icon='🏷️',
)


@st.cache_data(ttl=3600)
def load_data():
    # 1. Intentar leer el secreto desde Streamlit Cloud
    try:
        db_url = st.secrets["DATABASE_URL"]
    except (KeyError, FileNotFoundError):
        # 2. Si falla, intentar leer de la variable de entorno local
        db_url = os.getenv('DATABASE_URL')

    if db_url:
        # 3. SQLAlchemy requiere el prefijo postgresql://
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        engine = create_engine(db_url)
        df = pd.read_sql('SELECT * FROM price_history', engine)
    else:
        df = pd.read_csv('output/shopstar_analysis.csv')

    df['captured_at'] = pd.to_datetime(df['captured_at'])
    return df


df = load_data()

st.title('🏷️ Tracker de Millas y Precios - Shopstar Perú')

# Métricas Principales
col1, col2, col3 = st.columns(3)
buenas_ofertas = df[df['miles_per_sol'] < 20]
latest_date = df['captured_at'].max()

col1.metric('Última Actualización', latest_date.strftime('%Y-%m-%d %H:%M'))
col2.metric('Total Productos Monitoreados', len(df['url'].unique()))
col3.metric('Buenas Ofertas Activas', len(buenas_ofertas))

# Pestañas de la aplicación
tab1, tab2 = st.tabs(['🔥 Mejores Ofertas', '📈 Historial por Producto'])

with tab1:
    st.subheader('Productos con mejor ratio Millas / Sol (< 20)')
    cols_show = [
        'product_name',
        'price_current',
        'miles_current',
        'miles_per_sol',
        'offer_level',
        'url',
    ]
    st.dataframe(
        buenas_ofertas[cols_show].sort_values('miles_per_sol'),
        use_container_width=True,
    )

with tab2:
    st.subheader('Evolución de Precio y Millas')
    selected_product = st.selectbox(
        'Selecciona un producto:', df['product_name'].unique()
    )

    prod_df = df[df['product_name'] == selected_product].sort_values(
        'captured_at'
    )

    fig_price = px.line(
        prod_df,
        x='captured_at',
        y='price_current',
        markers=True,
        title=f'Historial de Precio (S/) - {selected_product}',
    )
    st.plotly_chart(fig_price, use_container_width=True)

    fig_miles = px.line(
        prod_df,
        x='captured_at',
        y='miles_current',
        markers=True,
        title=f'Historial de Millas Requeridas - {selected_product}',
    )
    st.plotly_chart(fig_miles, use_container_width=True)
