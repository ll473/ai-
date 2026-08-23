from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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


class ProductComparisonItem(ProductSummary):
    category_name: str
    brand_name: str | None = None
    parameters: dict[str, Any] | None = None
    skus: list[SkuPublic]
    total_available_stock: int


class ProductComparisonResult(BaseModel):
    items: list[ProductComparisonItem]
    unavailable_ids: list[int]
    category_id: int | None = None
    category_name: str | None = None


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


class ProductViewRequest(BaseModel):
    session_key: str | None = Field(default=None, max_length=64)
    source: str | None = Field(default=None, max_length=40)


class SearchSuggestion(BaseModel):
    kind: Literal["product", "category", "brand", "query"]
    label: str
    value: str
    product_id: int | None = None


class SearchFacetItem(BaseModel):
    id: int
    name: str
    count: int


class SearchFacets(BaseModel):
    categories: list[SearchFacetItem]
    brands: list[SearchFacetItem]
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    in_stock_count: int = 0


class CatalogSearchResult(BaseModel):
    items: list[ProductSummary]
    page: int
    page_size: int
    total: int
    facets: SearchFacets
    search_mode: Literal["catalog", "hybrid"] = "catalog"


class SearchEventFilters(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int | None = Field(default=None, ge=1)
    brand_id: int | None = Field(default=None, ge=1)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    in_stock: bool | None = None
    sort: Literal["relevance", "newest", "sales", "rating", "price_asc", "price_desc"] | None = (
        None
    )
    search_mode: Literal["catalog", "hybrid"] | None = None


class SearchEventRequest(BaseModel):
    event_type: Literal["search", "click"]
    query: str | None = Field(default=None, max_length=200)
    product_id: int | None = None
    session_key: str = Field(min_length=8, max_length=64)
    filters: SearchEventFilters | None = None
    result_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_event_context(self) -> "SearchEventRequest":
        if self.event_type == "search" and not (self.query or "").strip():
            raise ValueError("搜索事件必须包含关键词")
        if self.event_type == "click" and self.product_id is None:
            raise ValueError("点击事件必须包含商品 ID")
        return self
