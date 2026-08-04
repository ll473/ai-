from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.database import get_db
from backend.app.core.responses import ApiResponse
from backend.app.repositories.catalog import CatalogRepository
from backend.app.schemas.catalog import BrandPublic, CategoryPublic, ProductDetail, ProductSummary
from backend.app.schemas.common import PageData
from backend.app.schemas.trade import ReviewPublic
from backend.app.services.catalog import CatalogService
from backend.app.services.trade import TradeService

router = APIRouter(prefix="/catalog", tags=["商城商品"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/categories", response_model=ApiResponse[list[CategoryPublic]])
async def list_categories(session: DbSession) -> ApiResponse[list[CategoryPublic]]:
    categories = await CatalogRepository(session).list_categories(enabled_only=True)
    return ApiResponse(data=[CategoryPublic.model_validate(item) for item in categories])


@router.get("/brands", response_model=ApiResponse[list[BrandPublic]])
async def list_brands(session: DbSession) -> ApiResponse[list[BrandPublic]]:
    brands = await CatalogRepository(session).list_brands(enabled_only=True)
    return ApiResponse(data=[BrandPublic.model_validate(item) for item in brands])


@router.get("/products", response_model=ApiResponse[PageData[ProductSummary]])
async def list_products(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
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
    )
    return ApiResponse(data=data)


@router.get("/products/{product_id}", response_model=ApiResponse[ProductDetail])
async def get_product(product_id: int, session: DbSession) -> ApiResponse[ProductDetail]:
    return ApiResponse(data=await CatalogService(session).get_product_detail(product_id))


@router.get(
    "/products/{product_id}/reviews",
    response_model=ApiResponse[PageData[ReviewPublic]],
)
async def list_product_reviews(
    product_id: int,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
) -> ApiResponse[PageData[ReviewPublic]]:
    return ApiResponse(
        data=await TradeService(session).list_product_reviews(
            product_id, page=page, page_size=page_size
        )
    )
