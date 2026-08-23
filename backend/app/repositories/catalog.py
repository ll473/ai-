from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

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

    async def search_suggestions(
        self, terms: Sequence[str], *, limit: int
    ) -> tuple[list[Product], list[Category], list[Brand]]:
        if not terms:
            return [], [], []
        product_conditions = []
        taxonomy_conditions = []
        for term in terms:
            escaped = term.replace("%", r"\%").replace("_", r"\_")
            pattern = f"%{escaped}%"
            product_conditions.extend(
                [
                    Product.name.like(pattern, escape="\\"),
                    Product.subtitle.like(pattern, escape="\\"),
                ]
            )
            taxonomy_conditions.append(pattern)
        products = list(
            (
                await self.session.scalars(
                    select(Product)
                    .where(
                        Product.status == ProductStatus.ON_SALE,
                        or_(*product_conditions),
                    )
                    .order_by(
                        Product.sales_count.desc(),
                        Product.rating.desc(),
                        Product.id.desc(),
                    )
                    .limit(limit)
                )
            ).all()
        )
        remaining = max(0, limit - len(products))
        if not remaining:
            return products, [], []
        categories = list(
            (
                await self.session.scalars(
                    select(Category)
                    .where(
                        Category.enabled.is_(True),
                        or_(
                            *[
                                Category.name.like(pattern, escape="\\")
                                for pattern in taxonomy_conditions
                            ]
                        ),
                    )
                    .order_by(Category.sort_order, Category.id)
                    .limit(remaining)
                )
            ).all()
        )
        remaining = max(0, remaining - len(categories))
        if not remaining:
            return products, categories, []
        brands = list(
            (
                await self.session.scalars(
                    select(Brand)
                    .where(
                        Brand.enabled.is_(True),
                        or_(
                            *[
                                Brand.name.like(pattern, escape="\\")
                                for pattern in taxonomy_conditions
                            ]
                        ),
                    )
                    .order_by(Brand.name, Brand.id)
                    .limit(remaining)
                )
            ).all()
        )
        return products, categories, brands

    async def search_catalog_products(
        self,
        *,
        terms: Sequence[str],
        category_id: int | None,
        brand_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool,
        product_ids: Sequence[int] | None = None,
        offset: int = 0,
        limit: int = 500,
        sort: str = "relevance",
    ) -> list[Product]:
        statement: Select[tuple[Product]] = select(Product).where(
            *self._catalog_search_conditions(
                terms=terms,
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                in_stock=in_stock,
                product_ids=product_ids,
            )
        )
        if product_ids is not None:
            if not product_ids:
                return []
        if sort == "newest":
            statement = statement.order_by(Product.created_at.desc(), Product.id.desc())
        elif sort == "sales":
            statement = statement.order_by(Product.sales_count.desc(), Product.id.desc())
        elif sort == "rating":
            statement = statement.order_by(
                Product.rating.desc(), Product.review_count.desc(), Product.id.desc()
            )
        elif sort == "price_asc":
            statement = statement.order_by(Product.min_price.asc(), Product.id.asc())
        elif sort == "price_desc":
            statement = statement.order_by(Product.max_price.desc(), Product.id.desc())
        else:
            statement = statement.order_by(
                Product.rating.desc(), Product.sales_count.desc(), Product.id.desc()
            )
        statement = statement.offset(offset).limit(limit)
        return list((await self.session.scalars(statement)).all())

    async def count_catalog_products(
        self,
        *,
        terms: Sequence[str],
        category_id: int | None,
        brand_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool,
    ) -> int:
        statement = select(func.count(Product.id)).where(
            *self._catalog_search_conditions(
                terms=terms,
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                in_stock=in_stock,
            )
        )
        return int(await self.session.scalar(statement) or 0)

    async def search_catalog_facets(
        self,
        *,
        terms: Sequence[str],
        category_id: int | None,
        brand_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool,
    ) -> tuple[
        list[tuple[int, str, int]],
        list[tuple[int, str, int]],
        Decimal | None,
        Decimal | None,
        int,
    ]:
        category_statement = (
            select(Product.category_id, Category.name, func.count(Product.id))
            .join(Category, Category.id == Product.category_id)
            .where(
                Category.enabled.is_(True),
                *self._catalog_search_conditions(
                    terms=terms,
                    category_id=None,
                    brand_id=brand_id,
                    min_price=min_price,
                    max_price=max_price,
                    in_stock=in_stock,
                ),
            )
            .group_by(Product.category_id, Category.name)
            .order_by(func.count(Product.id).desc(), Product.category_id)
        )
        brand_statement = (
            select(Product.brand_id, Brand.name, func.count(Product.id))
            .join(Brand, Brand.id == Product.brand_id)
            .where(
                Brand.enabled.is_(True),
                *self._catalog_search_conditions(
                    terms=terms,
                    category_id=category_id,
                    brand_id=None,
                    min_price=min_price,
                    max_price=max_price,
                    in_stock=in_stock,
                ),
            )
            .group_by(Product.brand_id, Brand.name)
            .order_by(func.count(Product.id).desc(), Product.brand_id)
        )
        price_statement = select(
            func.min(Product.min_price), func.max(Product.max_price)
        ).where(
            *self._catalog_search_conditions(
                terms=terms,
                category_id=category_id,
                brand_id=brand_id,
                min_price=None,
                max_price=None,
                in_stock=in_stock,
            )
        )
        stock_statement = select(func.count(Product.id)).where(
            *self._catalog_search_conditions(
                terms=terms,
                category_id=category_id,
                brand_id=brand_id,
                min_price=min_price,
                max_price=max_price,
                in_stock=True,
            )
        )
        category_rows = [
            (int(row[0]), str(row[1]), int(row[2]))
            for row in (await self.session.execute(category_statement)).all()
        ]
        brand_rows = [
            (int(row[0]), str(row[1]), int(row[2]))
            for row in (await self.session.execute(brand_statement)).all()
        ]
        price_row = (await self.session.execute(price_statement)).one()
        in_stock_count = int(await self.session.scalar(stock_statement) or 0)
        return category_rows, brand_rows, price_row[0], price_row[1], in_stock_count

    @staticmethod
    def _catalog_search_conditions(
        *,
        terms: Sequence[str],
        category_id: int | None,
        brand_id: int | None,
        min_price: Decimal | None,
        max_price: Decimal | None,
        in_stock: bool,
        product_ids: Sequence[int] | None = None,
    ) -> list[ColumnElement[bool]]:
        conditions: list[ColumnElement[bool]] = [Product.status == ProductStatus.ON_SALE]
        if product_ids is not None:
            conditions.append(Product.id.in_(product_ids))
        if category_id is not None:
            conditions.append(Product.category_id == category_id)
        if brand_id is not None:
            conditions.append(Product.brand_id == brand_id)
        if min_price is not None:
            conditions.append(Product.max_price >= min_price)
        if max_price is not None:
            conditions.append(Product.min_price <= max_price)
        if in_stock:
            conditions.append(
                exists(
                    select(ProductSku.id).where(
                        ProductSku.product_id == Product.id,
                        ProductSku.enabled.is_(True),
                        ProductSku.stock > ProductSku.locked_stock,
                    )
                )
            )
        if terms:
            term_conditions: list[ColumnElement[bool]] = []
            for term in terms:
                escaped = term.replace("%", r"\%").replace("_", r"\_")
                pattern = f"%{escaped}%"
                term_conditions.extend(
                    [
                        Product.name.like(pattern, escape="\\"),
                        Product.subtitle.like(pattern, escape="\\"),
                        Product.category_id.in_(
                            select(Category.id).where(
                                Category.enabled.is_(True),
                                Category.name.like(pattern, escape="\\"),
                            )
                        ),
                        Product.brand_id.in_(
                            select(Brand.id).where(
                                Brand.enabled.is_(True),
                                Brand.name.like(pattern, escape="\\"),
                            )
                        ),
                    ]
                )
            conditions.append(or_(*term_conditions))
        return conditions

    async def list_in_stock_product_ids(self, product_ids: Sequence[int]) -> set[int]:
        if not product_ids:
            return set()
        statement = (
            select(ProductSku.product_id)
            .where(
                ProductSku.product_id.in_(product_ids),
                ProductSku.enabled.is_(True),
                ProductSku.stock > ProductSku.locked_stock,
            )
            .distinct()
        )
        return set((await self.session.scalars(statement)).all())

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

    async def list_product_skus(
        self, product_id: int, *, enabled_only: bool = True
    ) -> list[ProductSku]:
        statement = select(ProductSku).where(ProductSku.product_id == product_id)
        if enabled_only:
            statement = statement.where(ProductSku.enabled.is_(True))
        return list((await self.session.scalars(statement.order_by(ProductSku.id))).all())

    async def get_sku(self, sku_id: int, *, lock: bool = False) -> ProductSku | None:
        statement = select(ProductSku).where(ProductSku.id == sku_id)
        if lock:
            statement = statement.with_for_update()
        return (await self.session.execute(statement)).scalar_one_or_none()

    async def get_product_image(self, image_id: int) -> ProductImage | None:
        return await self.session.get(ProductImage, image_id)

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
