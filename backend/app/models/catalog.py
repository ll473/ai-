from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, IdMixin, TimestampMixin
from backend.app.models.enums import ProductStatus


class Category(IdMixin, TimestampMixin, Base):
    __tablename__ = "categories"

    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    icon_url: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Brand(IdMixin, TimestampMixin, Base):
    __tablename__ = "brands"

    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Product(IdMixin, TimestampMixin, Base):
    __tablename__ = "products"

    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("categories.id"), index=True)
    brand_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("brands.id"), index=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    subtitle: Mapped[str | None] = mapped_column(String(500))
    product_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    main_image_url: Mapped[str | None] = mapped_column(String(500))
    detail_markdown: Mapped[str | None] = mapped_column(Text)
    parameters: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    min_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    max_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    sales_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[ProductStatus] = mapped_column(
        String(20), default=ProductStatus.DRAFT, index=True
    )


class ProductImage(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_images"

    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), index=True)
    image_url: Mapped[str] = mapped_column(String(500))
    alt_text: Mapped[str | None] = mapped_column(String(255))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ProductSku(IdMixin, TimestampMixin, Base):
    __tablename__ = "product_skus"

    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), index=True)
    sku_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    stock: Mapped[int] = mapped_column(Integer, default=0)
    locked_stock: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=0, comment="Optimistic lock version")


class Favorite(IdMixin, TimestampMixin, Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "product_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), index=True)
