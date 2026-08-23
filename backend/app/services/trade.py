import secrets
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import ConflictError, NotFoundError
from backend.app.models.catalog import Favorite, Product, ProductSku
from backend.app.models.enums import (
    OrderStatus,
    PaymentStatus,
    ProductStatus,
    WalletTransactionType,
)
from backend.app.models.trade import CartItem, Order, OrderItem, PaymentTransaction, Review
from backend.app.models.user import User, UserAddress, Wallet, WalletTransaction
from backend.app.repositories.trade import CartRow, TradeRepository
from backend.app.schemas.catalog import ProductSummary
from backend.app.schemas.common import PageData
from backend.app.schemas.trade import (
    AddressCreate,
    AddressPublic,
    AddressUpdate,
    AdminOrderDetail,
    AdminOrderSummary,
    CartAddRequest,
    CartItemPublic,
    CartSummary,
    CartUpdateRequest,
    CheckoutRequest,
    OrderDetail,
    OrderItemPublic,
    OrderSummary,
    PaymentResult,
    ReviewAdmin,
    ReviewCreate,
    ReviewPublic,
    WalletPublic,
    WalletTransactionPublic,
)
from backend.app.services.promotion import PromotionLine, best_order_promotion

MONEY_STEP = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


def _business_no(prefix: str) -> str:
    timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}{timestamp}{secrets.token_hex(4).upper()}"


def _cart_item_public(row: CartRow) -> CartItemPublic:
    item, product, sku = row
    available_stock = max(0, sku.stock - sku.locked_stock)
    available = (
        product.status == ProductStatus.ON_SALE
        and sku.enabled
        and available_stock >= item.quantity
    )
    return CartItemPublic(
        id=item.id,
        product_id=product.id,
        sku_id=sku.id,
        product_name=product.name,
        sku_name=sku.name,
        sku_attributes=sku.attributes,
        image_url=product.main_image_url,
        unit_price=sku.price,
        quantity=item.quantity,
        selected=item.selected,
        available_stock=available_stock,
        available=available,
        subtotal=_money(sku.price * item.quantity),
    )


def _review_public(review: Review, user: User) -> ReviewPublic:
    return ReviewPublic(
        id=review.id,
        product_id=review.product_id,
        rating=review.rating,
        content=review.content,
        image_urls=review.image_urls,
        anonymous=review.anonymous,
        display_name="匿名用户" if review.anonymous else (user.nickname or user.username),
        created_at=review.created_at,
    )


class TradeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trade = TradeRepository(session)

    async def list_favorites(
        self, user_id: int, *, page: int, page_size: int
    ) -> PageData[ProductSummary]:
        products, total = await self.trade.list_favorites(
            user_id, page=page, page_size=page_size
        )
        return PageData(
            items=[ProductSummary.model_validate(product) for product in products],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def is_favorite(self, user_id: int, product_id: int) -> bool:
        return await self.trade.get_favorite(user_id, product_id) is not None

    async def add_favorite(self, user_id: int, product_id: int) -> ProductSummary:
        product = await self.session.get(Product, product_id)
        if product is None or product.status != ProductStatus.ON_SALE:
            raise NotFoundError("商品不存在或已下架")
        favorite = await self.trade.get_favorite(user_id, product_id)
        if favorite is None:
            self.trade.add(Favorite(user_id=user_id, product_id=product_id))
            await self.session.commit()
        return ProductSummary.model_validate(product)

    async def remove_favorite(self, user_id: int, product_id: int) -> None:
        favorite = await self.trade.get_favorite(user_id, product_id)
        if favorite is None:
            return
        await self.trade.delete(favorite)
        await self.session.commit()

    async def list_addresses(self, user_id: int) -> list[AddressPublic]:
        addresses = await self.trade.list_addresses(user_id)
        return [AddressPublic.model_validate(address) for address in addresses]

    async def create_address(self, user_id: int, payload: AddressCreate) -> AddressPublic:
        existing = await self.trade.list_addresses(user_id)
        values = payload.model_dump()
        values["is_default"] = payload.is_default or not existing
        if values["is_default"]:
            await self.trade.clear_default_addresses(user_id)
        address = UserAddress(user_id=user_id, **values)
        self.trade.add(address)
        await self.session.commit()
        await self.session.refresh(address)
        return AddressPublic.model_validate(address)

    async def update_address(
        self, user_id: int, address_id: int, payload: AddressUpdate
    ) -> AddressPublic:
        address = await self.trade.get_address(user_id, address_id)
        if address is None:
            raise NotFoundError("收货地址不存在")
        changes = payload.model_dump(exclude_unset=True)
        if changes.get("is_default"):
            await self.trade.clear_default_addresses(user_id, exclude_id=address_id)
        for field, value in changes.items():
            setattr(address, field, value)
        await self.session.commit()
        await self.session.refresh(address)
        return AddressPublic.model_validate(address)

    async def delete_address(self, user_id: int, address_id: int) -> None:
        address = await self.trade.get_address(user_id, address_id)
        if address is None:
            raise NotFoundError("收货地址不存在")
        was_default = address.is_default
        await self.trade.delete(address)
        await self.session.flush()
        if was_default:
            remaining = await self.trade.list_addresses(user_id)
            if remaining:
                remaining[0].is_default = True
        await self.session.commit()

    async def get_cart(self, user_id: int) -> CartSummary:
        items = [_cart_item_public(row) for row in await self.trade.list_cart_rows(user_id)]
        selected_items = [item for item in items if item.selected and item.available]
        return CartSummary(
            items=items,
            total_count=sum(item.quantity for item in items),
            selected_count=sum(item.quantity for item in selected_items),
            selected_amount=_money(sum((item.subtotal for item in selected_items), Decimal("0"))),
        )

    async def add_to_cart(self, user_id: int, payload: CartAddRequest) -> CartSummary:
        product_sku = await self.trade.get_product_sku(payload.sku_id)
        if product_sku is None:
            raise NotFoundError("商品规格不存在")
        product, sku = product_sku
        if product.status != ProductStatus.ON_SALE or not sku.enabled:
            raise ConflictError("商品或规格已下架")
        item = await self.trade.get_cart_item_by_sku(user_id, sku.id)
        target_quantity = payload.quantity + (item.quantity if item else 0)
        if target_quantity > max(0, sku.stock - sku.locked_stock):
            raise ConflictError("可售库存不足")
        if item:
            item.quantity = target_quantity
            item.selected = True
        else:
            self.trade.add(
                CartItem(
                    user_id=user_id,
                    product_id=product.id,
                    sku_id=sku.id,
                    quantity=payload.quantity,
                    selected=True,
                )
            )
        await self.session.commit()
        return await self.get_cart(user_id)

    async def update_cart_item(
        self, user_id: int, item_id: int, payload: CartUpdateRequest
    ) -> CartSummary:
        item = await self.trade.get_cart_item(user_id, item_id)
        if item is None:
            raise NotFoundError("购物车商品不存在")
        if payload.quantity is not None:
            product_sku = await self.trade.get_product_sku(item.sku_id)
            if product_sku is None:
                raise NotFoundError("商品规格不存在")
            product, sku = product_sku
            if (
                product.status != ProductStatus.ON_SALE
                or not sku.enabled
                or payload.quantity > max(0, sku.stock - sku.locked_stock)
            ):
                raise ConflictError("商品已下架或可售库存不足")
            item.quantity = payload.quantity
        if payload.selected is not None:
            item.selected = payload.selected
        await self.session.commit()
        return await self.get_cart(user_id)

    async def select_all_cart_items(self, user_id: int, selected: bool) -> CartSummary:
        rows = await self.trade.list_cart_rows(user_id)
        for item, product, sku in rows:
            item.selected = (
                selected
                and product.status == ProductStatus.ON_SALE
                and sku.enabled
                and sku.stock - sku.locked_stock >= item.quantity
            )
        await self.session.commit()
        return await self.get_cart(user_id)

    async def delete_cart_item(self, user_id: int, item_id: int) -> CartSummary:
        item = await self.trade.get_cart_item(user_id, item_id)
        if item is None:
            raise NotFoundError("购物车商品不存在")
        await self.trade.delete(item)
        await self.session.commit()
        return await self.get_cart(user_id)

    async def get_wallet(self, user_id: int) -> WalletPublic:
        wallet = await self._wallet_or_create(user_id)
        return WalletPublic(balance=wallet.balance)

    async def recharge_wallet(self, user_id: int, amount: Decimal) -> WalletPublic:
        wallet = await self.trade.get_wallet(user_id, lock=True)
        if wallet is None:
            wallet = Wallet(user_id=user_id)
            self.trade.add(wallet)
            await self.session.flush()
        amount = _money(amount)
        balance_before = wallet.balance
        wallet.balance = _money(wallet.balance + amount)
        wallet.version += 1
        self.trade.add(
            WalletTransaction(
                wallet_id=wallet.id,
                transaction_no=_business_no("WT"),
                transaction_type=WalletTransactionType.RECHARGE,
                amount=amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                reference_type="RECHARGE",
                remark="用户余额充值",
            )
        )
        await self.session.commit()
        return WalletPublic(balance=wallet.balance)

    async def list_wallet_transactions(
        self, user_id: int, *, page: int, page_size: int
    ) -> PageData[WalletTransactionPublic]:
        transactions, total = await self.trade.list_wallet_transactions(
            user_id, page=page, page_size=page_size
        )
        return PageData(
            items=[WalletTransactionPublic.model_validate(item) for item in transactions],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def create_order(self, user_id: int, payload: CheckoutRequest) -> OrderDetail:
        address = await self.trade.get_address(user_id, payload.address_id)
        if address is None:
            raise NotFoundError("收货地址不存在")
        cart_rows = await self.trade.list_cart_rows(user_id, selected_only=True, lock=True)
        if not cart_rows:
            raise ConflictError("请先选择要结算的购物车商品")
        sku_map = await self.trade.lock_skus([sku.id for _, _, sku in cart_rows])

        product_amount = Decimal("0")
        promotion_lines: list[PromotionLine] = []
        order_lines: list[tuple[CartItem, Product, ProductSku]] = []
        for cart_item, product, original_sku in cart_rows:
            sku = sku_map.get(original_sku.id)
            if sku is None or sku.product_id != product.id:
                raise ConflictError("商品规格数据已变化，请刷新购物车")
            available_stock = sku.stock - sku.locked_stock
            if (
                product.status != ProductStatus.ON_SALE
                or not sku.enabled
                or cart_item.quantity > available_stock
            ):
                raise ConflictError(f"“{product.name} / {sku.name}”已下架或库存不足")
            line_amount = _money(sku.price * cart_item.quantity)
            product_amount += line_amount
            promotion_lines.append(PromotionLine(product_id=product.id, amount=line_amount))
            order_lines.append((cart_item, product, sku))

        product_amount = _money(product_amount)
        promotion_result = await best_order_promotion(self.session, promotion_lines)
        discount_amount = promotion_result.discount_amount
        order = Order(
            order_no=_business_no("O"),
            user_id=user_id,
            status=OrderStatus.PENDING_PAYMENT,
            address_snapshot={
                "receiver_name": address.receiver_name,
                "receiver_phone": address.receiver_phone,
                "province": address.province,
                "city": address.city,
                "district": address.district,
                "detail": address.detail,
                "postal_code": address.postal_code,
            },
            product_amount=product_amount,
            discount_amount=discount_amount,
            payable_amount=_money(max(Decimal("0"), product_amount - discount_amount)),
            buyer_remark=payload.buyer_remark,
        )
        self.trade.add(order)
        await self.session.flush()

        for cart_item, product, sku in order_lines:
            sku.locked_stock += cart_item.quantity
            sku.version += 1
            self.trade.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    sku_id=sku.id,
                    product_name=product.name,
                    sku_name=sku.name,
                    sku_attributes=sku.attributes,
                    image_url=product.main_image_url,
                    unit_price=sku.price,
                    quantity=cart_item.quantity,
                    total_amount=_money(sku.price * cart_item.quantity),
                )
            )
            await self.trade.delete(cart_item)

        await self.session.commit()
        await self.session.refresh(order)
        return await self._order_detail(order)

    async def list_orders(
        self, user_id: int, *, page: int, page_size: int
    ) -> PageData[OrderSummary]:
        orders, total = await self.trade.list_orders(user_id, page=page, page_size=page_size)
        return PageData(
            items=[OrderSummary.model_validate(order) for order in orders],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_order(self, user_id: int, order_id: int) -> OrderDetail:
        order = await self.trade.get_order(user_id, order_id)
        if order is None:
            raise NotFoundError("订单不存在")
        return await self._order_detail(order)

    async def pay_order(self, user_id: int, order_id: int) -> PaymentResult:
        order = await self.trade.get_order(user_id, order_id, lock=True)
        if order is None:
            raise NotFoundError("订单不存在")
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise ConflictError("订单当前状态不可支付")
        wallet = await self.trade.get_wallet(user_id, lock=True)
        if wallet is None or wallet.balance < order.payable_amount:
            raise ConflictError("钱包余额不足，请先充值")
        items = await self.trade.list_order_items(order.id)
        sku_map = await self.trade.lock_skus([item.sku_id for item in items])
        for item in items:
            sku = sku_map.get(item.sku_id)
            if sku is None or sku.locked_stock < item.quantity or sku.stock < item.quantity:
                raise ConflictError("订单预占库存异常，请联系管理员")

        paid_at = datetime.now(UTC)
        balance_before = wallet.balance
        wallet.balance = _money(wallet.balance - order.payable_amount)
        wallet.version += 1
        payment_no = _business_no("P")
        self.trade.add(
            WalletTransaction(
                wallet_id=wallet.id,
                transaction_no=_business_no("WT"),
                transaction_type=WalletTransactionType.PAYMENT,
                amount=-order.payable_amount,
                balance_before=balance_before,
                balance_after=wallet.balance,
                reference_type="ORDER",
                reference_id=order.order_no,
                remark="订单余额支付",
            )
        )
        self.trade.add(
            PaymentTransaction(
                payment_no=payment_no,
                order_id=order.id,
                user_id=user_id,
                amount=order.payable_amount,
                status=PaymentStatus.SUCCESS,
                paid_at=paid_at,
            )
        )
        for item in items:
            sku = sku_map[item.sku_id]
            sku.stock -= item.quantity
            sku.locked_stock -= item.quantity
            sku.version += 1
            await self.session.execute(
                update(Product)
                .where(Product.id == item.product_id)
                .values(sales_count=Product.sales_count + item.quantity)
            )
        order.status = OrderStatus.PAID
        order.paid_amount = order.payable_amount
        order.paid_at = paid_at
        await self.session.commit()
        await self.session.refresh(order)
        return PaymentResult(
            payment_no=payment_no,
            status=PaymentStatus.SUCCESS,
            paid_amount=order.paid_amount,
            wallet_balance=wallet.balance,
            order=await self._order_detail(order),
        )

    async def cancel_order(self, user_id: int, order_id: int) -> OrderDetail:
        order = await self.trade.get_order(user_id, order_id, lock=True)
        if order is None:
            raise NotFoundError("订单不存在")
        if order.status != OrderStatus.PENDING_PAYMENT:
            raise ConflictError("只有待支付订单可以取消")
        items = await self.trade.list_order_items(order.id)
        sku_map = await self.trade.lock_skus([item.sku_id for item in items])
        for item in items:
            sku = sku_map.get(item.sku_id)
            if sku is None or sku.locked_stock < item.quantity:
                raise ConflictError("订单预占库存异常，请联系管理员")
            sku.locked_stock -= item.quantity
            sku.version += 1
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(order)
        return await self._order_detail(order)

    async def complete_order(self, user_id: int, order_id: int) -> OrderDetail:
        order = await self.trade.get_order(user_id, order_id, lock=True)
        if order is None:
            raise NotFoundError("订单不存在")
        if order.status != OrderStatus.SHIPPED:
            raise ConflictError("只有已发货订单可以确认收货")
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(order)
        return await self._order_detail(order)

    async def list_admin_orders(
        self,
        *,
        page: int,
        page_size: int,
        order_status: OrderStatus | None,
    ) -> PageData[AdminOrderSummary]:
        orders, total = await self.trade.list_admin_orders(
            page=page, page_size=page_size, order_status=order_status
        )
        return PageData(
            items=[AdminOrderSummary.model_validate(order) for order in orders],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def get_admin_order(self, order_id: int) -> AdminOrderDetail:
        order = await self.trade.get_admin_order(order_id)
        if order is None:
            raise NotFoundError("订单不存在")
        detail = await self._order_detail(order)
        return AdminOrderDetail(**detail.model_dump(), user_id=order.user_id)

    async def ship_order(self, order_id: int) -> AdminOrderDetail:
        order = await self.trade.get_admin_order(order_id, lock=True)
        if order is None:
            raise NotFoundError("订单不存在")
        if order.status != OrderStatus.PAID:
            raise ConflictError("只有已支付订单可以发货")
        order.status = OrderStatus.SHIPPED
        order.shipped_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(order)
        detail = await self._order_detail(order)
        return AdminOrderDetail(**detail.model_dump(), user_id=order.user_id)

    async def admin_complete_order(self, order_id: int) -> AdminOrderDetail:
        order = await self.trade.get_admin_order(order_id, lock=True)
        if order is None:
            raise NotFoundError("订单不存在")
        if order.status != OrderStatus.SHIPPED:
            raise ConflictError("只有已发货订单可以完成")
        order.status = OrderStatus.COMPLETED
        order.completed_at = datetime.now(UTC)
        await self.session.commit()
        await self.session.refresh(order)
        detail = await self._order_detail(order)
        return AdminOrderDetail(**detail.model_dump(), user_id=order.user_id)

    async def create_review(self, user: User, payload: ReviewCreate) -> ReviewPublic:
        order_item = await self.trade.get_order_item_for_user(user.id, payload.order_item_id)
        if order_item is None:
            raise NotFoundError("订单商品不存在")
        order, item = order_item
        if order.status != OrderStatus.COMPLETED:
            raise ConflictError("订单完成后才可以评价")
        if await self.trade.get_review_by_order_item(item.id):
            raise ConflictError("该订单商品已经评价")
        review = Review(
            user_id=user.id,
            product_id=item.product_id,
            order_item_id=item.id,
            rating=payload.rating,
            content=payload.content,
            image_urls=payload.image_urls,
            anonymous=payload.anonymous,
            visible=True,
        )
        self.trade.add(review)
        await self.session.flush()
        await self._refresh_product_review_stats(item.product_id)
        await self.session.commit()
        await self.session.refresh(review)
        return _review_public(review, user)

    async def list_product_reviews(
        self, product_id: int, *, page: int, page_size: int
    ) -> PageData[ReviewPublic]:
        rows, total = await self.trade.list_product_reviews(
            product_id, page=page, page_size=page_size
        )
        return PageData(
            items=[_review_public(review, user) for review, user in rows],
            page=page,
            page_size=page_size,
            total=total,
        )

    async def list_admin_reviews(
        self, *, page: int, page_size: int
    ) -> PageData[ReviewAdmin]:
        rows, total = await self.trade.list_admin_reviews(page=page, page_size=page_size)
        items = []
        for review, user, product in rows:
            public = _review_public(review, user).model_dump()
            items.append(
                ReviewAdmin(
                    **public,
                    order_item_id=review.order_item_id,
                    username=user.username,
                    product_name=product.name,
                    visible=review.visible,
                )
            )
        return PageData(items=items, page=page, page_size=page_size, total=total)

    async def update_review_visibility(self, review_id: int, visible: bool) -> ReviewAdmin:
        review = await self.trade.get_review(review_id)
        if review is None:
            raise NotFoundError("评价不存在")
        review.visible = visible
        await self.session.flush()
        await self._refresh_product_review_stats(review.product_id)
        await self.session.commit()
        user = await self.session.get(User, review.user_id)
        product = await self.session.get(Product, review.product_id)
        if user is None or product is None:
            raise NotFoundError("评价关联数据不存在")
        public = _review_public(review, user).model_dump()
        return ReviewAdmin(
            **public,
            order_item_id=review.order_item_id,
            username=user.username,
            product_name=product.name,
            visible=review.visible,
        )

    async def _wallet_or_create(self, user_id: int) -> Wallet:
        wallet = await self.trade.get_wallet(user_id)
        if wallet is None:
            wallet = Wallet(user_id=user_id)
            self.trade.add(wallet)
            await self.session.commit()
            await self.session.refresh(wallet)
        return wallet

    async def _order_detail(self, order: Order) -> OrderDetail:
        summary = OrderSummary.model_validate(order).model_dump()
        items = await self.trade.list_order_items(order.id)
        reviewed_ids = await self.trade.reviewed_order_item_ids(order.id)
        return OrderDetail(
            **summary,
            address_snapshot=order.address_snapshot,
            buyer_remark=order.buyer_remark,
            shipped_at=order.shipped_at,
            completed_at=order.completed_at,
            cancelled_at=order.cancelled_at,
            items=[
                OrderItemPublic(
                    **OrderItemPublic.model_validate(item).model_dump(exclude={"reviewed"}),
                    reviewed=item.id in reviewed_ids,
                )
                for item in items
            ],
        )

    async def _refresh_product_review_stats(self, product_id: int) -> None:
        average, count = (
            await self.session.execute(
                select(func.avg(Review.rating), func.count(Review.id)).where(
                    Review.product_id == product_id,
                    Review.visible.is_(True),
                )
            )
        ).one()
        product = await self.session.get(Product, product_id)
        if product is not None:
            product.rating = _money(Decimal(str(average or 0)))
            product.review_count = int(count or 0)
