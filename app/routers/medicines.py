from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Medicine, MedicineAlias, MedicineCategory, User
from ..schemas import (
    CategoryCreate,
    CategoryResponse,
    MedicineAliasCreate,
    MedicineAliasResponse,
    MedicineCreate,
    MedicineResponse,
)
from ..security import require_role

router = APIRouter()


# ---------- Categories ----------

@router.post("/categories", response_model=CategoryResponse, status_code=201)
def create_category(
    category: CategoryCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    existing = db.query(MedicineCategory).filter(
        MedicineCategory.name == category.name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")

    new_category = MedicineCategory(**category.model_dump())
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(db: Session = Depends(get_db)):
    return db.query(MedicineCategory).all()


# ---------- Medicines ----------
# Creating/editing the medicine catalog is an admin function; browsing is public
# (matches the proposal: admins "manage medicine information", customers just search).

@router.post("/", response_model=MedicineResponse, status_code=201)
def create_medicine(
    medicine: MedicineCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    new_medicine = Medicine(**medicine.model_dump())
    db.add(new_medicine)
    db.commit()
    db.refresh(new_medicine)
    return new_medicine


@router.get("/", response_model=list[MedicineResponse])
def list_medicines(q: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Medicine)

    if q:
        query = query.filter(
            or_(
                Medicine.name.ilike(f"%{q}%"),
                Medicine.generic_name.ilike(f"%{q}%"),
                Medicine.brand_name.ilike(f"%{q}%"),
            )
        )

    return query.limit(50).all()


@router.get("/{medicine_id}", response_model=MedicineResponse)
def get_medicine(medicine_id: int, db: Session = Depends(get_db)):
    medicine = db.query(Medicine).filter(Medicine.medicine_id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")
    return medicine


# ---------- Aliases (handles "different names / spellings" from the proposal) ----------

@router.post(
    "/{medicine_id}/aliases", response_model=MedicineAliasResponse, status_code=201
)
def add_alias(
    medicine_id: int,
    alias: MedicineAliasCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_role("admin")),
):
    medicine = db.query(Medicine).filter(Medicine.medicine_id == medicine_id).first()
    if not medicine:
        raise HTTPException(status_code=404, detail="Medicine not found")

    new_alias = MedicineAlias(medicine_id=medicine_id, **alias.model_dump())
    db.add(new_alias)
    db.commit()
    db.refresh(new_alias)
    return new_alias


@router.get("/{medicine_id}/aliases", response_model=list[MedicineAliasResponse])
def list_aliases(medicine_id: int, db: Session = Depends(get_db)):
    return (
        db.query(MedicineAlias)
        .filter(MedicineAlias.medicine_id == medicine_id)
        .all()
    )
