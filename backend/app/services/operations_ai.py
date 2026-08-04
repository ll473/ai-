import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Protocol

from openai import AsyncOpenAI
from sqlalchemy import case, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import get_settings
from backend.app.core.crypto import decrypt_secret
from backend.app.core.exceptions import AppError, NotFoundError
from backend.app.models.ai import (
    AgentRun,
    AiModelConfig,
    OperationReport,
    Recommendation,
    RecommendationItem,
    ReviewAnalysis,
)
from backend.app.models.catalog import Product
from backend.app.models.enums import AgentRunStatus, OrderStatus
from backend.app.models.trade import Order, OrderItem, Review
from backend.app.repositories.ai import AiRepository
from backend.app.schemas.ai import (
    OperationReportGenerateRequest,
    OperationReportPublic,
    OperationsDashboardPublic,
    ReviewAnalysisGenerateRequest,
    ReviewAnalysisPublic,
    ReviewAnalysisResult,
    TopProductMetric,
)

PAID_STATUSES = [OrderStatus.PAID, OrderStatus.SHIPPED, OrderStatus.COMPLETED]


class OperationsModelGateway(Protocol):
    async def analyze_reviews(self, reviews: list[dict[str, Any]]) -> ReviewAnalysisResult: ...

    async def generate_report(self, metrics: dict[str, Any]) -> str: ...

    async def close(self) -> None: ...


class BailianOperationsGateway:
    def __init__(
        self,
        config: AiModelConfig,
        api_key: str,
        *,
        review_prompt: str | None = None,
        report_prompt: str | None = None,
    ) -> None:
        settings = get_settings()
        self.model = config.chat_model
        self.max_tokens = config.max_tokens
        self.review_prompt = review_prompt
        self.report_prompt = report_prompt
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=config.base_url or settings.ai_base_url
        )

    async def analyze_reviews(self, reviews: list[dict[str, Any]]) -> ReviewAnalysisResult:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.review_prompt or (
                        "你是电商评价分析师。只依据输入评价归纳，不得虚构事实。"
                        "必须输出 JSON 对象，且仅包含 positive_keywords、negative_reasons、"
                        "after_sale_risks、missing_information、suggestions 五个字符串数组，"
                        "每组最多 10 项。没有证据的类别返回空数组。"
                    ),
                },
                {
                    "role": "user",
                    "content": "请分析以下真实可见评价并输出 JSON：\n"
                    + json.dumps(reviews, ensure_ascii=False),
                },
            ],
            response_format={"type": "json_object"},
            extra_body={"enable_thinking": False},
        )
        content = response.choices[0].message.content
        if not content:
            raise AppError("模型未返回评价分析结果", code="AI_EMPTY_RESPONSE")
        try:
            return ReviewAnalysisResult.model_validate_json(content)
        except ValueError as exc:
            raise AppError("模型评价分析格式无效", code="AI_INVALID_RESPONSE") from exc

    async def generate_report(self, metrics: dict[str, Any]) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": self.report_prompt or (
                        "你是电商运营负责人。根据后端提供的真实统计快照撰写中文 Markdown 报告。"
                        "不得改写、推测或补造任何指标。按经营摘要、评价洞察、导购表现、"
                        "商品机会、风险与下阶段行动组织；行动建议要具体且可验证。"
                    ),
                },
                {
                    "role": "user",
                    "content": "真实统计快照如下：\n"
                    + json.dumps(metrics, ensure_ascii=False),
                },
            ],
            max_tokens=self.max_tokens,
            extra_body={"enable_thinking": False},
        )
        content = response.choices[0].message.content
        if not content or not content.strip():
            raise AppError("模型未返回运营报告", code="AI_EMPTY_RESPONSE")
        return content.strip()

    async def close(self) -> None:
        await self.client.close()


