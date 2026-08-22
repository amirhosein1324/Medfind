"""Small shared helpers."""
from math import atan2, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0


def haversine_km(
    lat1: float | None, lon1: float | None, lat2: float | None, lon2: float | None
) -> float | None:
    """Great-circle distance in km between two lat/lon points.

    Returns None if either point is missing, so callers can distinguish
    "unknown distance" from "zero distance" (e.g. when ranking results).
    """
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        return None

    lat1_r, lon1_r, lat2_r, lon2_r = map(radians, (lat1, lon1, lat2, lon2))
    dlat = lat2_r - lat1_r
    dlon = lon2_r - lon1_r

    a = sin(dlat / 2) ** 2 + cos(lat1_r) * cos(lat2_r) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return round(EARTH_RADIUS_KM * c, 2)


# Availability ranks better than unknown/out-of-stock in default sort order.
AVAILABILITY_RANK = {
    "available": 0,
    "limited_stock": 1,
    "unknown": 2,
    "out_of_stock": 3,
}


def relevance_sort_key(result):
    """Sort key for default relevance ordering: availability, then price,
    then most-recently-updated first. Pulled out of the search router so it
    can be unit tested without spinning up the whole app/DB.
    """
    return (
        AVAILABILITY_RANK.get(result.availability, 9),
        result.price if result.price is not None else float("inf"),
        -result.last_updated.timestamp(),
    )
