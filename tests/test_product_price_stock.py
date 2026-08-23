from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.exceptions import NotFoundError
from backend.app.models import Base
from backend.app.models.catalog import Category, Product, ProductSku
from backend.app.models.enums import ProductStatus, PromotionType, StepStatus
from backend.app.models.trade import Promotion
from backend.app.services.ai_management import AiManagementService
from backend.app.services.product_price_stock import ProductPriceStockService
from backend.app.services.tool_center import ToolCenter, ToolContext


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


def product(*, product_id: int = 1, status: ProductStatus = ProductStatus.ON_SALE) -> Product:
    return Product(
        id=product_id,
        category_id=1,
        name="测试商品",
        product_no=f"PRODUCT-{product_id}",
        min_price=Decimal("400.00"),
        max_price=Decimal("600.00"),
        status=status,
    )


def sku(
    *,
    sku_id: int,
    product_id: int = 1,
    price: str,
    stock: int,
    locked_stock: int,
    enabled: bool = True,
) -> ProductSku:
    return ProductSku(
        id=sku_id,
        product_id=product_id,
        sku_no=f"SKU-{sku_id}",
        name=f"规格 {sku_id}",
        attributes={"sequence": sku_id},
        price=Decimal(price),
        stock=stock,
        locked_stock=locked_stock,
        enabled=enabled,
    )


def fixed_promotion(*, product_id: int = 1) -> Promotion:
    now = datetime.now(UTC)
    return Promotion(
        id=1,
        name="商品满五百减一百",
        product_id=product_id,
        promotion_type=PromotionType.FIXED,
        value=Decimal("100.00"),
        minimum_amount=Decimal("500.00"),
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
        enabled=True,
    )


async def seed_promoted_product(session: AsyncSession) -> None:
    session.add_all(
        [
            Category(id=1, name="测试分类", slug="test"),
            product(),
            sku(sku_id=1, price="400.00", stock=3, locked_stock=3),
            sku(sku_id=2, price="600.00", stock=10, locked_stock=3),
            fixed_promotion(),
        ]
    )
    await session.commit()


@pytest.mark.asyncio
async def test_service_calculates_stock_and_promotion_for_each_sku(
    session: AsyncSession,
) -> None:
    await seed_promoted_product(session)

    result = await ProductPriceStockService(session).get(1)

    assert result.product_name == "测试商品"
    assert [item.available_stock for item in result.skus] == [0, 7]
    assert result.skus[0].promotion is None
    assert result.skus[1].promotion is not None
    assert result.skus[1].promotion.discount_amount == Decimal("100.00")


@pytest.mark.asyncio
async def test_service_returns_empty_skus_when_all_are_disabled(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            Category(id=1, name="测试分类", slug="test"),
            product(),
            sku(
                sku_id=1,
                price="400.00",
                stock=3,
                locked_stock=0,
                enabled=False,
            ),
        ]
    )
    await session.commit()

    result = await ProductPriceStockService(session).get(1)

    assert result.skus == ()


@pytest.mark.asyncio
async def test_service_rejects_off_sale_product(session: AsyncSession) -> None:
    session.add_all(
        [
            Category(id=1, name="测试分类", slug="test"),
            product(status=ProductStatus.OFF_SALE),
        ]
    )
    await session.commit()

    with pytest.raises(NotFoundError, match="商品不存在或已下架"):
        await ProductPriceStockService(session).get(1)


@pytest.mark.asyncio
async def test_tool_center_returns_promotion_on_each_sku_only(
    session: AsyncSession,
) -> None:
    await seed_promoted_product(session)
    await AiManagementService(session).seed_builtin_tools()

    execution = await ToolCenter(session).execute_by_name(
        "get_product_price_stock",
        {"product_id": 1},
        ToolContext(),
    )

    assert execution.status == StepStatus.SUCCEEDED
    assert execution.result is not None
    assert "promotion" not in execution.result
    assert execution.result["skus"][0]["promotion"] is None
    assert execution.result["skus"][1]["promotion"]["discount_amount"] == "100.00"
