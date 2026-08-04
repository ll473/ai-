from datetime import datetime
from decimal import Decimal
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.models.enums import OrderStatus, PaymentStatus, WalletTransactionType


class AddressBase(BaseModel):
    receiver_name: str = Field(min_length=1, max_length=80)
    receiver_phone: str = Field(min_length=6, max_length=30)
    province: str = Field(min_length=1, max_length=80)
    city: str = Field(min_length=1, max_length=80)
    district: str = Field(min_length=1, max_length=80)
    detail: str = Field(min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    is_default: bool = False


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    receiver_name: str | None = Field(default=None, min_length=1, max_length=80)
    receiver_phone: str | None = Field(default=None, min_length=6, max_length=30)
    province: str | None = Field(default=None, min_length=1, max_length=80)
    city: str | None = Field(default=None, min_length=1, max_length=80)
    district: str | None = Field(default=None, min_length=1, max_length=80)
    detail: str | None = Field(default=None, min_length=1, max_length=255)
    postal_code: str | None = Field(default=None, max_length=20)
    is_default: bool | None = None


class AddressPublic(AddressBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class CartAddRequest(BaseModel):
    sku_id: int
    quantity: int = Field(default=1, ge=1, le=99)


class CartUpdateRequest(BaseModel):
    quantity: int | None = Field(default=None, ge=1, le=99)
    selected: bool | None = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.quantity is None and self.selected is None:
            raise ValueError("至少需要修改数量或选中状态")
        return self


class CartSelectRequest(BaseModel):
    selected: bool


class CartItemPublic(BaseModel):
    id: int
    product_id: int
    sku_id: int
    product_name: str
    sku_name: str
    sku_attributes: dict[str, Any] | None
    image_url: str | None
    unit_price: Decimal
    quantity: int
    selected: bool
    available_stock: int
    available: bool
    subtotal: Decimal


class CartSummary(BaseModel):
    items: list[CartItemPublic]
    total_count: int
    selected_count: int
    selected_amount: Decimal


class WalletPublic(BaseModel):
    balance: Decimal


class RechargeRequest(BaseModel):
    amount: Decimal = Field(gt=0, le=100000, max_digits=14, decimal_places=2)


class WalletTransactionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_no: str
    transaction_type: WalletTransactionType
    amount: Decimal
    balance_before: Decimal
    balance_after: Decimal
    reference_type: str | None
    reference_id: str | None
    remark: str | None
    created_at: datetime


class CheckoutRequest(BaseModel):
    address_id: int
    buyer_remark: str | None = Field(default=None, max_length=500)


class OrderItemPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    sku_id: int
    product_name: str
    sku_name: str
    sku_attributes: dict[str, Any] | None
    image_url: str | None
    unit_price: Decimal
    quantity: int
    total_amount: Decimal
    reviewed: bool = False


class OrderSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_no: str
    status: OrderStatus
    product_amount: Decimal
    discount_amount: Decimal
    shipping_amount: Decimal
    payable_amount: Decimal
    paid_amount: Decimal
    created_at: datetime
    paid_at: datetime | None


class OrderDetail(OrderSummary):
    address_snapshot: dict[str, Any]
    buyer_remark: str | None
    shipped_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    items: list[OrderItemPublic]


class PaymentResult(BaseModel):
    payment_no: str
    status: PaymentStatus
    paid_amount: Decimal
    wallet_balance: Decimal
    order: OrderDetail


class AdminOrderSummary(OrderSummary):
    user_id: int


class AdminOrderDetail(OrderDetail):
    user_id: int


class ReviewCreate(BaseModel):
    order_item_id: int
    rating: int = Field(ge=1, le=5)
    content: str = Field(min_length=1, max_length=2000)
    image_urls: list[str] | None = Field(default=None, max_length=6)
    anonymous: bool = False


class ReviewPublic(BaseModel):
    id: int
    product_id: int
    rating: int
    content: str
    image_urls: list[str] | None
    anonymous: bool
    display_name: str
    created_at: datetime


class ReviewAdmin(ReviewPublic):
    order_item_id: int
    username: str
    product_name: str
    visible: bool


class ReviewVisibilityUpdate(BaseModel):
    visible: bool
