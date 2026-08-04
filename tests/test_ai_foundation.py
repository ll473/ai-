from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import pytest
from openai.types.responses import ResponseFunctionToolCall
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.ai import AgentRun, AiModelConfig, RecommendationItem
from backend.app.models.catalog import Category, Product, ProductSku
from backend.app.models.enums import AgentRunStatus, ProductStatus, StepStatus
from backend.app.models.user import User, Wallet
from backend.app.schemas.ai import ModelConfigCreate, ShoppingGuideRequest
from backend.app.services.ai_management import AiManagementService
from backend.app.services.shopping_agent import ShoppingAgentService
from backend.app.services.tool_center import ToolCenter, ToolContext


@pytest.mark.asyncio
async def test_builtin_tools_return_real_catalog_data_and_write_logs() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Wallet(id=1, user_id=1, balance=Decimal("88.00")),
                Category(id=1, name="办公", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR001",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    rating=Decimal("4.80"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="CHAIR-SKU-1",
                    name="黑色标准款",
                    price=Decimal("1299.00"),
                    stock=10,
                    locked_stock=2,
                    enabled=True,
                ),
            ]
        )
        await session.commit()

        management = AiManagementService(session)
        tools = await management.seed_builtin_tools()
        search_tool = next(item for item in tools if item.name == "search_products")
        result = await ToolCenter(session).execute_by_name(
            search_tool.name,
            {"keyword": "工学", "min_price": None, "max_price": 1500, "limit": 5},
            ToolContext(user_id=1),
        )

        assert result.status == StepStatus.SUCCEEDED
        assert result.result is not None
        assert result.result["items"][0]["product_id"] == 1
        stock = await ToolCenter(session).execute_by_name(
            "get_product_price_stock", {"product_id": 1}, ToolContext(user_id=1)
        )
        assert stock.result is not None
        assert stock.result["skus"][0]["available_stock"] == 8
        logs = await management.list_tool_logs(page=1, page_size=20)
        assert logs.total == 2
        assert all(item.status == StepStatus.SUCCEEDED for item in logs.items)

    await engine.dispose()


@pytest.mark.asyncio
async def test_model_api_key_is_encrypted_before_persistence() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        public = await AiManagementService(session).create_model_config(
            ModelConfigCreate(
                name="默认模型",
                api_key="sk-test-secret-value",
                is_default=True,
            )
        )
        stored = await session.get(AiModelConfig, public.id)
        assert public.has_api_key is True
        assert stored is not None
        assert stored.api_key_ciphertext is not None
        assert "sk-test-secret-value" not in stored.api_key_ciphertext

    await engine.dispose()


@pytest.mark.asyncio
async def test_submit_recommendation_revalidates_and_replaces_model_candidates() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

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
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="CHAIR-SKU-1",
                    name="黑色标准款",
                    price=Decimal("1299.00"),
                    stock=10,
                    locked_stock=2,
                    enabled=True,
                ),
                AgentRun(
                    id=1,
                    run_no="AR-RECOMMENDATION-TEST",
                    user_id=1,
                    request_text="预算 1500 元买办公椅",
                    status=AgentRunStatus.RUNNING,
                    max_steps=6,
                    started_at=datetime.now(UTC),
                ),
            ]
        )
        await session.commit()
        tools = await AiManagementService(session).seed_builtin_tools()
        assert any(item.name == "submit_recommendation" for item in tools)
        context = ToolContext(user_id=1, agent_run_id=1)
        result = await ToolCenter(session).execute_by_name(
            "submit_recommendation",
            {
                "summary": "优先考虑支撑性与预算",
                "items": [
                    {
                        "product_id": 1,
                        "sku_id": 1,
                        "reason": "价格只要 99 元，适合久坐",
                    },
                    {"product_id": 999, "sku_id": None, "reason": "模型虚构商品"},
                ],
            },
            context,
        )
        assert result.status == StepStatus.SUCCEEDED
        assert result.result is not None
        assert result.result["accepted_items"][0]["verified_price"] == "1299.00"
        assert result.result["accepted_items"][0]["verified_stock"] == 8
        assert result.result["rejected_items"][0]["product_id"] == 999

        public_run = await ShoppingAgentService(session).get_run(1, 1)
        assert public_run.recommendation is not None
        assert len(public_run.recommendation.items) == 1
        assert public_run.recommendation.items[0].price_snapshot == Decimal("1299.00")

        repeated = await ToolCenter(session).execute_by_name(
            "submit_recommendation",
            {
                "summary": "更新后的推荐摘要",
                "items": [
                    {"product_id": 1, "sku_id": 1, "reason": "更新后的推荐理由"}
                ],
            },
            context,
        )
        assert repeated.status == StepStatus.SUCCEEDED
        item_count = int(
            await session.scalar(select(func.count(RecommendationItem.id))) or 0
        )
        assert item_count == 1
        updated_run = await ShoppingAgentService(session).get_run(1, 1)
        assert updated_run.recommendation is not None
        assert updated_run.recommendation.summary == "更新后的推荐摘要"

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_round_trips_function_output_and_records_steps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class FakeResponses:
        calls = 0

        async def create(self, **kwargs: Any) -> Any:
            self.calls += 1
            usage = SimpleNamespace(input_tokens=10, output_tokens=5)
            if self.calls == 1:
                return SimpleNamespace(
                    id="resp_1",
                    usage=usage,
                    output=[
                        ResponseFunctionToolCall(
                            arguments='{"keyword":"工学","min_price":null,"max_price":1500,"limit":5}',
                            call_id="call_1",
                            name="search_products",
                            type="function_call",
                        )
                    ],
                    output_text="",
                )
            assert kwargs["previous_response_id"] == "resp_1"
            assert kwargs["input"][0]["type"] == "function_call_output"
            return SimpleNamespace(
                id="resp_2",
                usage=usage,
                output=[],
                output_text="推荐人体工学椅，价格 1299 元，并建议确认具体规格库存。",
            )

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            self.responses = FakeResponses()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("backend.app.services.shopping_agent.AsyncOpenAI", FakeClient)

    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Wallet(id=1, user_id=1, balance=Decimal("0.00")),
                Category(id=1, name="办公", slug="office"),
                Product(
                    id=1,
                    category_id=1,
                    name="人体工学椅",
                    product_no="CHAIR001",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    status=ProductStatus.ON_SALE,
                ),
            ]
        )
        await session.commit()
        management = AiManagementService(session)
        await management.create_model_config(
            ModelConfigCreate(
                name="测试默认模型",
                api_key="sk-test-agent-key",
                is_default=True,
            )
        )
        await management.seed_builtin_tools()

        run = await ShoppingAgentService(session).run(
            1, ShoppingGuideRequest(message="预算 1500 元买办公椅", max_steps=4)
        )
        assert run.status == AgentRunStatus.SUCCEEDED
        assert run.final_answer is not None
        assert len(run.steps) == 2
        assert run.steps[0].tool_name == "search_products"
        assert run.steps[0].status == StepStatus.SUCCEEDED

    await engine.dispose()
