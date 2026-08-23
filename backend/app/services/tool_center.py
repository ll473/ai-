import asyncio
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from decimal import Decimal
from time import perf_counter
from typing import Any, Self

from pydantic import BaseModel, Field, ValidationError, model_validator
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.ai import (
    AgentRun,
    FunctionTool,
    Recommendation,
    RecommendationItem,
    ToolCallLog,
)
from backend.app.models.catalog import Product, ProductSku
from backend.app.models.enums import OrderStatus, ProductStatus, StepStatus
from backend.app.models.trade import Order
from backend.app.models.user import Wallet
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import ToolExecutionPublic
from backend.app.services.product_price_stock import ProductPriceStockService


class SearchProductsArgs(BaseModel):
    keyword: str | None = Field(default=None, max_length=100)
    min_price: Decimal | None = Field(default=None, ge=0)
    max_price: Decimal | None = Field(default=None, ge=0)
    limit: int = Field(default=10, ge=1, le=20)


class ProductPriceStockArgs(BaseModel):
    product_id: int = Field(gt=0)


class OrderStatusArgs(BaseModel):
    order_no: str = Field(min_length=1, max_length=64)


class EmptyArgs(BaseModel):
    pass


class RecommendationCandidate(BaseModel):
    product_id: int = Field(gt=0)
    sku_id: int | None = Field(default=None, gt=0)
    reason: str = Field(min_length=2, max_length=1000)


class SubmitRecommendationArgs(BaseModel):
    summary: str = Field(min_length=2, max_length=2000)
    items: list[RecommendationCandidate] = Field(min_length=1, max_length=5)

    @model_validator(mode="after")
    def unique_products(self) -> Self:
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("推荐商品不可重复")
        return self


@dataclass(frozen=True)
class ValidatedRecommendation:
    product: Product
    sku: ProductSku
    reason: str


@dataclass(frozen=True)
class ToolContext:
    user_id: int | None = None
    agent_run_id: int | None = None
    agent_step_id: int | None = None


Executor = Callable[[dict[str, Any], ToolContext], Awaitable[dict[str, Any]]]


