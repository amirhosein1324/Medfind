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


class AdminPharmacyResponse(PharmacyResponse):
    owner_name: str | None = None
    owner_email: str | None = None
    product_count: int = 0


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
    medicine_name: str | None = None
    medicine_detail: str | None = None


# ---------- Pharmacy update history (audit trail) ----------

class PharmacyUpdateHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    update_id: int
    product_id: int
    medicine_name: str
    old_price: Decimal | None
    new_price: Decimal | None
    old_status: str | None
    new_status: str | None
    old_stock: int | None
    new_stock: int | None
    updated_at: datetime


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
    # extra fields so the public UI can show a full pharmacy card
    medicine_detail: str | None = None
    generic_name: str | None = None
    phone: str | None = None
    website: str | None = None
    opening_hours: str | None = None
    is_verified: bool = False
    prescription_required: bool = False


# ---------- Web discovery ----------

class WebProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    title_en: str | None
    generic_en: str | None
    url: str
    source_domain: str
    price: Decimal | None
    currency: str | None
    availability: str
    image_url: str | None
    fetched_at: datetime


class OfferResponse(BaseModel):
    shop: str
    title: str
    price: Decimal | None
    currency: str | None
    availability: str
    url: str
    fetched_at: datetime


class ProductGroupResponse(BaseModel):
    key: str
    name: str
    title_fa: str | None = None
    generic: str | None = None
    image_url: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    currency: str | None = None
    shops: int
    available: int
    offers: list[OfferResponse]


class WebSearchResponse(BaseModel):
    enabled: bool
    items: list[WebProductResponse]
    groups: list[ProductGroupResponse] = []


class PricePointResponse(BaseModel):
    date: str
    min_price: float


class ProductPageResponse(ProductGroupResponse):
    history: list[PricePointResponse] = []


class CrawlSourceResponse(BaseModel):
    domain: str
    status: str
    detail: str | None = None
    urls_found: int = 0
    products_total: int = 0
    last_run: datetime | None = None
