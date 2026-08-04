from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.catalog import Brand, Category, Product, ProductImage, ProductSku
from backend.app.models.enums import ProductStatus


class CatalogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_categories(self, *, enabled_only: bool = True) -> list[Category]:
        statement = select(Category).order_by(Category.sort_order, Category.id)
        if enabled_only:
            statement = statement.where(Category.enabled.is_(True))
        return list((await self.session.scalars(statement)).all())

    async def get_category(self, category_id: int) -> Category | None:
        return await self.session.get(Category, category_id)

    async def category_slug_exists(self, slug: str, *, exclude_id: int | None = None) -> bool:
        statement = select(Category.id).where(Category.slug == slug)
        if exclude_id is not None:
            statement = statement.where(Category.id != exclude_id)
        return await self.session.scalar(statement.limit(1)) is not None

    async def list_brands(self, *, enabled_only: bool = True) -> list[Brand]:
        statement = select(Brand).order_by(Brand.name, Brand.id)
        if enabled_only:
            statement = statement.where(Brand.enabled.is_(True))
        return list((await self.session.scalars(statement)).all())

    async def get_brand(self, brand_id: int) -> Brand | None:
        return await self.session.get(Brand, brand_id)

    async def brand_slug_exists(self, slug: str, *, exclude_id: int | None = None) -> bool:
        statement = select(Brand.id).where(Brand.slug == slug)
        if exclude_id is not None:
            statement = statement.where(Brand.id != exclude_id)
        return await self.session.scalar(statement.limit(1)) is not None

    async def product_no_exists(self, product_no: str, *, exclude_id: int | None = None) -> bool:
        statement = select(Product.id).where(Product.product_no == product_no)
        if exclude_id is not None:
            statement = statement.where(Product.id != exclude_id)
        return await self.session.scalar(statement.limit(1)) is not None

    async def sku_no_exists(self, sku_no: str, *, exclude_id: int | None = None) -> bool:
        statement = select(ProductSku.id).where(ProductSku.sku_no == sku_no)
        if exclude_id is not None:
            statement = statement.where(ProductSku.id != exclude_id)
        return await self.session.scalar(statement.limit(1)) is not None

    async def list_products(
        self,
        *,
        page: int,
        page_size: int,
        category_id: int | None = None,
        brand_id: int | None = None,
        keyword: str | None = None,
        status: ProductStatus | None = ProductStatus.ON_SALE,
        min_price: Decimal | None = None,
        max_price: Decimal | None = None,
    ) -> tuple[list[Product], int]:
        statement: Select[tuple[Product]] = select(Product)
        if category_id is not None:
            statement = statement.where(Product.category_id == category_id)
        if brand_id is not None:
            statement = statement.where(Product.brand_id == brand_id)
        if keyword:
            escaped = keyword.replace("%", r"\%").replace("_", r"\_")
            statement = statement.where(Product.name.like(f"%{escaped}%", escape="\\"))
        if status is not None:
            statement = statement.where(Product.status == status)
        if min_price is not None:
            statement = statement.where(Product.max_price >= min_price)
        if max_price is not None:
            statement = statement.where(Product.min_price <= max_price)

        total_statement = select(func.count()).select_from(statement.order_by(None).subquery())
        total = int(await self.session.scalar(total_statement) or 0)
        statement = statement.order_by(Product.created_at.desc(), Product.id.desc())
        statement = statement.offset((page - 1) * page_size).limit(page_size)
        return list((await self.session.scalars(statement)).all()), total

    async def get_product(self, product_id: int) -> Product | None:
        return await self.session.get(Product, product_id)

    async def get_product_detail_parts(
        self, product_id: int, *, enabled_skus_only: bool
    ) -> tuple[list[ProductImage], list[ProductSku]]:
        images = list(
            (
                await self.session.scalars(
                    select(ProductImage)
                    .where(ProductImage.product_id == product_id)
                    .order_by(ProductImage.sort_order, ProductImage.id)
                )
            ).all()
        )
        sku_statement = select(ProductSku).where(ProductSku.product_id == product_id)
        if enabled_skus_only:
            sku_statement = sku_statement.where(ProductSku.enabled.is_(True))
        skus = list((await self.session.scalars(sku_statement.order_by(ProductSku.id))).all())
        return images, skus

    async def get_sku(self, sku_id: int) -> ProductSku | None:
        return await self.session.get(ProductSku, sku_id)

    async def update_product_price_range(self, product_id: int) -> None:
        result = await self.session.execute(
            select(func.min(ProductSku.price), func.max(ProductSku.price)).where(
                ProductSku.product_id == product_id,
                ProductSku.enabled.is_(True),
            )
        )
        min_price, max_price = result.one()
        product = await self.get_product(product_id)
        if product is not None:
            product.min_price = min_price or Decimal("0.00")
            product.max_price = max_price or Decimal("0.00")

    def add(self, entity: object) -> None:
        self.session.add(entity)

