import pytest
from metrics import canonical_url,product_id,is_good_offer,calc_change_pct,price_alert,failed_scrape_record

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
