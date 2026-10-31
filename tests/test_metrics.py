import pytest
from metrics import canonical_url, product_id, is_product_url, filter_product_urls, is_good_offer, calc_change_pct, price_alert, failed_scrape_record

def test_tracking_params_removed():
    a="https://shopstar.pe/product/p?utm_source=web#detalle"
    b="https://www.shopstar.pe/product/p/"
    assert canonical_url(a)==canonical_url(b)
    assert product_id(a)==product_id(b)

def test_reject_external_urls():
    with pytest.raises(ValueError):
        canonical_url("https://example.com/product/p")

def test_ratio_threshold():
    assert is_good_offer(20)
    assert not is_good_offer(20.01)
    assert not is_good_offer(None)

def test_historical_change():
    assert calc_change_pct(249,199)==pytest.approx(25.125628,abs=1e-5)
    assert price_alert(249,199)
    assert not price_alert(200,199)
    assert not price_alert(250,None)

def test_scrape_errors_are_not_prices():
    record=failed_scrape_record("https://www.shopstar.pe/product/p",RuntimeError("blocked"),"2026-10-30T12:00:00-05:00")
    assert record["status"]=="ERROR"
    assert record["price_current"] is None

# Regresión: cuatro falsos positivos encontrados en shopstar_analysis.xlsx (111 filas)
@pytest.mark.parametrize("url", [
    "https://www.shopstar.pe/peds-millas",
    "https://www.shopstar.pe/promociones",
    "https://www.shopstar.pe/politica-de-privacidad",
    "https://www.shopstar.pe/ps5?map=ft&_q=ps5",
    "https://www.shopstar.pe/categoria-productos?map=c",
    "https://otro-sitio.pe/perfume-123/p",
])
def test_reject_nonproduct_pages(url):
    assert not is_product_url(url)
    with pytest.raises(ValueError):
        canonical_url(url)

@pytest.mark.parametrize("url", [
    "https://www.shopstar.pe/mancuernas-set-de-30-kg-convertibles---barra---asas-16795874/p",
    "https://www.shopstar.pe/parlante-bluetooth-jbl-grip-azul-ip68-resistente-al-polvo-y-agua-903903-1204-1204/p",
    "https://www.shopstar.pe/ron-flor-de-cana-12-anos-botella-750ml/p",
    "https://shopstar.pe/mesa-plegable-viva-home-negra-180x74x74cm-1838629/p?utm_source=campaign",
])
def test_accept_real_product_url_patterns(url):
    assert is_product_url(url)
    assert canonical_url(url).endswith("/p")
    assert "?" not in canonical_url(url)

def test_url_list_removes_false_positives_and_duplicates():
    product = "https://www.shopstar.pe/hidrolavadora-electrolux-efficient-easywash-qws1650-16326717/p"
    accepted, rejected = filter_product_urls([
        "https://www.shopstar.pe/promociones",
        product + "?utm_source=x",
        "https://www.shopstar.pe/ps5?map=ft&_q=ps5",
        product,
    ])
    assert accepted == [product]
    assert len(rejected) == 2
