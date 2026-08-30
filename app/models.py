from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    String,
    Text,
    Integer,
    Boolean,
    DateTime,
    Numeric,
    ForeignKey,
    Enum,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[str] = mapped_column(
        Enum("customer", "pharmacy_owner", "admin", name="user_role"),
        default="customer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    pharmacies = relationship("Pharmacy", back_populates="owner")
    searches = relationship("SearchHistory", back_populates="user")
    updates = relationship("PharmacyUpdate", back_populates="updater")


class MedicineCategory(Base):
    __tablename__ = "medicine_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    medicines = relationship("Medicine", back_populates="category")


class Medicine(Base):
    __tablename__ = "medicines"

    medicine_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicine_categories.category_id"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    generic_name: Mapped[str | None] = mapped_column(String(200), index=True)
    brand_name: Mapped[str | None] = mapped_column(String(200), index=True)
    manufacturer: Mapped[str | None] = mapped_column(String(200))
    barcode: Mapped[str | None] = mapped_column(String(100), unique=True)
    dosage: Mapped[str | None] = mapped_column(String(100))
    form: Mapped[str | None] = mapped_column(String(100))
    package_size: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    prescription_required: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category = relationship("MedicineCategory", back_populates="medicines")
    aliases = relationship(
        "MedicineAlias", back_populates="medicine", cascade="all, delete-orphan"
    )
    products = relationship(
        "PharmacyProduct", back_populates="medicine", cascade="all, delete-orphan"
    )
    searches = relationship("SearchHistory", back_populates="medicine")


class Pharmacy(Base):
    __tablename__ = "pharmacies"

    pharmacy_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    name: Mapped[str] = mapped_column(String(150))
    address: Mapped[str] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    phone: Mapped[str | None] = mapped_column(String(30))
    website: Mapped[str | None] = mapped_column(String(255))
    opening_hours: Mapped[str | None] = mapped_column(Text)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="pharmacies")
    products = relationship(
        "PharmacyProduct", back_populates="pharmacy", cascade="all, delete-orphan"
    )


class MedicineAlias(Base):
    __tablename__ = "medicine_aliases"

    alias_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.medicine_id"))
    alias_name: Mapped[str] = mapped_column(String(200), index=True)
    alias_type: Mapped[str | None] = mapped_column(String(50))

    medicine = relationship("Medicine", back_populates="aliases")


class PharmacyProduct(Base):
    __tablename__ = "pharmacy_products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pharmacy_id: Mapped[int] = mapped_column(ForeignKey("pharmacies.pharmacy_id"))
    medicine_id: Mapped[int] = mapped_column(ForeignKey("medicines.medicine_id"))
    price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    package_size: Mapped[str | None] = mapped_column(String(100))
    availability_status: Mapped[str] = mapped_column(
        Enum(
            "available",
            "limited_stock",
            "out_of_stock",
            "unknown",
            name="availability_status",
        ),
        default="unknown",
        index=True,
    )
    stock_quantity: Mapped[int | None] = mapped_column(Integer)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, index=True
    )
    product_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    __table_args__ = (
        UniqueConstraint("pharmacy_id", "medicine_id", name="uq_pharmacy_medicine"),
        Index("ix_product_medicine_active", "medicine_id", "is_active"),
    )

    pharmacy = relationship("Pharmacy", back_populates="products")
    medicine = relationship("Medicine", back_populates="products")
    updates = relationship(
        "PharmacyUpdate", back_populates="product", cascade="all, delete-orphan"
    )


class PharmacyUpdate(Base):
    """Audit trail: one row per change to a pharmacy_products listing."""

    __tablename__ = "pharmacy_updates"

    update_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("pharmacy_products.product_id")
    )
    updated_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    old_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    new_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    old_status: Mapped[str | None] = mapped_column(String(30))
    new_status: Mapped[str | None] = mapped_column(String(30))
    old_stock: Mapped[int | None] = mapped_column(Integer)
    new_stock: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    product = relationship("PharmacyProduct", back_populates="updates")
    updater = relationship("User", back_populates="updates")


class SearchHistory(Base):
    __tablename__ = "search_history"

    search_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    search_query: Mapped[str] = mapped_column(String(255))
    medicine_id: Mapped[int | None] = mapped_column(
        ForeignKey("medicines.medicine_id"), nullable=True
    )
    latitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    longitude: Mapped[float | None] = mapped_column(Numeric(10, 7))
    sort_option: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="searches")
    medicine = relationship("Medicine", back_populates="searches")
