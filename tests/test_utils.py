from datetime import datetime, timedelta
from types import SimpleNamespace

from app.utils import haversine_km, relevance_sort_key


def test_haversine_km_returns_none_for_missing_coords():
    assert haversine_km(None, 8.68, 50.11, 8.68) is None
    assert haversine_km(50.11, 8.68, None, 8.68) is None


def test_haversine_km_zero_for_identical_points():
    assert haversine_km(50.11, 8.68, 50.11, 8.68) == 0.0


def test_haversine_km_known_distance_frankfurt_to_london():
    # Frankfurt (~50.11, 8.68) to London (~51.5, -0.12) is roughly 600-650km.
    km = haversine_km(50.11, 8.68, 51.5, -0.12)
    assert 600 <= km <= 650


def _fake_result(availability, price, minutes_ago):
    return SimpleNamespace(
        availability=availability,
        price=price,
        last_updated=datetime.utcnow() - timedelta(minutes=minutes_ago),
    )


def test_relevance_sort_key_prefers_available_over_out_of_stock():
    available = _fake_result("available", 10.0, 5)
    out_of_stock = _fake_result("out_of_stock", 1.0, 1)
    assert relevance_sort_key(available) < relevance_sort_key(out_of_stock)


def test_relevance_sort_key_prefers_cheaper_within_same_availability():
    cheap = _fake_result("available", 2.0, 10)
    pricey = _fake_result("available", 20.0, 10)
    assert relevance_sort_key(cheap) < relevance_sort_key(pricey)


def test_relevance_sort_key_handles_missing_price():
    no_price = _fake_result("available", None, 5)
    has_price = _fake_result("available", 5.0, 5)
    assert relevance_sort_key(has_price) < relevance_sort_key(no_price)
