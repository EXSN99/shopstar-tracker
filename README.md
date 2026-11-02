# 🛍️ Shopstar Tracker
### Radar de precios, millas y ofertas de Shopstar Perú

**¿Una promoción realmente conviene?** Shopstar Tracker permite explorar productos de la campaña **Bombas Millas**, comparar sus precios y millas requeridas, y consultar cómo han cambiado entre distintas capturas. Todo desde un tablero visual, sin revisar producto por producto manualmente.

<p align="center">
  <a href="https://shopstar-tracker-millas.streamlit.app/"><strong>🌐 Abrir tablero interactivo</strong></a>
  &nbsp;·&nbsp;
  <a href="#-guía-rápida">Guía rápida</a>
  &nbsp;·&nbsp;
  <a href="#-cómo-se-interpretan-los-indicadores">Entender los indicadores</a>
</p>

---

## ✨ ¿Qué puedes hacer?

| Funcionalidad | ¿Para qué sirve? |
|:--|:--|
| 🔎 **Explorar productos** | Consultar precios, millas, vendedores y enlaces directos a Shopstar. |
| 🏷️ **Identificar mejores ratios** | Ordenar los productos por **millas requeridas por sol** y aplicar los umbrales definidos para el proyecto. |
| 📈 **Seguir el histórico real** | Comparar precios y millas **observados en distintas extracciones**, no solo el descuento que muestra la tienda. |
| 🚩 **Detectar aumentos de precio** | Señalar productos cuyo precio actual supera en un 10 % o más el mínimo observado previamente en el periodo elegido. |
| 📊 **Explorar gráficos** | Visualizar distribuciones, comparaciones de productos y tendencias de captura. |
| ⬇️ **Exportar información** | Descargar el ranking y el histórico de un producto en formato CSV. |

> **Acceso a la aplicación:** https://shopstar-tracker-millas.streamlit.app/

## 🚀 Guía rápida

