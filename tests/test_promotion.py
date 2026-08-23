from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.enums import PromotionType
from backend.app.models.trade import Promotion
from backend.app.services.promotion import PromotionLine, best_order_promotion


NOW = datetime.now(UTC)


def promotion(
    *,
    name: str,
    product_id: int | None,
    promotion_type: PromotionType,
    value: str,
    minimum: str = "0.00",
    priority: int = 0,
) -> Promotion:
    return Promotion(
        name=name,
        product_id=product_id,
        promotion_type=promotion_type,
        value=Decimal(value),
        minimum_amount=Decimal(minimum),
        starts_at=NOW - timedelta(days=1),
        ends_at=NOW + timedelta(days=1),
        priority=priority,
        enabled=True,
    )


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


@pytest.mark.asyncio
async def test_global_fixed_promotion_applies_once_across_multiple_lines(
    session: AsyncSession,
) -> None:
    session.add(
        promotion(
            name="全场立减",
            product_id=None,
            promotion_type=PromotionType.FIXED,
            value="20.00",
        )
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [
            PromotionLine(product_id=1, amount=Decimal("60.00")),
            PromotionLine(product_id=2, amount=Decimal("60.00")),
        ],
        at=NOW,
    )

    assert result.strategy == "GLOBAL"
    assert result.discount_amount == Decimal("20.00")
    assert len(result.promotions) == 1


@pytest.mark.asyncio
async def test_product_promotion_aggregates_multiple_skus_of_same_product(
    session: AsyncSession,
) -> None:
    session.add(
        promotion(
            name="商品满减",
            product_id=1,
            promotion_type=PromotionType.FIXED,
            value="30.00",
            minimum="100.00",
        )
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [
            PromotionLine(product_id=1, amount=Decimal("60.00")),
            PromotionLine(product_id=1, amount=Decimal("60.00")),
        ],
        at=NOW,
    )

    assert result.strategy == "PRODUCT"
    assert result.discount_amount == Decimal("30.00")
    assert len(result.promotions) == 1


@pytest.mark.asyncio
async def test_product_plan_can_beat_global_plan(session: AsyncSession) -> None:
    session.add_all(
        [
            promotion(
                name="全场减三十",
                product_id=None,
                promotion_type=PromotionType.FIXED,
                value="30.00",
            ),
            promotion(
                name="商品一减二十",
                product_id=1,
                promotion_type=PromotionType.FIXED,
                value="20.00",
            ),
            promotion(
                name="商品二减二十",
                product_id=2,
                promotion_type=PromotionType.FIXED,
                value="20.00",
            ),
        ]
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [
            PromotionLine(product_id=1, amount=Decimal("50.00")),
            PromotionLine(product_id=2, amount=Decimal("50.00")),
        ],
        at=NOW,
    )

    assert result.strategy == "PRODUCT"
    assert result.discount_amount == Decimal("40.00")
    assert {item.name for item in result.promotions} == {"商品一减二十", "商品二减二十"}


@pytest.mark.asyncio
async def test_global_plan_wins_equal_discount_and_caps_at_order_amount(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            promotion(
                name="全场大额立减",
                product_id=None,
                promotion_type=PromotionType.FIXED,
                value="100.00",
            ),
            promotion(
                name="商品大额立减",
                product_id=1,
                promotion_type=PromotionType.FIXED,
                value="100.00",
            ),
        ]
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [PromotionLine(product_id=1, amount=Decimal("50.00"))],
        at=NOW,
    )

    assert result.strategy == "GLOBAL"
    assert result.discount_amount == Decimal("50.00")


@pytest.mark.asyncio
async def test_no_active_promotion_returns_zero(session: AsyncSession) -> None:
    result = await best_order_promotion(
        session,
        [PromotionLine(product_id=1, amount=Decimal("50.00"))],
        at=NOW,
    )

    assert result.strategy == "NONE"
    assert result.discount_amount == Decimal("0.00")
    assert result.promotions == ()
