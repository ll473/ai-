from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.trade import Promotion


class PromotionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_active_for_products(
        self, product_ids: set[int], *, at: datetime
    ) -> list[Promotion]:
        scope = or_(
            Promotion.product_id.is_(None),
            Promotion.product_id.in_(product_ids),
        )
        statement = (
            select(Promotion)
            .where(
                Promotion.enabled.is_(True),
                Promotion.starts_at <= at,
                Promotion.ends_at >= at,
                scope,
            )
            .order_by(Promotion.priority.desc(), Promotion.id.desc())
        )
        return list((await self.session.scalars(statement)).all())
