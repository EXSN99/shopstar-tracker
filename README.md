# Shopstar Tracker — Streamlit + Neon PostgreSQL + GitHub Actions

Dashboard para monitorizar productos de la campaña Shopstar Bombas Millas y registrar sus cambios de precio y millas. Extrae datos con Playwright y los almacena de forma **persistente** en Neon PostgreSQL; la web Streamlit lee ese histórico.

**Repositorio:** https://github.com/EXSN99/shopstar-tracker

## Estructura

- `shopstar_scraper.py`: funciones de extracción usando Playwright.
- `run_pipeline.py`: orquestación, lotes, histórico y exportación CSV/Excel.
- `metrics.py`: URL canónica, ratios y comparación de precios.
- `db.py` + `schema.sql`: PostgreSQL y consultas de histórico.
- `streamlit_app.py`: dashboard, filtros, gráficos, exportación de resultados.
- `app.py`: compatibilidad con la entrada Streamlit previa.
- `.github/workflows/scrape.yml`: extracción programada (8:17 a. m. y 8:17 p. m. en Lima) y manual.
- `.github/workflows/tests.yml`: tests automáticos.

## Paso 1 — Crear base de datos gratuita

1. Crea un proyecto en https://console.neon.tech/
2. Copia la **Connection string** PostgreSQL (SSL habilitado). Debe comenzar con `postgresql://`.
3. En GitHub abre **Settings → Secrets and variables → Actions → New repository secret**.
4. Crea `DATABASE_URL` y pega la cadena *completa*. No guardes la contraseña en el código.

El esquema SQL se crea automáticamente en la primera extracción.

## Paso 2 — Probar extracción

En GitHub abre **Actions → Extraer Shopstar → Run workflow**. Selecciona `main`, usa:
- `max_pages=2`
- `limit=5`

Revisa el log y la descarga `shopstar-N` (CSV/Excel). Cuando todo funcione, ejecuta sin límite (`limit=0`). La programación recurrente está activada por el archivo YAML, pero **GitHub no garantiza exactitud en el minuto** y puede suspender ejecuciones por inactividad.

Si el workflow da error por cambios del DOM de Shopstar, revisa los selectores CSS en `shopstar_scraper.py`. No se han validado hoy contra el sitio real.

## Paso 3 — Desplegar web gratis

1. En https://share.streamlit.io crea una aplicación desde `EXSN99/shopstar-tracker`, rama `main`.
2. Elige **Main file path:** `streamlit_app.py` (también funciona `app.py`).
3. En **Advanced settings → Secrets**, configura TOML:
   ```toml
   DATABASE_URL = "postgresql://TU_USUARIO:TU_PASSWORD@TU_HOST.neon.tech/neondb?sslmode=require"
   ```
4. Publica la app. El historial aparecerá tras la primera extracción completa.

**Los secretos de GitHub y Streamlit se configuran por separado.** Recomendación: crea un usuario PostgreSQL de solo lectura para Streamlit cuando la extracción esté funcionando.

## Ejecutar localmente

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-scraper.txt
python -m playwright install chromium
$env:DATABASE_URL = 'postgresql://TU_CADENA_DE_NEON'
python run_pipeline.py --max-pages 2 --limit 5
streamlit run streamlit_app.py
```

Pruebas: `pip install pytest && python -m pytest -q`.

## Métricas y calidad

El ratio **millas / S/** considera buena oferta si es ≤ 20. El incremento significativo compara el precio actual contra el menor precio **observado anteriormente** dentro de la ventana seleccionada (7–90 días). El precio tachado anunciado por Shopstar no representa una medición histórica fiable. Una subida observada no demuestra engaño comercial.

Se registran capturas con estado `OK`, `PARTIAL` y `ERROR`; los errores no se convierten en precios cero. Las identidades se obtienen de la URL normalizada. Una URL nueva del mismo artículo podría verse como producto diferente.

El proceso secuencial puede tardar, generar errores o ser bloqueado por cambios del sitio; respeta los términos de acceso. No contiene bypass anti-bot ni manejo de precios especiales de tarjeta Interbank.

Referencias: [GitHub Actions](https://docs.github.com/en/actions/reference/events-that-trigger-workflows#schedule), [Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy), [Neon](https://neon.com/docs/get-started-with-neon/connect-neon).
