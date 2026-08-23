from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.enums import PromotionType
from backend.app.models.trade import Promotion
from backend.app.repositories.promotion import PromotionRepository


@dataclass(frozen=True)
class AppliedPromotion:
    promotion_id: int
    name: str
    discount_amount: Decimal
    snapshot: dict[str, Any]


@dataclass(frozen=True)
class PromotionLine:
    product_id: int
    amount: Decimal


@dataclass(frozen=True)
class OrderPromotionResult:
    strategy: Literal["NONE", "GLOBAL", "PRODUCT"]
    discount_amount: Decimal
    promotions: tuple[AppliedPromotion, ...]


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def best_promotion(
    session: AsyncSession,
    product_id: int,
    amount: Decimal,
    *,
    at: datetime | None = None,
) -> AppliedPromotion | None:
    promotions = await PromotionRepository(session).list_active_for_products(
        {product_id}, at=at or datetime.now(UTC)
    )
    return _best_promotion(promotions, amount)


async def best_order_promotion(
    session: AsyncSession,
    lines: Iterable[PromotionLine],
    *,
    at: datetime | None = None,
) -> OrderPromotionResult:
    normalized_lines = tuple(lines)
    amounts_by_product: dict[int, Decimal] = {}
    for line in normalized_lines:
        amounts_by_product[line.product_id] = _money(
            amounts_by_product.get(line.product_id, Decimal("0")) + line.amount
        )
    order_amount = _money(sum(amounts_by_product.values(), Decimal("0")))
    if order_amount <= 0:
        return OrderPromotionResult("NONE", Decimal("0.00"), ())

    promotions = await PromotionRepository(session).list_active_for_products(
        set(amounts_by_product), at=at or datetime.now(UTC)
    )
    global_best = _best_promotion(
        (item for item in promotions if item.product_id is None), order_amount
    )
    product_best_list: list[AppliedPromotion] = []
    for product_id, amount in amounts_by_product.items():
        candidate = _best_promotion(
            (item for item in promotions if item.product_id == product_id), amount
        )
        if candidate is not None:
            product_best_list.append(candidate)
    product_best = tuple(product_best_list)
    product_discount = _money(
        sum((item.discount_amount for item in product_best), Decimal("0"))
    )
    global_discount = global_best.discount_amount if global_best else Decimal("0.00")
    if global_best is not None and global_discount >= product_discount:
        return OrderPromotionResult("GLOBAL", global_discount, (global_best,))
    if product_best:
        return OrderPromotionResult(
            "PRODUCT", min(order_amount, product_discount), product_best
        )
    return OrderPromotionResult("NONE", Decimal("0.00"), ())


def _best_promotion(
    promotions: Iterable[Promotion], amount: Decimal
) -> AppliedPromotion | None:
    best: AppliedPromotion | None = None
    for promotion in promotions:
        candidate = _apply_promotion(promotion, amount)
        if candidate is None:
            continue
        if best is None or candidate.discount_amount > best.discount_amount:
            best = candidate
    return best


def _apply_promotion(promotion: Promotion, amount: Decimal) -> AppliedPromotion | None:
    if amount < promotion.minimum_amount:
        return None
    if promotion.promotion_type == PromotionType.PERCENT:
        discount = amount * min(promotion.value, Decimal("100")) / Decimal("100")
    else:
        discount = promotion.value
    discount = min(amount, _money(discount))
    return AppliedPromotion(
        promotion_id=promotion.id,
        name=promotion.name,
        discount_amount=discount,
        snapshot={
            "promotion_id": promotion.id,
            "name": promotion.name,
            "type": str(promotion.promotion_type),
            "value": str(promotion.value),
            "discount_amount": str(discount),
        },
    )
