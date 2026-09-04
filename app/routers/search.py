from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Medicine, MedicineAlias, Pharmacy, PharmacyProduct, SearchHistory
from ..schemas import SearchResponse, SearchResult
from ..rate_limit import limiter
from ..utils import haversine_km, relevance_sort_key

router = APIRouter()


@router.get("/", response_model=SearchResponse)
@limiter.limit("30/minute")
def search_medicine(
    request: Request,
    q: str = Query(..., min_length=2, max_length=100),
    latitude: float | None = None,
    longitude: float | None = None,
    max_distance_km: float | None = None,
    availability: str | None = None,
    sort: Literal["relevance", "distance", "price"] = "relevance",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Core MedFind search: matches medicine name / generic name / brand name /
    aliases (handles the "different pharmacies use different names" problem
    from the proposal), joins to live pharmacy listings, and ranks results.

    - Pass latitude & longitude to get distance-based filtering/sorting.
    - sort=relevance (default) ranks by availability then price.
    - sort=distance requires latitude & longitude.
    - sort=price sorts cheapest first (nulls last).
    """
    query = (
        db.query(
            PharmacyProduct.product_id,
            Medicine.medicine_id,
            Medicine.name.label("medicine_name"),
            Pharmacy.pharmacy_id,
            Pharmacy.name.label("pharmacy_name"),
            PharmacyProduct.price,
            PharmacyProduct.availability_status,
            PharmacyProduct.stock_quantity,
            PharmacyProduct.last_updated,
            Pharmacy.address,
            Pharmacy.latitude,
            Pharmacy.longitude,
        )
        .join(PharmacyProduct, Medicine.medicine_id == PharmacyProduct.medicine_id)
        .join(Pharmacy, PharmacyProduct.pharmacy_id == Pharmacy.pharmacy_id)
        .outerjoin(MedicineAlias, Medicine.medicine_id == MedicineAlias.medicine_id)
        .filter(
            or_(
                Medicine.name.ilike(f"%{q}%"),
                Medicine.generic_name.ilike(f"%{q}%"),
                Medicine.brand_name.ilike(f"%{q}%"),
                MedicineAlias.alias_name.ilike(f"%{q}%"),
            )
        )
        .filter(PharmacyProduct.is_active == True)  # noqa: E712
        .filter(Pharmacy.is_approved == True)  # noqa: E712
        .distinct()
    )

    if availability:
        query = query.filter(PharmacyProduct.availability_status == availability)

    rows = query.all()

    results: list[SearchResult] = []
    for r in rows:
        distance = haversine_km(latitude, longitude, r.latitude, r.longitude)

        if max_distance_km is not None and (
            distance is None or distance > max_distance_km
        ):
            continue

        results.append(
            SearchResult(
                product_id=r.product_id,
                medicine_id=r.medicine_id,
                medicine=r.medicine_name,
                pharmacy_id=r.pharmacy_id,
                pharmacy=r.pharmacy_name,
                price=r.price,
                availability=r.availability_status,
                stock_quantity=r.stock_quantity,
                last_updated=r.last_updated,
                address=r.address,
                latitude=float(r.latitude) if r.latitude is not None else None,
                longitude=float(r.longitude) if r.longitude is not None else None,
                distance_km=distance,
            )
        )

    if sort == "distance":
        results.sort(
            key=lambda x: (x.distance_km is None, x.distance_km or float("inf"))
        )
    elif sort == "price":
        results.sort(key=lambda x: (x.price is None, x.price or 0))
    else:  # relevance: availability first, then price, then freshness
        results.sort(key=relevance_sort_key)

    # Log the search for analytics/personalization, per the proposal's
    # search_history entity. Anonymous searches are logged with user_id=None.
    db.add(
        SearchHistory(
            search_query=q,
            medicine_id=results[0].medicine_id if results else None,
            latitude=latitude,
            longitude=longitude,
            sort_option=sort,
        )
    )
    db.commit()

    total = len(results)
    page = results[offset : offset + limit]

    return SearchResponse(total=total, limit=limit, offset=offset, results=page)
