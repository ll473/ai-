from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.catalog import Category, Product, ProductSku
from backend.app.models.enums import OrderStatus, ProductStatus
from backend.app.models.trade import CartItem
from backend.app.models.user import User, UserAddress, Wallet
from backend.app.schemas.trade import CheckoutRequest, ReviewCreate
from backend.app.services.trade import TradeService


@pytest.mark.asyncio
async def test_cart_order_wallet_payment_closes_inventory_loop() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Wallet(id=1, user_id=1, balance=Decimal("0.00")),
                UserAddress(
                    id=1,
                    user_id=1,
                    receiver_name="张三",
                    receiver_phone="13800000000",
                    province="浙江省",
                    city="杭州市",
                    district="西湖区",
                    detail="测试路 1 号",
                    is_default=True,
                ),
                Category(id=1, name="数码", slug="digital"),
                Product(
                    id=1,
                    category_id=1,
                    name="测试商品",
                    product_no="P001",
                    min_price=Decimal("10.00"),
                    max_price=Decimal("10.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="SKU001",
                    name="标准款",
                    price=Decimal("10.00"),
                    stock=10,
                    locked_stock=0,
                    enabled=True,
                ),
                CartItem(id=1, user_id=1, product_id=1, sku_id=1, quantity=2, selected=True),
            ]
        )
        await session.commit()

        service = TradeService(session)
        favorite = await service.add_favorite(1, 1)
        assert favorite.id == 1
        assert await service.is_favorite(1, 1) is True
        favorites = await service.list_favorites(1, page=1, page_size=20)
        assert favorites.total == 1
        assert favorites.items[0].name == "测试商品"
        await service.remove_favorite(1, 1)
        assert await service.is_favorite(1, 1) is False

        order = await service.create_order(1, CheckoutRequest(address_id=1))
        assert order.status == OrderStatus.PENDING_PAYMENT
        assert order.payable_amount == Decimal("20.00")
        assert (await service.get_cart(1)).items == []

        reserved_sku = await session.get(ProductSku, 1)
        assert reserved_sku is not None
        assert reserved_sku.stock == 10
        assert reserved_sku.locked_stock == 2

        wallet = await service.recharge_wallet(1, Decimal("50.00"))
        assert wallet.balance == Decimal("50.00")
        payment = await service.pay_order(1, order.id)

        assert payment.order.status == OrderStatus.PAID
        assert payment.wallet_balance == Decimal("30.00")
        await session.refresh(reserved_sku)
        assert reserved_sku.stock == 8
        assert reserved_sku.locked_stock == 0

        shipped = await service.ship_order(order.id)
        assert shipped.status == OrderStatus.SHIPPED
        completed = await service.complete_order(1, order.id)
        assert completed.status == OrderStatus.COMPLETED
        assert completed.items[0].reviewed is False

        buyer = await session.get(User, 1)
        assert buyer is not None
        review = await service.create_review(
            buyer,
            ReviewCreate(
                order_item_id=completed.items[0].id,
                rating=5,
                content="坐感扎实，安装说明清楚。",
            ),
        )
        assert review.rating == 5
        reviews = await service.list_product_reviews(1, page=1, page_size=20)
        assert reviews.total == 1
        assert reviews.items[0].display_name == "buyer"
        product = await session.get(Product, 1)
        assert product is not None
        assert product.rating == Decimal("5.00")
        assert product.review_count == 1

    await engine.dispose()
