from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import PromotionType, UserStatus


class AdminUserStatusUpdate(BaseModel):
    status: UserStatus


class AfterSaleRuleBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category_id: int | None = Field(default=None, ge=1)
    rule_type: str = Field(min_length=1, max_length=40)
    keywords: list[str] | None = None
    content: str = Field(min_length=1, max_length=10000)
    priority: int = Field(default=0, ge=0)
    enabled: bool = True


class AfterSaleRuleCreate(AfterSaleRuleBase):
    pass


class AfterSaleRuleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category_id: int | None = Field(default=None, ge=1)
    rule_type: str | None = Field(default=None, min_length=1, max_length=40)
    keywords: list[str] | None = None
    content: str | None = Field(default=None, min_length=1, max_length=10000)
    priority: int | None = Field(default=None, ge=0)
    enabled: bool | None = None


class AfterSaleRulePublic(AfterSaleRuleBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PromotionBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    product_id: int | None = Field(default=None, ge=1)
    promotion_type: PromotionType
    value: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    minimum_amount: Decimal = Field(
        default=Decimal("0.00"), ge=0, max_digits=14, decimal_places=2
    )
    starts_at: datetime
    ends_at: datetime
    priority: int = Field(default=0, ge=0)
    enabled: bool = True


class PromotionCreate(PromotionBase):
    pass


class PromotionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    product_id: int | None = Field(default=None, ge=1)
    promotion_type: PromotionType | None = None
    value: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    minimum_amount: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    priority: int | None = Field(default=None, ge=0)
    enabled: bool | None = None


class PromotionPublic(PromotionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
