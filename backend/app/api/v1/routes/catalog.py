from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_optional_current_user
from backend.app.core.database import get_db
from backend.app.core.exceptions import NotFoundError
from backend.app.core.responses import ApiResponse
from backend.app.models.catalog import ProductViewEvent
from backend.app.models.user import User
from backend.app.repositories.catalog import CatalogRepository
from backend.app.schemas.catalog import (
    BrandPublic,
    CatalogSearchResult,
    CategoryPublic,
    ProductDetail,
    ProductSummary,
    ProductViewRequest,
    SearchEventRequest,
    SearchSuggestion,
)
from backend.app.schemas.common import PageData
from backend.app.schemas.trade import ReviewPublic
from backend.app.services.catalog import CatalogService
from backend.app.services.catalog_search import (
    CatalogSearchService,
    KnowledgeCatalogSemanticSearch,
)
from backend.app.services.media import MediaService
from backend.app.services.trade import TradeService

router = APIRouter(prefix="/catalog", tags=["商城商品"])
DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/images/{image_id}", response_class=Response)
async def get_product_image(image_id: int, session: DbSession) -> Response:
    content, content_type = await MediaService(session).get_product_image(image_id)
    return Response(content=content, media_type=content_type)


@router.get("/categories", response_model=ApiResponse[list[CategoryPublic]])
async def list_categories(session: DbSession) -> ApiResponse[list[CategoryPublic]]:
    categories = await CatalogRepository(session).list_categories(enabled_only=True)
    return ApiResponse(data=[CategoryPublic.model_validate(item) for item in categories])


@router.get("/brands", response_model=ApiResponse[list[BrandPublic]])
async def list_brands(session: DbSession) -> ApiResponse[list[BrandPublic]]:
    brands = await CatalogRepository(session).list_brands(enabled_only=True)
    return ApiResponse(data=[BrandPublic.model_validate(item) for item in brands])


@router.get(
    "/search/suggestions",
    response_model=ApiResponse[list[SearchSuggestion]],
)
async def search_suggestions(
    session: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=12)] = 8,
) -> ApiResponse[list[SearchSuggestion]]:
    return ApiResponse(data=await CatalogSearchService(session).suggest(q, limit=limit))


@router.get("/search", response_model=ApiResponse[CatalogSearchResult])
async def search_catalog(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=50)] = 20,
    keyword: Annotated[str | None, Query(max_length=100)] = None,
    category_id: int | None = None,
    brand_id: int | None = None,
    min_price: Annotated[Decimal | None, Query(ge=0)] = None,
    max_price: Annotated[Decimal | None, Query(ge=0)] = None,
    in_stock: bool = False,
    semantic: bool = False,
    sort: Literal["relevance", "newest", "sales", "rating", "price_asc", "price_desc"] = (
        "relevance"
    ),
) -> ApiResponse[CatalogSearchResult]:
    semantic_search = None
    if semantic and keyword:
        provider = await KnowledgeCatalogSemanticSearch.from_default_config(session)
        semantic_search = provider.search if provider else None
    data = await CatalogSearchService(session, semantic_search=semantic_search).search(
        page=page,
        page_size=page_size,
        keyword=keyword,
        category_id=category_id,
        brand_id=brand_id,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock,
        sort=sort,
    )
    return ApiResponse(data=data)


@router.post("/search-events", response_model=ApiResponse[None], status_code=201)
async def record_search_event(
    payload: SearchEventRequest,
    session: DbSession,
    current_user: Annotated[User | None, Depends(get_optional_current_user)],
) -> ApiResponse[None]:
    await CatalogSearchService(session).record_event(
        payload, user_id=current_user.id if current_user else None
    )
    return ApiResponse(message="搜索行为已记录", data=None)


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


@router.post("/products/{product_id}/view", response_model=ApiResponse[None])
async def record_product_view(
    product_id: int,
    payload: ProductViewRequest,
    session: DbSession,
    user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[None]:
    if await CatalogRepository(session).get_product(product_id) is None:
        raise NotFoundError("商品不存在")
    session.add(
        ProductViewEvent(
            user_id=user.id,
            product_id=product_id,
            session_key=payload.session_key,
            source=payload.source,
            viewed_at=datetime.now(UTC),
        )
    )
    await session.commit()
    return ApiResponse(message="浏览记录已保存", data=None)


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
