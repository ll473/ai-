import asyncio
import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.api.dependencies import get_current_user
from backend.app.api.v1.routes import ai as ai_routes
from backend.app.models import Base
from backend.app.models.catalog import Category, Product, ProductSku
from backend.app.models.enums import ProductStatus
from backend.app.schemas.ai import (
    ProductComparisonAiItem,
    ProductComparisonAiResult,
    ProductComparisonRequest,
)
from backend.app.services.product_comparison_ai import (
    BailianProductComparisonGateway,
    ProductComparisonAiService,
)


@asynccontextmanager
async def seeded_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            session.add_all(
                [
                    Category(id=10, name="数码影音", slug="digital"),
                    Category(id=20, name="办公效率", slug="office"),
                    Product(
                        id=1,
                        category_id=10,
                        name="耳机 A",
                        product_no="A-1",
                        min_price=599,
                        max_price=599,
                        detail_markdown="不应发送给模型的商品详情",
                        parameters={"降噪": "自适应", "续航": "30 小时"},
                        status=ProductStatus.ON_SALE,
                    ),
                    Product(
                        id=2,
                        category_id=10,
                        name="耳机 B",
                        product_no="B-2",
                        min_price=899,
                        max_price=899,
                        parameters={"降噪": "混合", "续航": "35 小时"},
                        status=ProductStatus.ON_SALE,
                    ),
                    Product(
                        id=3,
                        category_id=20,
                        name="办公椅",
                        product_no="C-3",
                        status=ProductStatus.ON_SALE,
                    ),
                    Product(
                        id=4,
                        category_id=10,
                        name="下架耳机",
                        product_no="D-4",
                        status=ProductStatus.OFF_SALE,
                    ),
                    ProductSku(
                        id=11,
                        product_id=1,
                        sku_no="A-1-S",
                        name="标准版",
                        attributes={"配色": "黑色", "版本": 2},
                        price=599,
                        stock=5,
                        locked_stock=1,
                        enabled=True,
                    ),
                    ProductSku(
                        id=21,
                        product_id=2,
                        sku_no="B-2-S",
                        name="标准版",
                        attributes={"配色": "黑色", "版本": 2},
                        price=899,
                        stock=9,
                        locked_stock=2,
                        enabled=True,
                    ),
                ]
            )
            await session.commit()
            yield session
    finally:
        await engine.dispose()


def ai_result(recommended_product_id: int = 2) -> ProductComparisonAiResult:
    return ProductComparisonAiResult(
        recommended_product_id=recommended_product_id,
        summary="更推荐耳机 B。",
        items=[
            ProductComparisonAiItem(
                product_id=1,
                strengths=["价格更低"],
                weaknesses=["续航较短"],
                suitable_for=["预算优先"],
            ),
            ProductComparisonAiItem(
                product_id=2,
                strengths=["续航更长"],
                weaknesses=["价格较高"],
                suitable_for=["通勤"],
            ),
        ],
        considerations=["请结合佩戴舒适度选择"],
    )


class FakeComparisonGateway:
    def __init__(self, result: ProductComparisonAiResult) -> None:
        self.calls = 0
        self.facts: list[dict[str, Any]] = []
        self.preference: str | None = None
        self.result = result
        self.closed = False

    async def compare(
        self, facts: list[dict[str, Any]], preference: str | None
    ) -> ProductComparisonAiResult:
        self.calls += 1
        self.facts = facts
        self.preference = preference
        return self.result

    async def close(self) -> None:
        self.closed = True


class SlowComparisonGateway(FakeComparisonGateway):
    async def compare(
        self, facts: list[dict[str, Any]], preference: str | None
    ) -> ProductComparisonAiResult:
        self.calls += 1
        await asyncio.sleep(0.1)
        return self.result


@pytest.mark.asyncio
async def test_ai_comparison_uses_server_facts_once_in_requested_order() -> None:
    async with seeded_session() as session:
        gateway = FakeComparisonGateway(ai_result())
        result = await ProductComparisonAiService(session, gateway=gateway).compare(
            ProductComparisonRequest(product_ids=[2, 1], preference="  通勤使用  ")
        )

    assert gateway.calls == 1
    assert [fact["product_id"] for fact in gateway.facts] == [2, 1]
    assert gateway.preference == "通勤使用"
    assert "detail_markdown" not in gateway.facts[0]
    assert gateway.facts[0]["min_price"] == "899.00"
    assert gateway.facts[0]["max_price"] == "899.00"
    assert gateway.facts[0]["total_available_stock"] == 7
    assert gateway.facts[0]["skus"] == [{
        "name": "标准版",
        "attributes": {"配色": "黑色", "版本": "2"},
        "price": "899.00",
        "available_stock": 7,
    }]
    assert "detail_markdown" not in gateway.facts[0]
    assert "locked_stock" not in gateway.facts[0]
    assert "stock" not in gateway.facts[0]
    assert result.recommended_product_id == 2


@pytest.mark.asyncio
async def test_ai_comparison_rejects_unavailable_candidate_before_gateway_call() -> None:
    async with seeded_session() as session:
        gateway = FakeComparisonGateway(ai_result())
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(session, gateway=gateway).compare(
                ProductComparisonRequest(product_ids=[1, 4])
            )

    assert captured.value.code == "COMPARISON_PRODUCT_UNAVAILABLE"
    assert gateway.calls == 0


