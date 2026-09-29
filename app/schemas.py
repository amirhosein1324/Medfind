from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------- Auth ----------

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ---------- Users ----------

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    phone: str | None = None
    role: str = "customer"  # customer | pharmacy_owner  (admin is never self-assigned)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    full_name: str
    email: str
    phone: str | None
    role: str
    is_active: bool


# ---------- Medicine categories ----------

class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryResponse(CategoryCreate):
    model_config = ConfigDict(from_attributes=True)
    category_id: int


# ---------- Medicines ----------

class MedicineCreate(BaseModel):
    name: str
    generic_name: str | None = None
    brand_name: str | None = None
    manufacturer: str | None = None
    barcode: str | None = None
    dosage: str | None = None
    form: str | None = None
    package_size: str | None = None
    description: str | None = None
    prescription_required: bool = False
    category_id: int | None = None


class MedicineResponse(MedicineCreate):
    model_config = ConfigDict(from_attributes=True)

    medicine_id: int
    created_at: datetime


class MedicineAliasCreate(BaseModel):
    alias_name: str
    alias_type: str | None = None  # e.g. "brand", "misspelling", "local_name"


class MedicineAliasResponse(MedicineAliasCreate):
    model_config = ConfigDict(from_attributes=True)
    alias_id: int
    medicine_id: int


# ---------- Pharmacies ----------

class PharmacyCreate(BaseModel):
    name: str
    address: str
    latitude: float | None = None
    longitude: float | None = None
    phone: str | None = None
    website: str | None = None
    opening_hours: str | None = None


class PharmacyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pharmacy_id: int
    owner_user_id: int
    name: str
    address: str
    latitude: float | None
    longitude: float | None
    phone: str | None
    website: str | None
    opening_hours: str | None
    is_verified: bool
    is_approved: bool
    created_at: datetime


# ---------- Pharmacy products (listings) ----------

class PharmacyProductCreate(BaseModel):
    medicine_id: int
    price: Decimal | None = None
    package_size: str | None = None
    availability_status: str = "unknown"
    stock_quantity: int | None = None
    product_url: str | None = None


class PharmacyProductUpdate(BaseModel):
    price: float | None = None
    availability_status: str | None = None
    stock_quantity: int | None = None


class PharmacyProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    pharmacy_id: int
    medicine_id: int
    price: Decimal | None
    package_size: str | None
    availability_status: str
    stock_quantity: int | None
    last_updated: datetime
    product_url: str | None
    is_active: bool


# ---------- Search ----------

class SearchResult(BaseModel):
    product_id: int
    medicine_id: int
    medicine: str
    pharmacy_id: int
    pharmacy: str
    price: Decimal | None
    availability: str
    stock_quantity: int | None
    last_updated: datetime
    address: str
    latitude: float | None
    longitude: float | None
    distance_km: float | None = None
<<<<<<< HEAD
=======


class SearchResponse(BaseModel):
    total: int
    limit: int
    offset: int
    results: list[SearchResult]
>>>>>>> d9330aae4fcad9dcf5b77c3caff219517d5546fa
