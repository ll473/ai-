from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.catalog import Category, Product, ProductImage, ProductSku
from backend.app.models.enums import ProductStatus
from backend.app.services.catalog import CatalogService


@pytest.mark.asyncio
async def test_product_detail_serializes_skus_from_database_models() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                Category(id=1, name="Office", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="Ergonomic chair",
                    product_no="CHAIR-001",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductImage(
                    id=1,
                    product_id=1,
                    image_url="/uploads/chair.png",
                    alt_text="Chair",
                    sort_order=0,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="CHAIR-BLACK",
                    name="Black",
                    price=Decimal("1299.00"),
                    stock=10,
                    locked_stock=3,
                    enabled=True,
                ),
            ]
        )
        await session.commit()

        detail = await CatalogService(session).get_product_detail(1)

        assert detail.id == 1
        assert detail.images[0].image_url == "/uploads/chair.png"
        assert detail.skus[0].sku_no == "CHAIR-BLACK"
        assert detail.skus[0].available_stock == 7

    await engine.dispose()
