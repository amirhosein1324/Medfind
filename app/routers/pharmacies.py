from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Pharmacy, PharmacyProduct, PharmacyUpdate, User
from ..schemas import (
    PharmacyCreate,
    PharmacyProductCreate,
    PharmacyProductResponse,
    PharmacyProductUpdate,
    PharmacyResponse,
)
from ..security import get_current_user, require_role

router = APIRouter()


def _get_owned_pharmacy(pharmacy_id: int, current_user: User, db: Session) -> Pharmacy:
    """Fetch a pharmacy and verify the current user may manage it
    (its owner, or an admin). Raises 404/403 as appropriate."""
    pharmacy = db.query(Pharmacy).filter(Pharmacy.pharmacy_id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    if pharmacy.owner_user_id != current_user.user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=403, detail="You do not own this pharmacy"
        )
    return pharmacy


# ---------- Pharmacies ----------

@router.post("/", response_model=PharmacyResponse, status_code=201)
def create_pharmacy(
    pharmacy: PharmacyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("pharmacy_owner", "admin")),
):
    new_pharmacy = Pharmacy(owner_user_id=current_user.user_id, **pharmacy.model_dump())
    db.add(new_pharmacy)
    db.commit()
    db.refresh(new_pharmacy)
    return new_pharmacy


@router.get("/", response_model=list[PharmacyResponse])
def list_pharmacies(db: Session = Depends(get_db)):
    # Only approved pharmacies are publicly listed/searchable, per the
    # proposal's "Administrators approve pharmacies" requirement.
    return db.query(Pharmacy).filter(Pharmacy.is_approved == True).all()  # noqa: E712


@router.get("/mine", response_model=list[PharmacyResponse])
def list_my_pharmacies(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("pharmacy_owner", "admin")),
):
    return (
        db.query(Pharmacy)
        .filter(Pharmacy.owner_user_id == current_user.user_id)
        .all()
    )


@router.patch("/{pharmacy_id}/approve", response_model=PharmacyResponse)
def approve_pharmacy(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    pharmacy = db.query(Pharmacy).filter(Pharmacy.pharmacy_id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")

    pharmacy.is_approved = True
    db.commit()
    db.refresh(pharmacy)
    return pharmacy


# ---------- Pharmacy product listings ----------

@router.post(
    "/{pharmacy_id}/products", response_model=PharmacyProductResponse, status_code=201
)
def create_product(
    pharmacy_id: int,
    product: PharmacyProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_pharmacy(pharmacy_id, current_user, db)

    new_product = PharmacyProduct(pharmacy_id=pharmacy_id, **product.model_dump())
    db.add(new_product)
    db.commit()
    db.refresh(new_product)
    return new_product


@router.get("/{pharmacy_id}/products", response_model=list[PharmacyProductResponse])
def list_products(pharmacy_id: int, db: Session = Depends(get_db)):
    return (
        db.query(PharmacyProduct)
        .filter(
            PharmacyProduct.pharmacy_id == pharmacy_id,
            PharmacyProduct.is_active == True,  # noqa: E712
        )
        .all()
    )


@router.patch("/products/{product_id}", response_model=PharmacyProductResponse)
def update_product(
    product_id: int,
    changes: PharmacyProductUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update price/availability/stock for a listing. Only the owning
    pharmacy's account (or an admin) may do this, and every change is
    recorded in pharmacy_updates for the audit trail the proposal calls for."""
    product = (
        db.query(PharmacyProduct)
        .filter(PharmacyProduct.product_id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product listing not found")

    _get_owned_pharmacy(product.pharmacy_id, current_user, db)

    history = PharmacyUpdate(
        product_id=product.product_id,
        updated_by=current_user.user_id,
        old_price=product.price,
        new_price=changes.price if changes.price is not None else product.price,
        old_status=product.availability_status,
        new_status=changes.availability_status or product.availability_status,
        old_stock=product.stock_quantity,
        new_stock=(
            changes.stock_quantity
            if changes.stock_quantity is not None
            else product.stock_quantity
        ),
    )

    if changes.price is not None:
        product.price = changes.price
    if changes.availability_status is not None:
        product.availability_status = changes.availability_status
    if changes.stock_quantity is not None:
        product.stock_quantity = changes.stock_quantity

    db.add(history)
    db.commit()
    db.refresh(product)
    return product
