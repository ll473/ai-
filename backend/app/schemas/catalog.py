from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.enums import ProductStatus


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    parent_id: int | None = None
    icon_url: str | None = Field(default=None, max_length=500)
    sort_order: int = 0
    enabled: bool = True


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    parent_id: int | None = None
    icon_url: str | None = Field(default=None, max_length=500)
    sort_order: int | None = None
    enabled: bool | None = None


class CategoryPublic(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class BrandBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    logo_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    enabled: bool = True


class BrandCreate(BrandBase):
    pass


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    slug: str | None = Field(default=None, min_length=1, max_length=120, pattern=r"^[a-z0-9-]+$")
    logo_url: str | None = Field(default=None, max_length=500)
    description: str | None = None
    enabled: bool | None = None


class BrandPublic(BrandBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime


class ProductBase(BaseModel):
    category_id: int
    brand_id: int | None = None
    name: str = Field(min_length=1, max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    product_no: str = Field(min_length=1, max_length=64)
    main_image_url: str | None = Field(default=None, max_length=500)
    detail_markdown: str | None = None
    parameters: dict[str, Any] | None = None
    status: ProductStatus = ProductStatus.DRAFT


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    category_id: int | None = None
    brand_id: int | None = None
    name: str | None = Field(default=None, min_length=1, max_length=255)
    subtitle: str | None = Field(default=None, max_length=500)
    product_no: str | None = Field(default=None, min_length=1, max_length=64)
    main_image_url: str | None = Field(default=None, max_length=500)
    detail_markdown: str | None = None
    parameters: dict[str, Any] | None = None
    status: ProductStatus | None = None


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    brand_id: int | None
    name: str
    subtitle: str | None
    product_no: str
    main_image_url: str | None
    min_price: Decimal
    max_price: Decimal
    rating: Decimal
    review_count: int
    sales_count: int
    status: ProductStatus
    created_at: datetime


class SkuBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sku_no: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=255)
    attributes: dict[str, Any] | None = None
    price: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    market_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    enabled: bool = True


class SkuCreate(SkuBase):
    pass


class SkuUpdate(BaseModel):
    sku_no: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    attributes: dict[str, Any] | None = None
    price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    market_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)
    enabled: bool | None = None


class SkuPublic(SkuBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    locked_stock: int
    available_stock: int
    created_at: datetime


class ProductImagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    image_url: str
    alt_text: str | None
    sort_order: int


class ProductDetail(ProductSummary):
    detail_markdown: str | None
    parameters: dict[str, Any] | None
    images: list[ProductImagePublic]
    skus: list[SkuPublic]


class UploadedImage(BaseModel):
    id: int
    url: str
    content_type: str
    size: int
