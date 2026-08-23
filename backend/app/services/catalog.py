from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import AppError, ConflictError, NotFoundError
from backend.app.models.catalog import Brand, Category, Product, ProductSku
from backend.app.models.enums import ProductStatus
from backend.app.repositories.catalog import CatalogRepository
from backend.app.schemas.catalog import (
    BrandCreate,
    BrandUpdate,
    CategoryCreate,
    CategoryUpdate,
    ProductComparisonItem,
    ProductComparisonResult,
    ProductCreate,
    ProductDetail,
    ProductImagePublic,
    ProductSummary,
    ProductUpdate,
    SkuBase,
    SkuCreate,
    SkuPublic,
    SkuUpdate,
)
from backend.app.schemas.common import PageData


def _apply_changes(entity: object, changes: Mapping[str, Any]) -> None:
    for field, value in changes.items():
        setattr(entity, field, value)


def _sku_public(sku: ProductSku) -> SkuPublic:
    base = SkuBase.model_validate(sku).model_dump()
    return SkuPublic(
        **base,
        id=sku.id,
        product_id=sku.product_id,
        locked_stock=sku.locked_stock,
        available_stock=max(0, sku.stock - sku.locked_stock),
        created_at=sku.created_at,
    )


def _comparison_item(
    product: Product,
    category: Category,
    brand: Brand | None,
    skus: list[ProductSku],
) -> ProductComparisonItem:
    public_skus = [_sku_public(sku) for sku in skus]
    return ProductComparisonItem(
        **ProductSummary.model_validate(product).model_dump(),
        category_name=category.name,
        brand_name=brand.name if brand else None,
        parameters=product.parameters,
        skus=public_skus,
        total_available_stock=sum(sku.available_stock for sku in public_skus),
    )


class CatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogRepository(session)

    async def list_products(
        self,
        *,
        page: int,
        page_size: int,
        category_id: int | None,
        brand_id: int | None,
        keyword: str | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        include_all_statuses: bool = False,
    ) -> PageData[ProductSummary]:
        products, total = await self.catalog.list_products(
            page=page,
            page_size=page_size,
            category_id=category_id,
            brand_id=brand_id,
            keyword=keyword,
            min_price=min_price,
            max_price=max_price,
            status=None if include_all_statuses else ProductStatus.ON_SALE,
        )
        return PageData(
            items=[ProductSummary.model_validate(item) for item in products],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_product_detail(
        self, product_id: int, *, admin: bool = False
    ) -> ProductDetail:
        product = await self.catalog.get_product(product_id)
        if product is None or (not admin and product.status != ProductStatus.ON_SALE):
            raise NotFoundError("商品不存在或已下架")
        images, skus = await self.catalog.get_product_detail_parts(
            product_id, enabled_skus_only=not admin
        )
        summary = ProductSummary.model_validate(product).model_dump()
        return ProductDetail(
            **summary,
            detail_markdown=product.detail_markdown,
            parameters=product.parameters,
            images=[ProductImagePublic.model_validate(image) for image in images],
            skus=[_sku_public(sku) for sku in skus],
        )

    async def compare_products(self, product_ids: Sequence[int]) -> ProductComparisonResult:
        ordered_ids = list(dict.fromkeys(product_ids))
        if not 2 <= len(ordered_ids) <= 4:
            raise AppError(
                "请选择 2–4 件商品进行对比",
                code="COMPARISON_SIZE_INVALID",
                status_code=422,
            )
        rows, skus = await self.catalog.get_products_for_comparison(ordered_ids)
        row_by_id = {
            product.id: (product, category, brand) for product, category, brand in rows
        }
        categories = {product.category_id for product, _, _ in rows}
        if len(categories) > 1:
            raise AppError(
                "只能对比同一分类商品",
                code="COMPARISON_CATEGORY_MISMATCH",
                status_code=422,
            )
        skus_by_product: dict[int, list[ProductSku]] = defaultdict(list)
        for sku in skus:
            skus_by_product[sku.product_id].append(sku)
        items = [
            _comparison_item(*row_by_id[product_id], skus_by_product[product_id])
            for product_id in ordered_ids
            if product_id in row_by_id
        ]
        unavailable_ids = [product_id for product_id in ordered_ids if product_id not in row_by_id]
        return ProductComparisonResult(
            items=items,
            unavailable_ids=unavailable_ids,
            category_id=items[0].category_id if items else None,
            category_name=items[0].category_name if items else None,
        )

    async def create_category(self, payload: CategoryCreate) -> Category:
        if await self.catalog.category_slug_exists(payload.slug):
            raise ConflictError("分类标识已存在")
        if (
            payload.parent_id is not None
            and await self.catalog.get_category(payload.parent_id) is None
        ):
            raise NotFoundError("父分类不存在")
        category = Category(**payload.model_dump())
        self.catalog.add(category)
        await self._commit_and_refresh(category)
        return category

    async def update_category(self, category_id: int, payload: CategoryUpdate) -> Category:
        category = await self.catalog.get_category(category_id)
        if category is None:
            raise NotFoundError("分类不存在")
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("slug") and await self.catalog.category_slug_exists(
            changes["slug"], exclude_id=category_id
        ):
            raise ConflictError("分类标识已存在")
        if "parent_id" in changes:
            parent_id = changes["parent_id"]
            if parent_id == category_id:
                raise ConflictError("分类不能将自己设为父分类")
            if parent_id is not None and await self.catalog.get_category(parent_id) is None:
                raise NotFoundError("父分类不存在")
        _apply_changes(category, changes)
        await self._commit_and_refresh(category)
        return category

    async def create_brand(self, payload: BrandCreate) -> Brand:
        if await self.catalog.brand_slug_exists(payload.slug):
            raise ConflictError("品牌标识已存在")
        brand = Brand(**payload.model_dump())
        self.catalog.add(brand)
        await self._commit_and_refresh(brand)
        return brand

    async def update_brand(self, brand_id: int, payload: BrandUpdate) -> Brand:
        brand = await self.catalog.get_brand(brand_id)
        if brand is None:
            raise NotFoundError("品牌不存在")
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("slug") and await self.catalog.brand_slug_exists(
            changes["slug"], exclude_id=brand_id
        ):
            raise ConflictError("品牌标识已存在")
        _apply_changes(brand, changes)
        await self._commit_and_refresh(brand)
        return brand

    async def create_product(self, payload: ProductCreate) -> Product:
        await self._validate_product_relations(payload.category_id, payload.brand_id)
        if await self.catalog.product_no_exists(payload.product_no):
            raise ConflictError("商品编号已存在")
        product = Product(**payload.model_dump())
        self.catalog.add(product)
        await self._commit_and_refresh(product)
        return product

    async def update_product(self, product_id: int, payload: ProductUpdate) -> Product:
        product = await self.catalog.get_product(product_id)
        if product is None:
            raise NotFoundError("商品不存在")
        changes = payload.model_dump(exclude_unset=True)
        category_id = changes.get("category_id", product.category_id)
        brand_id = changes.get("brand_id", product.brand_id)
        await self._validate_product_relations(category_id, brand_id)
        if changes.get("product_no") and await self.catalog.product_no_exists(
            changes["product_no"], exclude_id=product_id
        ):
            raise ConflictError("商品编号已存在")
        _apply_changes(product, changes)
        await self._commit_and_refresh(product)
        return product

    async def create_sku(self, product_id: int, payload: SkuCreate) -> SkuPublic:
        if await self.catalog.get_product(product_id) is None:
            raise NotFoundError("商品不存在")
        if await self.catalog.sku_no_exists(payload.sku_no):
            raise ConflictError("SKU 编号已存在")
        sku = ProductSku(product_id=product_id, **payload.model_dump())
        self.catalog.add(sku)
        await self.session.flush()
        await self.catalog.update_product_price_range(product_id)
        await self.session.commit()
        await self.session.refresh(sku)
        return _sku_public(sku)

    async def update_sku(self, sku_id: int, payload: SkuUpdate) -> SkuPublic:
        sku = await self.catalog.get_sku(sku_id, lock=True)
        if sku is None:
            raise NotFoundError("SKU 不存在")
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("sku_no") and await self.catalog.sku_no_exists(
            changes["sku_no"], exclude_id=sku_id
        ):
            raise ConflictError("SKU 编号已存在")
        if changes.get("stock", sku.stock) < sku.locked_stock:
            raise ConflictError("库存不能低于待支付订单已锁定的数量")
        _apply_changes(sku, changes)
        await self.session.flush()
        await self.catalog.update_product_price_range(sku.product_id)
        await self.session.commit()
        await self.session.refresh(sku)
        return _sku_public(sku)

    async def _validate_product_relations(
        self, category_id: int, brand_id: int | None
    ) -> None:
        if await self.catalog.get_category(category_id) is None:
            raise NotFoundError("商品分类不存在")
        if brand_id is not None and await self.catalog.get_brand(brand_id) is None:
            raise NotFoundError("商品品牌不存在")

    async def _commit_and_refresh(self, entity: Any) -> None:
        await self.session.commit()
        await self.session.refresh(entity)
