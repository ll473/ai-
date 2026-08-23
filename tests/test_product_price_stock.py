from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.api.v1.routes.ai import product_question
from backend.app.core.exceptions import NotFoundError
from backend.app.models import Base
from backend.app.models.ai import FunctionTool
from backend.app.models.catalog import Category, Product, ProductSku
from backend.app.models.enums import ProductStatus, PromotionType, QuestionType, StepStatus
from backend.app.models.trade import Promotion
from backend.app.models.user import User
from backend.app.schemas.ai import ProductQuestionRequest
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "product_status",
    [None, ProductStatus.OFF_SALE],
    ids=["missing", "off-sale"],
)
async def test_tool_center_preserves_missing_or_off_sale_business_error(
    session: AsyncSession,
    product_status: ProductStatus | None,
) -> None:
    if product_status is not None:
        session.add_all(
            [
                Category(id=1, name="测试分类", slug="test"),
                product(status=product_status),
            ]
        )
        await session.commit()
    await AiManagementService(session).seed_builtin_tools()

    execution = await ToolCenter(session).execute_by_name(
        "get_product_price_stock",
        {"product_id": 1},
        ToolContext(),
    )

    assert execution.status == StepStatus.FAILED
    assert execution.result is None
    assert execution.error_message == "商品不存在或已下架"


async def seed_consumer_price_stock_data(
    session: AsyncSession, *, disabled_tool: bool
) -> User:
    user = User(
        id=1,
        username="price-stock-user",
        password_hash="test-hash",
    )
    session.add_all(
        [
            user,
            Category(id=1, name="测试分类", slug="test"),
            product(),
            ProductSku(
                id=1,
                product_id=1,
                sku_no="SKU-STANDARD",
                name="标准款",
                attributes={"version": "standard"},
                price=Decimal("600.00"),
                stock=10,
                locked_stock=3,
                enabled=True,
            ),
            fixed_promotion(),
        ]
    )
    if disabled_tool:
        session.add(
            FunctionTool(
                name="get_product_price_stock",
                display_name="查询商品价格库存",
                description="禁用状态不应影响消费者问答",
                input_schema={"type": "object"},
                executor="catalog.get_product_price_stock",
                enabled=False,
            )
        )
    await session.commit()
    return user


async def assert_consumer_price_stock_answer(
    session: AsyncSession, user: User
) -> None:
    response = await product_question(
        ProductQuestionRequest(
            question="这个商品各规格多少钱，还有库存吗？",
            question_type=QuestionType.PRICE_STOCK,
            product_id=1,
        ),
        session,
        user,
    )

    assert response.data is not None
    assert "标准款：¥600.00，可售库存 7 件" in response.data.answer
    assert "优惠" in response.data.answer


@pytest.mark.asyncio
async def test_consumer_price_stock_works_without_function_tool(
    session: AsyncSession,
) -> None:
    user = await seed_consumer_price_stock_data(session, disabled_tool=False)

    await assert_consumer_price_stock_answer(session, user)


@pytest.mark.asyncio
async def test_consumer_price_stock_ignores_disabled_function_tool(
    session: AsyncSession,
) -> None:
    user = await seed_consumer_price_stock_data(session, disabled_tool=True)

    await assert_consumer_price_stock_answer(session, user)
