from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Medicine, Pharmacy, PharmacyProduct, PharmacyUpdate, User
from ..schemas import (
    AdminPharmacyResponse,
    PharmacyCreate,
    PharmacyProductCreate,
    PharmacyProductResponse,
    PharmacyProductUpdate,
    PharmacyResponse,
    PharmacyUpdateHistoryItem,
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


@router.get("/admin/all", response_model=list[AdminPharmacyResponse])
def admin_list_pharmacies(
    status: str | None = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """Every pharmacy with its owner and listing count. `status` may be
    'pending' or 'approved'. Powers the admin approval queue."""
    q = (
        db.query(Pharmacy, User, func.count(PharmacyProduct.product_id))
        .join(User, Pharmacy.owner_user_id == User.user_id)
        .outerjoin(PharmacyProduct, PharmacyProduct.pharmacy_id == Pharmacy.pharmacy_id)
        .group_by(Pharmacy.pharmacy_id, User.user_id)
        .order_by(Pharmacy.created_at.desc())
    )
    if status == "pending":
        q = q.filter(Pharmacy.is_approved == False)  # noqa: E712
    elif status == "approved":
        q = q.filter(Pharmacy.is_approved == True)  # noqa: E712

    out = []
    for pharmacy, owner, count in q.all():
        item = AdminPharmacyResponse.model_validate(pharmacy)
        item.owner_name = owner.full_name
        item.owner_email = owner.email
        item.product_count = count
        out.append(item)
    return out


@router.patch("/{pharmacy_id}/revoke", response_model=PharmacyResponse)
def revoke_pharmacy(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    """Take an approved pharmacy back out of public search."""
    pharmacy = db.query(Pharmacy).filter(Pharmacy.pharmacy_id == pharmacy_id).first()
    if not pharmacy:
        raise HTTPException(status_code=404, detail="Pharmacy not found")
    pharmacy.is_approved = False
    db.commit()
    db.refresh(pharmacy)
    return pharmacy


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


@router.post("/products/{product_id}/confirm", response_model=PharmacyProductResponse)
def confirm_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Say "this listing is still accurate" without changing any value.
    Refreshes last_updated (so the public freshness indicator resets) and
    records the confirmation in the audit trail."""
    product = (
        db.query(PharmacyProduct)
        .filter(PharmacyProduct.product_id == product_id)
        .first()
    )
    if not product:
        raise HTTPException(status_code=404, detail="Product listing not found")
    _get_owned_pharmacy(product.pharmacy_id, current_user, db)

    db.add(PharmacyUpdate(
        product_id=product.product_id,
        updated_by=current_user.user_id,
        old_price=product.price,
        new_price=product.price,
        old_status=product.availability_status,
        new_status=product.availability_status,
        old_stock=product.stock_quantity,
        new_stock=product.stock_quantity,
    ))
    product.last_updated = datetime.utcnow()
    db.commit()
    db.refresh(product)
    return product


@router.post("/{pharmacy_id}/confirm-all")
def confirm_all_products(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk version of confirm: marks every active listing of this pharmacy
    as just-verified. Does not write one audit row per listing."""
    _get_owned_pharmacy(pharmacy_id, current_user, db)
    now = datetime.utcnow()
    count = (
        db.query(PharmacyProduct)
        .filter(
            PharmacyProduct.pharmacy_id == pharmacy_id,
            PharmacyProduct.is_active == True,  # noqa: E712
        )
        .update({PharmacyProduct.last_updated: now}, synchronize_session=False)
    )
    db.commit()
    return {"confirmed": count, "confirmed_at": now.isoformat()}


@router.get(
    "/{pharmacy_id}/updates", response_model=list[PharmacyUpdateHistoryItem]
)
def list_pharmacy_update_history(
    pharmacy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recent price/stock/availability changes for this pharmacy's listings
    — the "view listing history" function from the project proposal.
    Owner or admin only, same as other pharmacy-management endpoints."""
    _get_owned_pharmacy(pharmacy_id, current_user, db)

    rows = (
        db.query(
            PharmacyUpdate.update_id,
            PharmacyUpdate.product_id,
            Medicine.name.label("medicine_name"),
            PharmacyUpdate.old_price,
            PharmacyUpdate.new_price,
            PharmacyUpdate.old_status,
            PharmacyUpdate.new_status,
            PharmacyUpdate.old_stock,
            PharmacyUpdate.new_stock,
            PharmacyUpdate.updated_at,
        )
        .join(PharmacyProduct, PharmacyUpdate.product_id == PharmacyProduct.product_id)
        .join(Medicine, PharmacyProduct.medicine_id == Medicine.medicine_id)
        .filter(PharmacyProduct.pharmacy_id == pharmacy_id)
        .order_by(PharmacyUpdate.updated_at.desc())
        .limit(50)
        .all()
    )
    return rows