class OperationsAiService:
    def __init__(
        self, session: AsyncSession, gateway: OperationsModelGateway | None = None
    ) -> None:
        self.session = session
        self.ai = AiRepository(session)
        self.gateway = gateway

    async def get_dashboard(self, days: int = 30) -> OperationsDashboardPublic:
        end = datetime.now(UTC)
        start = end - timedelta(days=days)
        order_base = [Order.created_at >= start, Order.created_at <= end]
        review_base = [
            Review.visible.is_(True), Review.created_at >= start, Review.created_at <= end
        ]
        orders_total = int(
            await self.session.scalar(select(func.count(Order.id)).where(*order_base)) or 0
        )
        paid_orders = int(
            await self.session.scalar(
                select(func.count(Order.id)).where(*order_base, Order.status.in_(PAID_STATUSES))
            )
            or 0
        )
        revenue = Decimal(
            await self.session.scalar(
                select(func.coalesce(func.sum(Order.paid_amount), 0)).where(
                    *order_base, Order.status.in_(PAID_STATUSES)
                )
            )
            or 0
        )
        review_stats = (
            await self.session.execute(
                select(
                    func.count(Review.id),
                    func.coalesce(func.avg(Review.rating), 0),
                    func.coalesce(func.sum(case((Review.rating >= 4, 1), else_=0)), 0),
                    func.coalesce(func.sum(case((Review.rating <= 2, 1), else_=0)), 0),
                ).where(*review_base)
            )
        ).one()
        agent_runs = int(
            await self.session.scalar(
                select(func.count(AgentRun.id)).where(
                    AgentRun.created_at >= start, AgentRun.created_at <= end
                )
            )
            or 0
        )
        successful_agent_runs = int(
            await self.session.scalar(
                select(func.count(AgentRun.id)).where(
                    AgentRun.created_at >= start,
                    AgentRun.created_at <= end,
                    AgentRun.status == AgentRunStatus.SUCCEEDED,
                )
            )
            or 0
        )
        recommendations = int(
            await self.session.scalar(
                select(func.count(Recommendation.id))
                .join(AgentRun, AgentRun.id == Recommendation.agent_run_id)
                .where(AgentRun.created_at >= start, AgentRun.created_at <= end)
            )
            or 0
        )
        recommendation_items = int(
            await self.session.scalar(
                select(func.count(RecommendationItem.id))
                .join(Recommendation, Recommendation.id == RecommendationItem.recommendation_id)
                .join(AgentRun, AgentRun.id == Recommendation.agent_run_id)
                .where(AgentRun.created_at >= start, AgentRun.created_at <= end)
            )
            or 0
        )
        top_rows = (
            await self.session.execute(
                select(
                    Product.id,
                    Product.name,
                    func.count(distinct(Order.id)),
                    func.sum(OrderItem.quantity),
                    func.sum(OrderItem.total_amount),
                )
                .join(OrderItem, OrderItem.product_id == Product.id)
                .join(Order, Order.id == OrderItem.order_id)
                .where(*order_base, Order.status.in_(PAID_STATUSES))
                .group_by(Product.id, Product.name)
                .order_by(func.sum(OrderItem.total_amount).desc())
                .limit(5)
            )
        ).all()
        return OperationsDashboardPublic(
            period_start=start,
            period_end=end,
            orders_total=orders_total,
            paid_orders=paid_orders,
            revenue=revenue,
            reviews_total=int(review_stats[0]),
            average_rating=round(float(review_stats[1]), 2),
            positive_reviews=int(review_stats[2]),
            negative_reviews=int(review_stats[3]),
            agent_runs=agent_runs,
            successful_agent_runs=successful_agent_runs,
            recommendations=recommendations,
            recommendation_items=recommendation_items,
            top_products=[
                TopProductMetric(
                    product_id=int(row[0]),
                    product_name=str(row[1]),
                    order_count=int(row[2]),
                    quantity=int(row[3]),
                    revenue=Decimal(row[4]),
                )
                for row in top_rows
            ],
        )

    async def generate_review_analysis(
        self, payload: ReviewAnalysisGenerateRequest
    ) -> ReviewAnalysisPublic:
        end = datetime.now(UTC)
        start = end - timedelta(days=payload.days)
        statement = (
            select(Review, Product)
            .join(Product, Product.id == Review.product_id)
            .where(
                Review.visible.is_(True),
                Review.created_at >= start,
                Review.created_at <= end,
            )
            .order_by(Review.created_at.desc())
            .limit(200)
        )
        if payload.product_id is not None:
            statement = statement.where(Review.product_id == payload.product_id)
        rows = list((await self.session.execute(statement)).tuples().all())
        if not rows:
            raise AppError("所选范围暂无可分析评价", code="NO_REVIEWS")
        reviews = [
            {
                "product_id": review.product_id,
                "product_name": product.name,
                "rating": review.rating,
                "content": review.content[:2000],
            }
            for review, product in rows
        ]
        gateway, _ = await self._resolve_gateway()
        try:
            result = await gateway.analyze_reviews(reviews)
        finally:
            if self.gateway is None:
                await gateway.close()
        analysis = ReviewAnalysis(
            product_id=payload.product_id,
            period_start=start,
            period_end=end,
            source_review_count=len(rows),
            **result.model_dump(),
        )
        self.ai.add(analysis)
        await self.session.commit()
        await self.session.refresh(analysis)
        product_name = rows[0][1].name if payload.product_id is not None else None
        return self._analysis_public(analysis, product_name)

    async def list_review_analyses(self) -> list[ReviewAnalysisPublic]:
        rows = await self.ai.list_review_analyses()
        return [
            self._analysis_public(item, product.name if product else None)
            for item, product in rows
        ]

    async def generate_report(
        self, payload: OperationReportGenerateRequest
    ) -> OperationReportPublic:
        dashboard = await self.get_dashboard(payload.days)
        analyses = await self.list_review_analyses()
        metrics = dashboard.model_dump(mode="json")
        metrics["recent_review_analyses"] = [
            item.model_dump(mode="json") for item in analyses[:5]
        ]
        gateway, model_config_id = await self._resolve_gateway()
        try:
            content = await gateway.generate_report(metrics)
        finally:
            if self.gateway is None:
                await gateway.close()
        report = OperationReport(
            title=payload.title or f"近 {payload.days} 天 AI 运营增长报告",
            report_type="GROWTH",
            period_start=dashboard.period_start,
            period_end=dashboard.period_end,
            content_markdown=content,
            metrics_snapshot=metrics,
            model_config_id=model_config_id,
        )
        self.ai.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return OperationReportPublic.model_validate(report)

    async def list_reports(self) -> list[OperationReportPublic]:
        return [
            OperationReportPublic.model_validate(item)
            for item in await self.ai.list_operation_reports()
        ]

    async def get_report(self, report_id: int) -> OperationReportPublic:
        report = await self.ai.get_operation_report(report_id)
        if report is None:
            raise NotFoundError("运营报告不存在")
        return OperationReportPublic.model_validate(report)

    async def _resolve_gateway(self) -> tuple[OperationsModelGateway, int | None]:
        if self.gateway is not None:
            return self.gateway, None
        config = await self.ai.get_default_model_config()
        if config is None:
            raise AppError("请先启用默认百炼模型配置", code="AI_MODEL_NOT_CONFIGURED")
        settings = get_settings()
        api_key = (
            decrypt_secret(config.api_key_ciphertext)
            if config.api_key_ciphertext
            else settings.ai_api_key
        )
        if not api_key:
            raise AppError("默认模型尚未配置 API Key", code="AI_API_KEY_MISSING")
        review_prompt = await self.ai.get_scene_prompt("REVIEW_ANALYSIS")
        report_prompt = await self.ai.get_scene_prompt("OPERATIONS_REPORT")
        return (
            BailianOperationsGateway(
                config,
                api_key,
                review_prompt=review_prompt.system_prompt if review_prompt else None,
                report_prompt=report_prompt.system_prompt if report_prompt else None,
            ),
            config.id,
        )

    @staticmethod
    def _analysis_public(
        analysis: ReviewAnalysis, product_name: str | None
    ) -> ReviewAnalysisPublic:
        return ReviewAnalysisPublic(
            id=analysis.id,
            product_id=analysis.product_id,
            product_name=product_name,
            period_start=analysis.period_start,
            period_end=analysis.period_end,
            positive_keywords=analysis.positive_keywords or [],
            negative_reasons=analysis.negative_reasons or [],
            after_sale_risks=analysis.after_sale_risks or [],
            missing_information=analysis.missing_information or [],
            suggestions=analysis.suggestions or [],
            source_review_count=analysis.source_review_count,
            created_at=analysis.created_at,
        )
