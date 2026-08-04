from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.catalog import Favorite, Product, ProductSku
from backend.app.models.enums import OrderStatus, ProductStatus
from backend.app.models.trade import CartItem, Order, OrderItem, Review
from backend.app.models.user import User, UserAddress, Wallet, WalletTransaction

CartRow = tuple[CartItem, Product, ProductSku]
ReviewRow = tuple[Review, User]
AdminReviewRow = tuple[Review, User, Product]


class TradeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_addresses(self, user_id: int) -> list[UserAddress]:
        statement = (
            select(UserAddress)
            .where(UserAddress.user_id == user_id)
            .order_by(UserAddress.is_default.desc(), UserAddress.created_at.desc())
        )
        return list((await self.session.scalars(statement)).all())

    async def list_favorites(
        self, user_id: int, *, page: int, page_size: int
    ) -> tuple[list[Product], int]:
        base = (
            select(Product)
            .join(Favorite, Favorite.product_id == Product.id)
            .where(Favorite.user_id == user_id, Product.status == ProductStatus.ON_SALE)
        )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(Favorite.created_at.desc(), Favorite.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.scalars(statement)).all()), total

    async def get_favorite(self, user_id: int, product_id: int) -> Favorite | None:
        result = await self.session.execute(
            select(Favorite).where(
                Favorite.user_id == user_id,
                Favorite.product_id == product_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_address(self, user_id: int, address_id: int) -> UserAddress | None:
        result = await self.session.execute(
            select(UserAddress).where(
                UserAddress.id == address_id, UserAddress.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def clear_default_addresses(self, user_id: int, *, exclude_id: int | None = None) -> None:
        statement = update(UserAddress).where(UserAddress.user_id == user_id)
        if exclude_id is not None:
            statement = statement.where(UserAddress.id != exclude_id)
        await self.session.execute(statement.values(is_default=False))

    async def list_cart_rows(self, user_id: int, *, selected_only: bool = False) -> list[CartRow]:
        statement = (
            select(CartItem, Product, ProductSku)
            .join(Product, Product.id == CartItem.product_id)
            .join(ProductSku, ProductSku.id == CartItem.sku_id)
            .where(CartItem.user_id == user_id)
        )
        if selected_only:
            statement = statement.where(CartItem.selected.is_(True))
        result = await self.session.execute(statement.order_by(CartItem.created_at.desc()))
        return list(result.tuples().all())

    async def get_cart_item(self, user_id: int, item_id: int) -> CartItem | None:
        result = await self.session.execute(
            select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_cart_item_by_sku(self, user_id: int, sku_id: int) -> CartItem | None:
        result = await self.session.execute(
            select(CartItem).where(CartItem.user_id == user_id, CartItem.sku_id == sku_id)
        )
        return result.scalar_one_or_none()

    async def get_product_sku(
        self, sku_id: int, *, lock: bool = False
    ) -> tuple[Product, ProductSku] | None:
        statement = (
            select(Product, ProductSku)
            .join(ProductSku, ProductSku.product_id == Product.id)
            .where(ProductSku.id == sku_id)
        )
        if lock:
            statement = statement.with_for_update()
        row = (await self.session.execute(statement)).tuples().one_or_none()
        return row

    async def lock_skus(self, sku_ids: list[int]) -> dict[int, ProductSku]:
        statement = (
            select(ProductSku)
            .where(ProductSku.id.in_(sorted(set(sku_ids))))
            .order_by(ProductSku.id)
            .with_for_update()
        )
        return {sku.id: sku for sku in (await self.session.scalars(statement)).all()}

    async def get_wallet(self, user_id: int, *, lock: bool = False) -> Wallet | None:
        statement = select(Wallet).where(Wallet.user_id == user_id)
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_wallet_transactions(
        self, user_id: int, *, page: int, page_size: int
    ) -> tuple[list[WalletTransaction], int]:
        base = (
            select(WalletTransaction)
            .join(Wallet, Wallet.id == WalletTransaction.wallet_id)
            .where(Wallet.user_id == user_id)
        )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(WalletTransaction.created_at.desc(), WalletTransaction.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.scalars(statement)).all()), total

    async def list_orders(
        self, user_id: int, *, page: int, page_size: int
    ) -> tuple[list[Order], int]:
        base = select(Order).where(Order.user_id == user_id)
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.scalars(statement)).all()), total

    async def list_admin_orders(
        self,
        *,
        page: int,
        page_size: int,
        order_status: OrderStatus | None = None,
    ) -> tuple[list[Order], int]:
        base = select(Order)
        if order_status is not None:
            base = base.where(Order.status == order_status)
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(Order.created_at.desc(), Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.scalars(statement)).all()), total

    async def get_order(self, user_id: int, order_id: int, *, lock: bool = False) -> Order | None:
        statement = select(Order).where(Order.id == order_id, Order.user_id == user_id)
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_admin_order(self, order_id: int, *, lock: bool = False) -> Order | None:
        statement = select(Order).where(Order.id == order_id)
        if lock:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_order_items(self, order_id: int) -> list[OrderItem]:
        return list(
            (
                await self.session.scalars(
                    select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.id)
                )
            ).all()
        )

    async def get_order_item_for_user(
        self, user_id: int, order_item_id: int
    ) -> tuple[Order, OrderItem] | None:
        statement = (
            select(Order, OrderItem)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(Order.user_id == user_id, OrderItem.id == order_item_id)
        )
        return (await self.session.execute(statement)).tuples().one_or_none()

    async def reviewed_order_item_ids(self, order_id: int) -> set[int]:
        statement = (
            select(Review.order_item_id)
            .join(OrderItem, OrderItem.id == Review.order_item_id)
            .where(OrderItem.order_id == order_id)
        )
        return set((await self.session.scalars(statement)).all())

    async def get_review_by_order_item(self, order_item_id: int) -> Review | None:
        result = await self.session.execute(
            select(Review).where(Review.order_item_id == order_item_id)
        )
        return result.scalar_one_or_none()

    async def list_product_reviews(
        self, product_id: int, *, page: int, page_size: int
    ) -> tuple[list[ReviewRow], int]:
        base = (
            select(Review, User)
            .join(User, User.id == Review.user_id)
            .where(Review.product_id == product_id, Review.visible.is_(True))
        )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(Review.created_at.desc(), Review.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(statement)).tuples().all()), total

    async def list_admin_reviews(
        self, *, page: int, page_size: int
    ) -> tuple[list[AdminReviewRow], int]:
        base = (
            select(Review, User, Product)
            .join(User, User.id == Review.user_id)
            .join(Product, Product.id == Review.product_id)
        )
        total = int(
            await self.session.scalar(
                select(func.count()).select_from(base.order_by(None).subquery())
            )
            or 0
        )
        statement = (
            base.order_by(Review.created_at.desc(), Review.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list((await self.session.execute(statement)).tuples().all()), total

    async def get_review(self, review_id: int) -> Review | None:
        return await self.session.get(Review, review_id)

    def add(self, entity: object) -> None:
        self.session.add(entity)

    async def delete(self, entity: object) -> None:
        await self.session.delete(entity)
