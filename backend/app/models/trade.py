from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, IdMixin, TimestampMixin
from backend.app.models.enums import OrderStatus, PaymentStatus, PromotionType


class CartItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "cart_items"
    __table_args__ = (UniqueConstraint("user_id", "sku_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), index=True)
    sku_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_skus.id"), index=True)
    quantity: Mapped[int] = mapped_column(Integer)
    selected: Mapped[bool] = mapped_column(Boolean, default=True)


class Order(IdMixin, TimestampMixin, Base):
    __tablename__ = "orders"

    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    status: Mapped[OrderStatus] = mapped_column(
        String(30), default=OrderStatus.PENDING_PAYMENT, index=True
    )
    address_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON)
    product_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    shipping_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    payable_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    buyer_remark: Mapped[str | None] = mapped_column(String(500))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shipped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class OrderItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id"), index=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), index=True)
    sku_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("product_skus.id"), index=True)
    product_name: Mapped[str] = mapped_column(String(255))
    sku_name: Mapped[str] = mapped_column(String(255))
    sku_attributes: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    image_url: Mapped[str | None] = mapped_column(String(500))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    quantity: Mapped[int] = mapped_column(Integer)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))


class PaymentTransaction(IdMixin, TimestampMixin, Base):
    __tablename__ = "payment_transactions"

    payment_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orders.id"), index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    payment_method: Mapped[str] = mapped_column(String(30), default="WALLET")
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[PaymentStatus] = mapped_column(
        String(20), default=PaymentStatus.PENDING, index=True
    )
    failure_reason: Mapped[str | None] = mapped_column(String(500))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Review(IdMixin, TimestampMixin, Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("order_item_id"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), index=True)
    order_item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("order_items.id"), index=True)
    rating: Mapped[int] = mapped_column(Integer, index=True)
    content: Mapped[str] = mapped_column(Text)
    image_urls: Mapped[list[str] | None] = mapped_column(JSON)
    anonymous: Mapped[bool] = mapped_column(Boolean, default=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class AfterSaleRule(IdMixin, TimestampMixin, Base):
    __tablename__ = "after_sale_rules"

    name: Mapped[str] = mapped_column(String(120))
    category_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("categories.id"), index=True
    )
    rule_type: Mapped[str] = mapped_column(String(40), index=True)
    keywords: Mapped[list[str] | None] = mapped_column(JSON)
    content: Mapped[str] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Promotion(IdMixin, TimestampMixin, Base):
    __tablename__ = "promotions"

    name: Mapped[str] = mapped_column(String(120))
    product_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("products.id"), index=True
    )
    promotion_type: Mapped[PromotionType] = mapped_column(String(20), index=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    minimum_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), default=Decimal("0.00")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
