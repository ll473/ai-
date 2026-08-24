from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.api.v1.routes import catalog as catalog_routes
from backend.app.core.exceptions import AppError
from backend.app.models import Base
from backend.app.models.catalog import Brand, Category, Product, ProductSku
from backend.app.models.enums import ProductStatus
from backend.app.services.catalog import CatalogService


@asynccontextmanager
async def seeded_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            session.add_all(
                [
                    Category(id=10, name="数码影音", slug="digital"),
                    Category(id=20, name="办公效率", slug="office"),
                    Brand(id=1, name="EchoArc", slug="echoarc"),
                    Product(
                        id=1,
                        category_id=10,
                        name="耳机 A",
                        product_no="A-1",
                        status=ProductStatus.ON_SALE,
                    ),
                    Product(
                        id=2,
                        category_id=10,
                        brand_id=1,
                        name="耳机 B",
                        product_no="B-2",
                        status=ProductStatus.ON_SALE,
                    ),
                    Product(
                        id=3,
                        category_id=20,
                        name="办公椅",
                        product_no="C-3",
                        status=ProductStatus.ON_SALE,
                    ),
                    Product(
                        id=4,
                        category_id=10,
                        name="下架耳机",
                        product_no="D-4",
                        status=ProductStatus.OFF_SALE,
                    ),
                    ProductSku(
                        id=11,
                        product_id=1,
                        sku_no="A-1-S",
                        name="标准版",
                        price=Decimal("599.00"),
                        stock=5,
                        locked_stock=1,
                        enabled=True,
                    ),
                    ProductSku(
                        id=21,
                        product_id=2,
                        sku_no="B-2-S",
                        name="标准版",
                        price=Decimal("899.00"),
                        stock=9,
                        locked_stock=2,
                        enabled=True,
                    ),
                    ProductSku(
                        id=22,
                        product_id=2,
                        sku_no="B-2-X",
                        name="停用规格",
                        price=Decimal("999.00"),
                        stock=8,
                        locked_stock=0,
                        enabled=False,
                    ),
                ]
            )
            await session.commit()
            yield session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_compare_products_preserves_order_and_marks_unavailable() -> None:
    """Drops off-sale/missing products while preserving valid requested order."""
    async with seeded_session() as session:
        result = await CatalogService(session).compare_products([2, 999, 1, 4])

    assert [item.id for item in result.items] == [2, 1]
    assert result.unavailable_ids == [999, 4]
    assert result.items[0].category_name == "数码影音"
    assert result.items[0].brand_name == "EchoArc"
    assert result.items[0].total_available_stock == 7
    assert len(result.items[0].skus) == 1
    assert result.items[0].skus[0].name == "标准版"


@pytest.mark.asyncio
async def test_compare_products_public_json_excludes_internal_sku_fields() -> None:
    """Public comparison JSON exposes only comparison-safe SKU facts."""
    async with seeded_session() as session:
        result = await CatalogService(session).compare_products([1, 2])

    sku = result.model_dump(mode="json")["items"][0]["skus"][0]
    assert sku == {
        "name": "标准版",
        "attributes": None,
        "price": "599.00",
        "available_stock": 4,
    }
    assert {"stock", "locked_stock", "sku_no", "created_at"}.isdisjoint(sku)


@pytest.mark.asyncio
async def test_compare_products_rejects_cross_category_candidates() -> None:
    """Prevents comparison facts from mixing categories."""
    async with seeded_session() as session:
        with pytest.raises(AppError, match="只能对比同一分类商品") as captured:
            await CatalogService(session).compare_products([1, 3])

    assert captured.value.status_code == 422
    assert captured.value.code == "COMPARISON_CATEGORY_MISMATCH"


@pytest.mark.asyncio
async def test_compare_products_requires_two_to_four_unique_products() -> None:
    """Rejects lists that become invalid after duplicate IDs are removed."""
    async with seeded_session() as session:
        with pytest.raises(AppError, match="请选择 2–4 件商品进行对比") as captured:
            await CatalogService(session).compare_products([1, 1])

    assert captured.value.status_code == 422
    assert captured.value.code == "COMPARISON_SIZE_INVALID"


@pytest.mark.asyncio
async def test_compare_products_uses_exactly_two_selects() -> None:
    """Keeps the public comparison read bounded to products and enabled SKUs."""
    async with seeded_session() as session:
        select_count = 0

        def count_selects(
            _connection: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: object,
        ) -> None:
            nonlocal select_count
            if statement.lstrip().upper().startswith("SELECT"):
                select_count += 1

        event.listen(session.sync_session.bind, "before_cursor_execute", count_selects)
        try:
            await CatalogService(session).compare_products([1, 2])
        finally:
            event.remove(session.sync_session.bind, "before_cursor_execute", count_selects)

    assert select_count == 2


def test_compare_route_precedes_dynamic_product_route() -> None:
    """Keeps the static comparison path from being captured as a product ID."""
    paths = [route.path for route in catalog_routes.router.routes]

    assert paths.index("/catalog/products/compare") < paths.index("/catalog/products/{product_id}")
