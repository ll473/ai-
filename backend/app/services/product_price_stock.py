from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.exceptions import NotFoundError
from backend.app.models.enums import ProductStatus
from backend.app.repositories.catalog import CatalogRepository
from backend.app.services.promotion import AppliedPromotion, best_promotion


@dataclass(frozen=True)
class SkuPriceStock:
    sku_id: int
    sku_name: str
    price: Decimal
    available_stock: int
    attributes: dict[str, Any] | None
    promotion: AppliedPromotion | None


@dataclass(frozen=True)
class ProductPriceStockResult:
    product_id: int
    product_name: str
    skus: tuple[SkuPriceStock, ...]


class ProductPriceStockService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.catalog = CatalogRepository(session)

    async def get(self, product_id: int) -> ProductPriceStockResult:
        product = await self.catalog.get_product(product_id)
        if product is None or product.status != ProductStatus.ON_SALE:
            raise NotFoundError("商品不存在或已下架")
        skus = await self.catalog.list_product_skus(product_id, enabled_only=True)
        results: list[SkuPriceStock] = []
        for sku in skus:
            results.append(
                SkuPriceStock(
                    sku_id=sku.id,
                    sku_name=sku.name,
                    price=sku.price,
                    available_stock=max(0, sku.stock - sku.locked_stock),
                    attributes=sku.attributes,
                    promotion=await best_promotion(
                        self.session, product.id, sku.price
                    ),
                )
            )
        return ProductPriceStockResult(
            product_id=product.id,
            product_name=product.name,
            skus=tuple(results),
        )