1. **Abre el [tablero interactivo](https://shopstar-tracker-millas.streamlit.app/).**
2. En el panel lateral, selecciona la **Fecha de captura**. Por defecto se muestra la más reciente.
3. Usa **Buscar producto o vendedor** para encontrar una marca o artículo específico.
4. Explora **📊 Panorama** para comparar precios y ratios de toda la captura.
5. Entra en **🏷️ Ranking y productos** para identificar los artículos con menor ratio y abrir sus fichas en Shopstar.
6. Selecciona un artículo en **📈 Historial de precios** para comprobar si su precio o cantidad de millas ha cambiado entre capturas.
7. Si necesitas analizar los datos fuera de la web, utiliza **Descargar ranking CSV** o **Exportar histórico del producto**.

**Consejo:** si activas *Solo buenas ofertas (≤20 millas/S/)* y no aparecen productos, no significa que el tablero esté vacío: significa que **ningún artículo de la selección actual cumple ese umbral**. Desactiva el filtro para ver todo el catálogo monitorizado.

## 🧭 Conoce las cuatro vistas

### 📊 1. Panorama: descubre patrones de un vistazo

La vista inicial contiene tres visualizaciones:

- **Precio vs. millas/S/**: cada punto representa un producto. El eje horizontal es su precio; el vertical muestra las millas requeridas por sol. **Cuanto más abajo esté el punto, menor es su ratio**. El tamaño del punto representa las millas requeridas.
- **Distribución de ratios**: agrupa los artículos por intervalos (≤16,7; 16,7–20; 20–30; 30–40; >40) para entender dónde se concentra la campaña.
- **Ranking visual de ratios**: presenta hasta 15 productos ordenados por el menor número de millas/S/.

La línea de referencia situada en **20 millas/S/** ayuda a identificar visualmente los productos dentro del objetivo configurado.

### 🏷️ 2. Ranking y productos: compara antes de decidir

La tabla permite revisar, por artículo:

| Campo | Significado |
|:--|:--|
| **Precio S/** | Precio actual extraído de Shopstar. |
| **Millas** | Millas requeridas que muestra el producto. |
| **Millas/S/** | Millas requeridas divididas entre el precio actual. **Menor es mejor**, según el criterio del tablero. |
| **Tachado S/** | Precio de referencia anunciado por Shopstar; **no es un dato histórico verificado**. |
| **Anterior observado S/** | Último precio válido capturado previamente para ese producto. |
| **Mínimo previo** | Menor precio observado anteriormente dentro de la ventana de días seleccionada. |
| **Cambio anterior % / Cambio mínimo %** | Variación porcentual respecto a esas referencias históricas. |
| **Categoría** | Clasificación basada en el ratio de millas/S/. |
| **Ver producto** | Acceso directo al enlace del artículo en Shopstar. |

Debajo de la tabla aparecen **fichas destacadas** con precio, millas y un enlace para abrir cada producto. Puedes descargar el ranking filtrado como CSV.

### 📈 3. Historial de precios: ¿subió o bajó?

Selecciona un producto para revisar:

- **Último precio**, **mínimo observado** y **cantidad de capturas disponibles**.
- Un gráfico con la evolución de su **precio real observado (S/)**.
- Un gráfico con la evolución de sus **millas requeridas**.
- Una tabla cronológica que puedes exportar a CSV.

Cada punto corresponde a una extracción registrada. Si el producto solo tiene una captura, **todavía no existe una tendencia suficiente para comparar**.

### 🧪 4. Ejecuciones: transparencia y calidad de datos

Esta vista muestra el estado de los registros (**OK**, **PARTIAL** o **ERROR**), la cantidad de productos que cuentan con una referencia histórica y la evolución del número de productos procesados y posibles buenas ofertas.

Sirve para distinguir entre **ausencia de una oferta** y **ausencia o insuficiencia de datos**.

## 🎛️ Filtros del panel lateral

| Control | Cómo usarlo |
|:--|:--|
| **Fecha de captura** | Permite comparar el estado del catálogo en una ejecución específica. |
| **Comparar con el mínimo observado de** | Elige una ventana de **7, 14, 30, 60 o 90 días** para calcular el mínimo histórico previo. |
| **Buscar producto o vendedor** | Filtra por palabras del nombre o del vendedor. |
| **Solo buenas ofertas (≤20 millas/S/)** | Muestra únicamente productos con estado OK cuyo ratio cumple el objetivo. |
| **Ocultar aumentos ≥10% vs mínimo** | Excluye artículos que presentan una subida de al menos 10 % sobre su mínimo observado previamente. |
| **Incluir extracciones parciales** | Permite revisar registros incompletos que normalmente quedan ocultos. |
| **Actualizar datos** | Fuerza la actualización de las consultas del tablero. |

## 🧮 Cómo se interpretan los indicadores

### Millas requeridas por sol

La métrica principal es:

$$
\text{Millas/S/} = \frac{\text{Millas requeridas}}{\text{Precio actual en soles}}
$$

**Ejemplo ilustrativo:** si un producto cuesta **S/ 200** y requiere **3.800 millas**, su ratio es **19 millas/S/**.

| Ratio | Clasificación del tablero |
|---:|:--|
| ≤ 16,7 | 🟢 Excelente |
| > 16,7 y ≤ 20 | 🟢 Buena |
| > 20 | ⚪ Fuera de objetivo |

Estos son **umbrales de análisis del proyecto**, no una calificación oficial de Shopstar ni una garantía de ahorro. La utilidad real de las millas depende de las condiciones del programa y de cada usuario.

### Aumento frente al mínimo observado

$$
\text{Variación (\%)} =
\left(\frac{\text{Precio actual}}{\text{Mínimo observado previo}}-1\right)\times100
$$

**Ejemplo ilustrativo:** si un producto llegó a **S/ 100** en capturas previas y ahora cuesta **S/ 115**, el tablero indica **+15 %** respecto a ese mínimo.

Una subida **no demuestra que exista un descuento engañoso**; es una señal para investigar. Si aún no existen observaciones anteriores dentro del periodo seleccionado, el mínimo y su variación pueden aparecer vacíos.

### Precio tachado ≠ precio histórico

- **Precio tachado:** valor publicitado en la ficha del producto.
- **Precio anterior observado:** última medición válida realizada por el tracker.
- **Mínimo observado:** menor medición válida previa en la ventana de días escogida.

La comparación basada en capturas reales es el valor central de este proyecto.

## 🔄 ¿Cada cuánto se actualiza?

El sistema tiene **dos extracciones diarias programadas**, aproximadamente a las **8:17 a. m. y 8:17 p. m. (hora de Lima)**. Los datos de cada ejecución se conservan para construir el histórico, y el dashboard permite seleccionar capturas anteriores.

Las ejecuciones pueden sufrir retrasos y el número de productos disponibles varía según la campaña. Por eso, **la fecha de captura seleccionada** es la referencia correcta para interpretar el contenido de cada gráfico.

## 💡 Casos de uso

**Caso A — Comparar alternativas.** Buscas una cafetera y ordenas los artículos por menor ratio de millas/S/; luego comparas precio y cantidad de millas antes de abrir la ficha original.

**Caso B — Validar una promoción.** Una freidora aparece rebajada. Revisas el **precio tachado**, pero sobre todo el **mínimo previo observado** y el gráfico de evolución para saber si su precio ya había sido más bajo.

**Caso C — Seguir un artículo.** Seleccionas el mismo producto en distintas capturas y compruebas cómo evolucionan sus precios y millas, sin depender de una única visita a la tienda.

## ℹ️ Alcance y limitaciones

- La información procede de **capturas periódicas**, no de un monitoreo en tiempo real. Puede haber cambios entre una captura y otra.
- El tablero se concentra en productos detectados en la campaña; **no representa necesariamente el catálogo completo** de Shopstar.
- Los registros incompletos se identifican para evitar tratarlos como ofertas verificadas.
- Los precios especiales condicionados a bancos, tarjetas, cupones u otros beneficios **no se calculan automáticamente**.
- Si Shopstar modifica la URL de un producto, su histórico podría aparecer dividido en más de una ficha.
- El tablero es un proyecto de análisis independiente; **no constituye una recomendación de compra ni una herramienta oficial de Shopstar**.

---

**[🌐 Explorar Shopstar Tracker](https://shopstar-tracker-millas.streamlit.app/)** · **[💻 Repositorio del proyecto](https://github.com/EXSN99/shopstar-tracker)**

<sub>Aplicación desarrollada con Python, Streamlit y PostgreSQL, con recopilación automatizada de datos. Proyecto independiente para análisis de precios y millas.</sub>
