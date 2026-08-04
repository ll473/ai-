from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.ai import AgentRun, Recommendation, RecommendationItem
from backend.app.models.catalog import Category, Product
from backend.app.models.enums import AgentRunStatus, OrderStatus, ProductStatus
from backend.app.models.trade import Order, OrderItem, Review
from backend.app.models.user import User
from backend.app.schemas.ai import (
    OperationReportGenerateRequest,
    ReviewAnalysisGenerateRequest,
    ReviewAnalysisResult,
)
from backend.app.services.operations_ai import OperationsAiService


class FakeOperationsGateway:
    def __init__(self) -> None:
        self.reviews: list[dict[str, Any]] = []
        self.metrics: dict[str, Any] = {}

    async def analyze_reviews(
        self, reviews: list[dict[str, Any]]
    ) -> ReviewAnalysisResult:
        self.reviews = reviews
        return ReviewAnalysisResult(
            positive_keywords=["支撑性好"],
            negative_reasons=["安装说明不清晰"],
            after_sale_risks=["配件补发"],
            missing_information=["安装步骤"],
            suggestions=["补充安装视频"],
        )

    async def generate_report(self, metrics: dict[str, Any]) -> str:
        self.metrics = metrics
        return "# 运营增长报告\n\n## 经营摘要\n\n成交金额以统计快照为准。"

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_review_analysis_uses_visible_reviews_and_persists_result() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    gateway = FakeOperationsGateway()

    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Category(id=1, name="办公", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR001",
                    status=ProductStatus.ON_SALE,
                ),
                Order(
                    id=1,
                    order_no="ORDER001",
                    user_id=1,
                    status=OrderStatus.COMPLETED,
                    address_snapshot={},
                    product_amount=Decimal("1299.00"),
                    payable_amount=Decimal("1299.00"),
                    paid_amount=Decimal("1299.00"),
                ),
                OrderItem(
                    id=1,
                    order_id=1,
                    product_id=1,
                    sku_id=1,
                    product_name="人体工学椅",
                    sku_name="标准款",
                    unit_price=Decimal("1299.00"),
                    quantity=1,
                    total_amount=Decimal("1299.00"),
                ),
                OrderItem(
                    id=2,
                    order_id=1,
                    product_id=1,
                    sku_id=2,
                    product_name="人体工学椅",
                    sku_name="隐藏评价款",
                    unit_price=Decimal("1299.00"),
                    quantity=1,
                    total_amount=Decimal("1299.00"),
                ),
                Review(
                    id=1,
                    user_id=1,
                    product_id=1,
                    order_item_id=1,
                    rating=5,
                    content="腰背支撑很好，但安装说明可以更清楚。",
                    visible=True,
                ),
                Review(
                    id=2,
                    user_id=1,
                    product_id=1,
                    order_item_id=2,
                    rating=1,
                    content="这条已被管理员隐藏",
                    visible=False,
                ),
            ]
        )
        await session.commit()

        service = OperationsAiService(session, gateway)
        result = await service.generate_review_analysis(
            ReviewAnalysisGenerateRequest(product_id=1, days=30)
        )

        assert result.product_name == "人体工学椅"
        assert result.source_review_count == 1
        assert result.suggestions == ["补充安装视频"]
        assert len(gateway.reviews) == 1
        assert gateway.reviews[0]["rating"] == 5
        assert len(await service.list_review_analyses()) == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_dashboard_and_report_only_use_real_persisted_metrics() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    gateway = FakeOperationsGateway()

    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Category(id=1, name="办公", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR001",
                    status=ProductStatus.ON_SALE,
                ),
                Order(
                    id=1,
                    order_no="ORDER001",
                    user_id=1,
                    status=OrderStatus.PAID,
                    address_snapshot={},
                    product_amount=Decimal("1299.00"),
                    payable_amount=Decimal("1299.00"),
                    paid_amount=Decimal("1299.00"),
                ),
                OrderItem(
                    id=1,
                    order_id=1,
                    product_id=1,
                    sku_id=1,
                    product_name="人体工学椅",
                    sku_name="标准款",
                    unit_price=Decimal("1299.00"),
                    quantity=1,
                    total_amount=Decimal("1299.00"),
                ),
                AgentRun(
                    id=1,
                    run_no="AR-OPERATIONS-TEST",
                    user_id=1,
                    request_text="推荐办公椅",
                    status=AgentRunStatus.SUCCEEDED,
                    max_steps=6,
                    started_at=datetime.now(UTC),
                ),
                Recommendation(
                    id=1, agent_run_id=1, user_id=1, summary="办公椅推荐"
                ),
                RecommendationItem(
                    id=1,
                    recommendation_id=1,
                    product_id=1,
                    reason="支撑性好",
                    price_snapshot=Decimal("1299.00"),
                    stock_snapshot=8,
                    validation_passed=True,
                ),
            ]
        )
        await session.commit()

        service = OperationsAiService(session, gateway)
        dashboard = await service.get_dashboard(30)
        assert dashboard.orders_total == 1
        assert dashboard.paid_orders == 1
        assert dashboard.revenue == Decimal("1299.00")
        assert dashboard.recommendations == 1
        assert dashboard.top_products[0].quantity == 1

        report = await service.generate_report(
            OperationReportGenerateRequest(title="八月增长报告", days=30)
        )
        assert report.title == "八月增长报告"
        assert report.content_markdown.startswith("# 运营增长报告")
        assert gateway.metrics["revenue"] == "1299.00"
        assert len(await service.list_reports()) == 1

    await engine.dispose()
