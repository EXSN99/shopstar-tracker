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

## Conectar el proyecto Neon existente (octubre 2026)

Los siguientes identificadores **no son contraseñas**, pero nunca publiques `DATABASE_URL`:

- Neon project: `shopstar-tracker`
- Organización: `org-small-frog-54927481`
- Project ID: `super-glade-87180589`
- Rama deseada en Neon: `production`

### Opción recomendada: usar la conexión del dashboard

1. En [Neon Console](https://console.neon.tech/), entra a `shopstar-tracker` y selecciona la rama **production**. Si aún no existe, créala primero (sin borrar la rama predeterminada).
2. Abre **Connect** y copia la cadena de conexión PostgreSQL con `sslmode=require`. Para el dashboard se recomienda la URL **pooled**; para operaciones de DDL/migración, Neon recomienda una conexión **directa**.
3. Guarda una URL adecuada para escribir y crear tablas en el secreto `DATABASE_URL` de **GitHub → Settings → Secrets and variables → Actions**.
4. Ve a **Actions → Verificar base de datos Neon → Run workflow**. Esto comprueba conectividad y permisos, crea las tres tablas si faltan, escribe en una tabla temporal y verifica lectura.
5. Una vez la prueba haya pasado, ve a **Actions → Extraer Shopstar**, ejecuta con `max_pages=2` y `limit=5`.
6. En Streamlit Community Cloud configura `DATABASE_URL` en los Secrets de la app. Idealmente utiliza un usuario PostgreSQL **solo lectura**, con permisos SELECT sobre las tres tablas. En esta app Streamlit no modifica datos.

### Opción CLI — las instrucciones que entregó Neon

Usa el terminal de tu equipo local, **dentro de la raíz del repositorio**:

```powershell
npm i -g neon@latest
neon init -y --org-id org-small-frog-54927481 --project-id super-glade-87180589 --branch production --services postgres
neon deploy
```

Si el CLI solicita autenticación web, finaliza el login en tu navegador. En caso de fallo puedes ejecutar `neon login` (o `neon auth` según la versión instalada). `neon deploy` solo es necesario para aplicar configuraciones declarativas de Neon; **PostgreSQL ya existe** en el proyecto creado en Neon. No añadimos una aplicación Node.js ni un `npm run build` ficticio.

`neon deploy` puede descargar `DATABASE_URL` en `.env.local`. El scraper y Streamlit local cargan ahora ese archivo con `python-dotenv`; `.env.local` y `.neon` están ignorados por Git.

Probar localmente después de `neon deploy`:

```powershell
pip install -r requirements-scraper.txt
python scripts/check_neon.py
python run_pipeline.py --max-pages 2 --limit 5
streamlit run streamlit_app.py
```

Para verificar **este proyecto Python**, usa `python -m pytest -q` y `python -m compileall -q .`. No existe `package.json`, por tanto `npm run build` no aplica.

Si tu red o la autenticación impiden instalar Neon CLI, configura `DATABASE_URL` desde Neon Console: no bloquea el despliegue de este scraper Python.

## Control de calidad de enlaces (31/10/2026)

Se auditó el archivo proporcionado `shopstar_analysis.xlsx`, 111 registros de la hoja `Analisis`.
Se identificaron **4 URLs que no son páginas de producto**: `/peds-millas`,
`/promociones`, `/politica-de-privacidad` y `/ps5?map=ft&_q=ps5`.
Dos de estas habían sido marcadas como `OK` porque el scraper analizaba el texto de
toda la página. Las restantes 107 URLs usan la ruta de ficha `/<slug>/p`.

**Corrección:** `metrics.is_product_url` y `canonical_url` exigen que la ruta
termine en `/p`. El descubrimiento filtra los enlaces antes de encolarlos; la
importación desde CSV pasa por el mismo filtro; la persistencia valida la URL
mediante `canonical_url`. Las URLs con parámetros de campaña se normalizan.
Si Shopstar cambia el patrón de rutas, será necesario revisar el filtro.

**Calidad de extracción:** si una URL se redirige a una página distinta de una
ficha de producto se descarta con un error. Si no se obtiene un nombre en `h1`,
el registro queda `PARTIAL`; no se clasificará erróneamente como `OK`.
Estas validaciones son estructurales, no garantizan por sí solas que el precio
pertenezca a un artículo cuando el sitio cambia su HTML.

Las 2 fichas legítimas `PARTIAL` en el Excel original **no se descartan por URL**:
se conservan para revisión de extracción.

## Dashboard visual y extracción completa

El dashboard desplegado en **https://shopstar-tracker-millas.streamlit.app/** dispone de
cuatro vistas: panorama de ratios y precios, ranking de productos, histórico por
producto y calidad de extracciones. Al actualizar la rama `main`, Streamlit
Community Cloud sincroniza los cambios y reinstala dependencias nuevas.

El workflow `Extraer Shopstar` se programa automáticamente **todos los días a
las 08:17 y 20:17 en Lima** (`America/Lima`). Cada ejecución programada usa
`max_pages=50` y `limit=0` (sin límite de productos). La concurrencia
`shopstar-extraccion` evita ejecuciones simultáneas, y los datos se agregan
por corrida en Neon PostgreSQL sin sobreescribir el histórico.

Una ejecución completa excepcional se puede iniciar creando o modificando
`ops/trigger-full-scrape.txt` en `main` (el único archivo que activa
`on.push.paths` en el workflow). Los cambios de código normales **no**
disparan una extracción. También puede iniciarse desde **Actions > Extraer
Shopstar > Run workflow**, con `max_pages=50`, `limit=0`.

Si el flujo falla tras procesar varios productos, los lotes confirmados
permanecen asociados a una corrida `FAILED`, nunca se presentan como un
escaneo completo. El dashboard solo selecciona corridas `COMPLETED` o
`PARTIAL`. GitHub Actions puede retrasar las ejecuciones programadas;
la hora indicada es el horario configurado, no una garantía de inicio exacto.
