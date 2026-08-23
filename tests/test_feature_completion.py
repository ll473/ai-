from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.catalog import Category, Product, ProductSku
from backend.app.models.enums import ProductStatus, PromotionType
from backend.app.models.trade import Promotion
from backend.app.services.promotion import best_promotion


@pytest.mark.asyncio
async def test_best_promotion_uses_largest_valid_discount() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="办公", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR001",
                    min_price=Decimal("1000.00"),
                    max_price=Decimal("1000.00"),
                    rating=Decimal("5.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="CHAIR-SKU",
                    name="标准款",
                    price=Decimal("1000.00"),
                    stock=10,
                    enabled=True,
                ),
                Promotion(
                    name="九折",
                    product_id=None,
                    promotion_type=PromotionType.PERCENT,
                    value=Decimal("10.00"),
                    minimum_amount=Decimal("0.00"),
                    starts_at=now - timedelta(days=1),
                    ends_at=now + timedelta(days=1),
                    enabled=True,
                ),
                Promotion(
                    name="单品立减",
                    product_id=1,
                    promotion_type=PromotionType.FIXED,
                    value=Decimal("150.00"),
                    minimum_amount=Decimal("500.00"),
                    starts_at=now - timedelta(days=1),
                    ends_at=now + timedelta(days=1),
                    enabled=True,
                ),
            ]
        )
        await session.commit()

        applied = await best_promotion(session, 1, Decimal("1000.00"), at=now)
        assert applied is not None
        assert applied.name == "单品立减"
        assert applied.discount_amount == Decimal("150.00")

    await engine.dispose()