class ToolCenter:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ai = AiRepository(session)
        self.executors: dict[str, Executor] = {
            "catalog.search_products": self._search_products,
            "catalog.get_product_price_stock": self._get_product_price_stock,
            "orders.get_user_order_status": self._get_user_order_status,
            "profile.get_user_summary": self._get_user_summary,
            "recommendations.submit": self._submit_recommendation,
        }

    async def execute_by_name(
        self, name: str, arguments: dict[str, Any], context: ToolContext
    ) -> ToolExecutionPublic:
        tool = await self.ai.get_tool_by_name(name)
        if tool is None or not tool.enabled:
            return ToolExecutionPublic(
                call_no=self._call_no(),
                tool_name=name,
                status=StepStatus.FAILED,
                result=None,
                error_message="工具不存在或已停用",
                duration_ms=0,
            )
        return await self.execute(tool, arguments, context)

    async def execute(
        self, tool: FunctionTool, arguments: dict[str, Any], context: ToolContext
    ) -> ToolExecutionPublic:
        call_no = self._call_no()
        log = ToolCallLog(
            call_no=call_no,
            tool_id=tool.id,
            agent_run_id=context.agent_run_id,
            agent_step_id=context.agent_step_id,
            user_id=context.user_id,
            arguments_json=arguments,
            status=StepStatus.RUNNING,
        )
        self.ai.add(log)
        await self.session.flush()
        started = perf_counter()
        result: dict[str, Any] | None = None
        error_message: str | None = None
        status = StepStatus.SUCCEEDED
        try:
            executor = self.executors.get(tool.executor)
            if executor is None:
                raise ValueError("工具 executor 不在后端白名单中")
            async with asyncio.timeout(tool.timeout_seconds):
                result = await executor(arguments, context)
        except (TimeoutError, ValidationError, ValueError) as exc:
            status = StepStatus.FAILED
            error_message = "工具执行超时" if isinstance(exc, TimeoutError) else str(exc)
        except Exception as exc:  # pragma: no cover - defensive logging boundary
            status = StepStatus.FAILED
            error_message = f"工具执行失败：{type(exc).__name__}"
        duration_ms = max(0, int((perf_counter() - started) * 1000))
        log.result_json = result
        log.status = status
        log.error_message = error_message
        log.duration_ms = duration_ms
        await self.session.commit()
        return ToolExecutionPublic(
            call_no=call_no,
            tool_name=tool.name,
            status=status,
            result=result,
            error_message=error_message,
            duration_ms=duration_ms,
        )

    async def _search_products(
        self, arguments: dict[str, Any], _: ToolContext
    ) -> dict[str, Any]:
        args = SearchProductsArgs.model_validate(arguments)
        statement = select(Product).where(Product.status == ProductStatus.ON_SALE)
        if args.keyword:
            escaped = args.keyword.replace("%", r"\%").replace("_", r"\_")
            statement = statement.where(Product.name.like(f"%{escaped}%", escape="\\"))
        if args.min_price is not None:
            statement = statement.where(Product.max_price >= args.min_price)
        if args.max_price is not None:
            statement = statement.where(Product.min_price <= args.max_price)
        statement = statement.order_by(
            Product.rating.desc(), Product.sales_count.desc(), Product.id.desc()
        ).limit(args.limit)
        products = list((await self.session.scalars(statement)).all())
        return {
            "count": len(products),
            "items": [
                {
                    "product_id": item.id,
                    "name": item.name,
                    "subtitle": item.subtitle,
                    "min_price": str(item.min_price),
                    "max_price": str(item.max_price),
                    "rating": str(item.rating),
                    "review_count": item.review_count,
                    "sales_count": item.sales_count,
                }
                for item in products
            ],
        }

    async def _get_product_price_stock(
        self, arguments: dict[str, Any], _: ToolContext
    ) -> dict[str, Any]:
        args = ProductPriceStockArgs.model_validate(arguments)
        result = await ProductPriceStockService(self.session).get(args.product_id)
        return {
            "product_id": result.product_id,
            "product_name": result.product_name,
            "skus": [
                {
                    "sku_id": item.sku_id,
                    "sku_name": item.sku_name,
                    "price": str(item.price),
                    "available_stock": item.available_stock,
                    "attributes": item.attributes,
                    "promotion": item.promotion.snapshot if item.promotion else None,
                }
                for item in result.skus
            ],
        }

    async def _get_user_order_status(
        self, arguments: dict[str, Any], context: ToolContext
    ) -> dict[str, Any]:
        if context.user_id is None:
            raise ValueError("该工具需要登录用户上下文")
        args = OrderStatusArgs.model_validate(arguments)
        result = await self.session.execute(
            select(Order).where(
                Order.user_id == context.user_id, Order.order_no == args.order_no
            )
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise ValueError("未找到当前用户的该订单")
        return {
            "order_no": order.order_no,
            "status": str(order.status),
            "payable_amount": str(order.payable_amount),
            "paid_amount": str(order.paid_amount),
            "paid_at": order.paid_at.isoformat() if order.paid_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        }

    async def _get_user_summary(
        self, arguments: dict[str, Any], context: ToolContext
    ) -> dict[str, Any]:
        EmptyArgs.model_validate(arguments)
        if context.user_id is None:
            raise ValueError("该工具需要登录用户上下文")
        wallet = await self.session.scalar(select(Wallet).where(Wallet.user_id == context.user_id))
        rows = await self.session.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.user_id == context.user_id)
            .group_by(Order.status)
        )
        counts = {str(status): int(count) for status, count in rows.all()}
        return {
            "wallet_balance": str(wallet.balance if wallet else Decimal("0.00")),
            "order_counts": {status.value: counts.get(status.value, 0) for status in OrderStatus},
        }

    async def _submit_recommendation(
        self, arguments: dict[str, Any], context: ToolContext
    ) -> dict[str, Any]:
        if context.user_id is None or context.agent_run_id is None:
            raise ValueError("提交推荐需要登录用户与 Agent Run 上下文")
        args = SubmitRecommendationArgs.model_validate(arguments)
        run = await self.session.get(AgentRun, context.agent_run_id)
        if run is None or run.user_id != context.user_id:
            raise ValueError("Agent Run 不存在或不属于当前用户")

        accepted: list[ValidatedRecommendation] = []
        rejected: list[dict[str, Any]] = []
        for candidate in args.items:
            product = await self.session.get(Product, candidate.product_id)
            if product is None or product.status != ProductStatus.ON_SALE:
                rejected.append(
                    {
                        "product_id": candidate.product_id,
                        "sku_id": candidate.sku_id,
                        "reason": "商品不存在或已下架",
                    }
                )
                continue
            sku = await self._select_recommendation_sku(product.id, candidate.sku_id)
            if sku is None:
                rejected.append(
                    {
                        "product_id": candidate.product_id,
                        "sku_id": candidate.sku_id,
                        "reason": "SKU 不属于该商品、已停用或缺货",
                    }
                )
                continue
            accepted.append(
                ValidatedRecommendation(product=product, sku=sku, reason=candidate.reason)
            )
        if not accepted:
            raise ValueError("推荐候选均未通过商品、SKU 与库存校验")

        recommendation = await self.ai.get_recommendation(run.id)
        if recommendation is None:
            recommendation = Recommendation(
                agent_run_id=run.id, user_id=context.user_id, summary=args.summary
            )
            self.ai.add(recommendation)
            await self.session.flush()
        else:
            recommendation.summary = args.summary
            await self.session.execute(
                delete(RecommendationItem).where(
                    RecommendationItem.recommendation_id == recommendation.id
                )
            )
            await self.session.flush()

        result_items: list[dict[str, Any]] = []
        for item in accepted:
            available_stock = item.sku.stock - item.sku.locked_stock
            self.ai.add(
                RecommendationItem(
                    recommendation_id=recommendation.id,
                    product_id=item.product.id,
                    sku_id=item.sku.id,
                    reason=item.reason,
                    price_snapshot=item.sku.price,
                    stock_snapshot=available_stock,
                    promotion_snapshot=None,
                    validation_passed=True,
                )
            )
            result_items.append(
                {
                    "product_id": item.product.id,
                    "product_name": item.product.name,
                    "sku_id": item.sku.id,
                    "sku_name": item.sku.name,
                    "reason": item.reason,
                    "verified_price": str(item.sku.price),
                    "verified_stock": available_stock,
                }
            )
        return {
            "recommendation_id": recommendation.id,
            "summary": recommendation.summary,
            "accepted_items": result_items,
            "rejected_items": rejected,
            "validation": "价格、库存与商品状态已由后端实时校验",
        }

    async def _select_recommendation_sku(
        self, product_id: int, sku_id: int | None
    ) -> ProductSku | None:
        statement = select(ProductSku).where(
            ProductSku.product_id == product_id,
            ProductSku.enabled.is_(True),
            ProductSku.stock > ProductSku.locked_stock,
        )
        if sku_id is not None:
            statement = statement.where(ProductSku.id == sku_id)
        else:
            statement = statement.order_by(ProductSku.price, ProductSku.id).limit(1)
        return (await self.session.execute(statement)).scalar_one_or_none()

    @staticmethod
    def _call_no() -> str:
        return f"TC{secrets.token_hex(12).upper()}"