@pytest.mark.asyncio
async def test_ai_comparison_rejects_cross_category_before_gateway_call() -> None:
    async with seeded_session() as session:
        gateway = FakeComparisonGateway(ai_result())
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(session, gateway=gateway).compare(
                ProductComparisonRequest(product_ids=[1, 3])
            )

    assert captured.value.code == "COMPARISON_CATEGORY_MISMATCH"
    assert gateway.calls == 0


def test_ai_comparison_request_rejects_duplicate_only_selection() -> None:
    with pytest.raises(ValueError, match="至少需要两件不同商品"):
        ProductComparisonRequest(product_ids=[1, 1])


@pytest.mark.asyncio
async def test_ai_comparison_rejects_response_ids_outside_server_candidates() -> None:
    async with seeded_session() as session:
        gateway = FakeComparisonGateway(ai_result(recommended_product_id=999))
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(session, gateway=gateway).compare(
                ProductComparisonRequest(product_ids=[1, 2])
            )

    assert captured.value.code == "AI_INVALID_RESPONSE"


@pytest.mark.asyncio
async def test_ai_comparison_rejects_item_ids_outside_server_candidates() -> None:
    invalid_result = ai_result()
    invalid_result.items[0].product_id = 999
    async with seeded_session() as session:
        gateway = FakeComparisonGateway(invalid_result)
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(session, gateway=gateway).compare(
                ProductComparisonRequest(product_ids=[1, 2])
            )

    assert captured.value.code == "AI_INVALID_RESPONSE"


@pytest.mark.asyncio
async def test_ai_comparison_rejects_response_missing_a_candidate_item() -> None:
    incomplete_result = ai_result()
    incomplete_result.items.pop()
    async with seeded_session() as session:
        gateway = FakeComparisonGateway(incomplete_result)
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(session, gateway=gateway).compare(
                ProductComparisonRequest(product_ids=[1, 2])
            )

    assert captured.value.code == "AI_INVALID_RESPONSE"
    assert captured.value.status_code == 502


@pytest.mark.asyncio
async def test_ai_comparison_rejects_response_with_no_candidate_items() -> None:
    empty_result = ai_result()
    empty_result.items = []
    async with seeded_session() as session:
        gateway = FakeComparisonGateway(empty_result)
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(session, gateway=gateway).compare(
                ProductComparisonRequest(product_ids=[1, 2])
            )

    assert captured.value.code == "AI_INVALID_RESPONSE"
    assert captured.value.status_code == 502


@pytest.mark.asyncio
async def test_ai_comparison_maps_gateway_timeout_to_504() -> None:
    async with seeded_session() as session:
        gateway = SlowComparisonGateway(ai_result())
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(
                session, gateway=gateway, timeout_seconds=0.01
            ).compare(ProductComparisonRequest(product_ids=[1, 2]))

    assert captured.value.code == "AI_COMPARISON_TIMEOUT"
    assert captured.value.status_code == 504


@pytest.mark.asyncio
async def test_ai_comparison_reports_unavailable_when_default_model_is_not_configured() -> None:
    async with seeded_session() as session:
        with pytest.raises(Exception) as captured:
            await ProductComparisonAiService(session).compare(
                ProductComparisonRequest(product_ids=[1, 2])
            )

    assert captured.value.code == "AI_MODEL_UNAVAILABLE"
    assert captured.value.status_code == 503


@pytest.mark.asyncio
async def test_bailian_gateway_uses_one_non_thinking_json_request() -> None:
    class FakeCompletions:
        def __init__(self) -> None:
            self.calls: list[dict[str, Any]] = []

        async def create(self, **kwargs: Any) -> Any:
            self.calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(message=SimpleNamespace(content=ai_result().model_dump_json()))
                ]
            )

    class FakeClient:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(completions=FakeCompletions())
            self.closed = False

        async def close(self) -> None:
            self.closed = True

    client = FakeClient()
    gateway = BailianProductComparisonGateway(
        model="qwen3.7-plus", api_key="test-key", client=client
    )
    result = await gateway.compare([{"product_id": 1, "name": "耳机 A"}], None)

    assert result.recommended_product_id == 2
    assert len(client.chat.completions.calls) == 1
    kwargs = client.chat.completions.calls[0]
    assert kwargs["extra_body"] == {"enable_thinking": False}
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["max_tokens"] <= 800
    assert kwargs["temperature"] == 0.2


@pytest.mark.asyncio
async def test_bailian_gateway_maps_invalid_json_to_502() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(
                    create=self.create,
                )
            )

        async def create(self, **_: Any) -> Any:
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))]
            )

        async def close(self) -> None:
            pass

    gateway = BailianProductComparisonGateway(
        model="qwen3.7-plus", api_key="test-key", client=FakeClient()
    )
    with pytest.raises(Exception) as captured:
        await gateway.compare([{"product_id": 1, "name": "耳机 A"}], None)

    assert captured.value.code == "AI_INVALID_RESPONSE"
    assert captured.value.status_code == 502


def test_ai_comparison_route_keeps_login_dependency_before_service_execution() -> None:
    route = next(
        route
        for route in ai_routes.router.routes
        if route.path == "/ai/product-comparison"
    )

    assert any(dependency.call is get_current_user for dependency in route.dependant.dependencies)
    assert "user" in inspect.signature(route.endpoint).parameters
