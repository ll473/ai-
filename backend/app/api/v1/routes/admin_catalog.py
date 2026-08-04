from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin
from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.models.user import User
from backend.app.repositories.catalog import CatalogRepository
from backend.app.schemas.catalog import (
    BrandCreate,
    BrandPublic,
    BrandUpdate,
    CategoryCreate,
    CategoryPublic,
    CategoryUpdate,
    ProductCreate,
    ProductDetail,
    ProductSummary,
    ProductUpdate,
    SkuCreate,
    SkuPublic,
    SkuUpdate,
    UploadedImage,
)
from backend.app.schemas.common import PageData
from backend.app.services.catalog import CatalogService
from backend.app.services.media import MediaService

router = APIRouter(prefix="/admin/catalog", tags=["管理端商品"])
DbSession = Annotated[AsyncSession, Depends(get_db)]
AdminUser = Annotated[User, Depends(require_admin)]


@router.get("/categories", response_model=ApiResponse[list[CategoryPublic]])
async def list_categories(
    session: DbSession, _: AdminUser
) -> ApiResponse[list[CategoryPublic]]:
    items = await CatalogRepository(session).list_categories(enabled_only=False)
    return ApiResponse(data=[CategoryPublic.model_validate(item) for item in items])


@router.post(
    "/categories",
    response_model=ApiResponse[CategoryPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreate, session: DbSession, _: AdminUser
) -> ApiResponse[CategoryPublic]:
    item = await CatalogService(session).create_category(payload)
    return ApiResponse(message="分类创建成功", data=CategoryPublic.model_validate(item))


@router.put("/categories/{category_id}", response_model=ApiResponse[CategoryPublic])
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[CategoryPublic]:
    item = await CatalogService(session).update_category(category_id, payload)
    return ApiResponse(message="分类更新成功", data=CategoryPublic.model_validate(item))


@router.get("/brands", response_model=ApiResponse[list[BrandPublic]])
async def list_brands(session: DbSession, _: AdminUser) -> ApiResponse[list[BrandPublic]]:
    items = await CatalogRepository(session).list_brands(enabled_only=False)
    return ApiResponse(data=[BrandPublic.model_validate(item) for item in items])


@router.post(
    "/brands",
    response_model=ApiResponse[BrandPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_brand(
    payload: BrandCreate, session: DbSession, _: AdminUser
) -> ApiResponse[BrandPublic]:
    item = await CatalogService(session).create_brand(payload)
    return ApiResponse(message="品牌创建成功", data=BrandPublic.model_validate(item))


@router.put("/brands/{brand_id}", response_model=ApiResponse[BrandPublic])
async def update_brand(
    brand_id: int,
    payload: BrandUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[BrandPublic]:
    item = await CatalogService(session).update_brand(brand_id, payload)
    return ApiResponse(message="品牌更新成功", data=BrandPublic.model_validate(item))


@router.get("/products", response_model=ApiResponse[PageData[ProductSummary]])
async def list_products(
    session: DbSession,
    _: AdminUser,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    category_id: int | None = None,
    brand_id: int | None = None,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
) -> ApiResponse[PageData[ProductSummary]]:
    data = await CatalogService(session).list_products(
        page=page,
        page_size=page_size,
        category_id=category_id,
        brand_id=brand_id,
        keyword=keyword,
        min_price=min_price,
        max_price=max_price,
        include_all_statuses=True,
    )
    return ApiResponse(data=data)


@router.get("/products/{product_id}", response_model=ApiResponse[ProductDetail])
async def get_product(
    product_id: int, session: DbSession, _: AdminUser
) -> ApiResponse[ProductDetail]:
    data = await CatalogService(session).get_product_detail(product_id, admin=True)
    return ApiResponse(data=data)


@router.post(
    "/products",
    response_model=ApiResponse[ProductSummary],
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: ProductCreate, session: DbSession, _: AdminUser
) -> ApiResponse[ProductSummary]:
    item = await CatalogService(session).create_product(payload)
    return ApiResponse(message="商品创建成功", data=ProductSummary.model_validate(item))


@router.put("/products/{product_id}", response_model=ApiResponse[ProductSummary])
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[ProductSummary]:
    item = await CatalogService(session).update_product(product_id, payload)
    return ApiResponse(message="商品更新成功", data=ProductSummary.model_validate(item))


@router.post(
    "/products/{product_id}/skus",
    response_model=ApiResponse[SkuPublic],
    status_code=status.HTTP_201_CREATED,
)
async def create_sku(
    product_id: int,
    payload: SkuCreate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[SkuPublic]:
    item = await CatalogService(session).create_sku(product_id, payload)
    return ApiResponse(message="SKU 创建成功", data=item)


@router.put("/skus/{sku_id}", response_model=ApiResponse[SkuPublic])
async def update_sku(
    sku_id: int,
    payload: SkuUpdate,
    session: DbSession,
    _: AdminUser,
) -> ApiResponse[SkuPublic]:
    item = await CatalogService(session).update_sku(sku_id, payload)
    return ApiResponse(message="SKU 更新成功", data=item)


@router.post(
    "/products/{product_id}/images",
    response_model=ApiResponse[UploadedImage],
    status_code=status.HTTP_201_CREATED,
)
async def upload_product_image(
    product_id: int,
    session: DbSession,
    _: AdminUser,
    file: Annotated[UploadFile, File()],
    alt_text: Annotated[str | None, Form(max_length=255)] = None,
    sort_order: Annotated[int, Form(ge=0)] = 0,
) -> ApiResponse[UploadedImage]:
    data = await MediaService(session).save_product_image(
        product_id,
        file,
        alt_text=alt_text,
        sort_order=sort_order,
    )
    return ApiResponse(message="图片上传成功", data=data)
