import json
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from openai import APIConnectionError
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
                    subtitle="适合日常办公与久坐",
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
        subtitle_search = await ToolCenter(session).execute_by_name(
            search_tool.name,
            {"keyword": "办公", "min_price": None, "max_price": 1500, "limit": 5},
            ToolContext(user_id=1),
        )
        assert subtitle_search.status == StepStatus.SUCCEEDED
        assert subtitle_search.result is not None
        assert subtitle_search.result["count"] == 1
        oversized_limit_search = await ToolCenter(session).execute_by_name(
            search_tool.name,
            {"keyword": "办公", "min_price": None, "max_price": 1500, "limit": "30"},
            ToolContext(user_id=1),
        )
        assert oversized_limit_search.status == StepStatus.SUCCEEDED
        assert oversized_limit_search.result is not None
        assert oversized_limit_search.result["count"] == 1
        stock = await ToolCenter(session).execute_by_name(
            "get_product_price_stock", {"product_id": 1}, ToolContext(user_id=1)
        )
        assert stock.result is not None
        assert stock.result["skus"][0]["available_stock"] == 8
        logs = await management.list_tool_logs(page=1, page_size=20)
        assert logs.total == 4
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
    caplog: pytest.LogCaptureFixture,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class FakeResponses:
        calls = 0

        async def create(self, **kwargs: Any) -> Any:
            self.calls += 1
            assert kwargs["model"] == "qwen3.7-flash"
            assert kwargs["max_tool_calls"] == 1
            assert kwargs["reasoning"] == {"effort": "none"}
            usage = SimpleNamespace(
                input_tokens=10,
                output_tokens=5,
                input_tokens_details=SimpleNamespace(cached_tokens=8),
                output_tokens_details=SimpleNamespace(reasoning_tokens=0),
            )
            if self.calls == 1:
                return SimpleNamespace(
                    _request_id="request_1",
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
                _request_id="request_2",
                id="resp_2",
                usage=usage,
                output=[],
                output_text="推荐人体工学椅，价格 1299 元，并建议确认具体规格库存。",
            )

    class FakeClient:
        def __init__(self, **kwargs: Any) -> None:
            assert kwargs["default_headers"] == {
                "x-dashscope-session-cache": "enable"
            }
            self.responses = FakeResponses()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("backend.app.services.shopping_agent.AsyncOpenAI", FakeClient)
    caplog.set_level("INFO", logger="uvicorn.error.shopping_agent")

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
        assert not hasattr(run, "steps")
        admin_run = await ShoppingAgentService(session).get_admin_run(run.id)
        assert len(admin_run.steps) == 2
        assert admin_run.steps[0].tool_name == "search_products"
        assert admin_run.steps[0].status == StepStatus.SUCCEEDED
        model_call_records = [
            record
            for record in caplog.records
            if record.getMessage().startswith("shopping_agent_model_call ")
        ]
        assert len(model_call_records) == 2
        assert [record.model_call_no for record in model_call_records] == [1, 2]
        assert [record.tool_call_count for record in model_call_records] == [1, 0]
        assert all(record.agent_run_id == run.id for record in model_call_records)
        assert all(record.reasoning_effort == "none" for record in model_call_records)
        assert all(record.input_tokens == 10 for record in model_call_records)
        assert all(record.output_tokens == 5 for record in model_call_records)
        assert all(record.cached_tokens == 8 for record in model_call_records)
        assert all(record.reasoning_tokens == 0 for record in model_call_records)
        assert all(record.duration_ms >= 0 for record in model_call_records)
        assert [record.request_id for record in model_call_records] == [
            "request_1",
            "request_2",
        ]
        assert "cached_tokens=8" in model_call_records[0].getMessage()
        assert "reasoning_tokens=0" in model_call_records[0].getMessage()
        assert "duration_ms=" in model_call_records[0].getMessage()

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_stops_researching_and_finishes_when_recommendation_is_submitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class RepeatingSearchResponses:
        calls = 0
        price_checked = False

        async def create(self, **kwargs: Any) -> Any:
            self.calls += 1
            usage = SimpleNamespace(input_tokens=10, output_tokens=5)
            tool_names = {item["name"] for item in kwargs["tools"]}
            if self.calls == 1:
                call = ResponseFunctionToolCall(
                    arguments='{"keyword":"日常办公用品","min_price":null,"max_price":5000,"limit":5}',
                    call_id="search_empty",
                    name="search_products",
                    type="function_call",
                )
            elif self.calls == 2:
                call = ResponseFunctionToolCall(
                    arguments='{"keyword":"键盘","min_price":null,"max_price":5000,"limit":5}',
                    call_id="search_found",
                    name="search_products",
                    type="function_call",
                )
            elif "search_products" in tool_names:
                call = ResponseFunctionToolCall(
                    arguments='{"keyword":"办公","min_price":null,"max_price":5000,"limit":5}',
                    call_id=f"repeat_{self.calls}",
                    name="search_products",
                    type="function_call",
                )
            elif not self.price_checked:
                self.price_checked = True
                call = ResponseFunctionToolCall(
                    arguments='{"product_id":1}',
                    call_id="price_stock",
                    name="get_product_price_stock",
                    type="function_call",
                )
            else:
                raise AssertionError("系统应保留最后一步并自动提交已发现的商品")
            return SimpleNamespace(
                id=f"resp_{self.calls}",
                usage=usage,
                output=[call],
                output_text="",
            )

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            self.responses = RepeatingSearchResponses()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("backend.app.services.shopping_agent.AsyncOpenAI", FakeClient)

    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Wallet(id=1, user_id=1, balance=Decimal("0.00")),
                Category(id=1, name="数码影音", slug="digital"),
                Product(
                    id=1,
                    category_id=1,
                    name="KeyNest K75 三模机械键盘",
                    product_no="KEYBOARD001",
                    subtitle="兼顾办公和游戏",
                    min_price=Decimal("499.00"),
                    max_price=Decimal("529.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="KEYBOARD-SKU-1",
                    name="标准款",
                    price=Decimal("499.00"),
                    stock=10,
                    locked_stock=0,
                    enabled=True,
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
            1,
            ShoppingGuideRequest(
                message="预算 5000 元，想买一件适合日常办公的商品",
                max_steps=4,
            ),
        )
        assert run.status == AgentRunStatus.SUCCEEDED
        assert run.recommendation is not None
        assert run.recommendation.items[0].product_name == "KeyNest K75 三模机械键盘"
        assert run.actual_steps <= 6

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_uses_verified_catalog_after_three_empty_model_searches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class EmptySearchResponses:
        calls = 0

        async def create(self, **_: Any) -> Any:
            self.calls += 1
            return SimpleNamespace(
                id=f"empty_{self.calls}",
                usage=SimpleNamespace(input_tokens=5, output_tokens=2),
                output=[
                    ResponseFunctionToolCall(
                        arguments=json.dumps(
                            {
                                "keyword": keyword,
                                "min_price": 0,
                                "max_price": 5000,
                                "limit": 10,
                            },
                            ensure_ascii=False,
                        ),
                        call_id=f"empty_call_{index}",
                        name="search_products",
                        type="function_call",
                    )
                    for index, keyword in enumerate(
                        ["办公电脑", "笔记本电脑", "台式机", "显示器"], start=1
                    )
                ],
                output_text="",
            )

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            self.responses = EmptySearchResponses()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("backend.app.services.shopping_agent.AsyncOpenAI", FakeClient)
    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Wallet(id=1, user_id=1, balance=Decimal("0.00")),
                Category(id=1, name="数码影音", slug="digital"),
                Product(
                    id=1,
                    category_id=1,
                    name="KeyNest K75 三模机械键盘",
                    product_no="KEYBOARD001",
                    subtitle="兼顾办公和游戏",
                    min_price=Decimal("499.00"),
                    max_price=Decimal("529.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="KEYBOARD-SKU-1",
                    name="标准款",
                    price=Decimal("499.00"),
                    stock=10,
                    locked_stock=0,
                    enabled=True,
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
            1,
            ShoppingGuideRequest(
                message="预算 5000 元，想买一件适合日常办公的商品",
                max_steps=6,
            ),
        )
        assert run.status == AgentRunStatus.SUCCEEDED
        assert run.recommendation is not None
        assert run.recommendation.items[0].product_name == "KeyNest K75 三模机械键盘"

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_returns_labeled_backup_for_underspecified_gift_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class GiftClarificationResponse:
        async def create(self, **_: Any) -> Any:
            return SimpleNamespace(
                id="gift_clarification",
                usage=SimpleNamespace(input_tokens=5, output_tokens=2),
                output=[],
                output_text="请补充父母的年龄和兴趣。",
            )

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            self.responses = GiftClarificationResponse()

        async def close(self) -> None:
            pass

    monkeypatch.setattr("backend.app.services.shopping_agent.AsyncOpenAI", FakeClient)
    async with session_factory() as session:
        session.add_all(
            [
                User(id=1, username="buyer", password_hash="unused"),
                Wallet(id=1, user_id=1, balance=Decimal("0.00")),
                Category(id=1, name="数码影音", slug="digital"),
                Product(
                    id=1,
                    category_id=1,
                    name="KeyNest K75 三模机械键盘",
                    product_no="KEYBOARD001",
                    subtitle="75% 紧凑配列，兼顾办公和游戏",
                    min_price=Decimal("499.00"),
                    max_price=Decimal("529.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="KEYBOARD-SKU-1",
                    name="标准款",
                    price=Decimal("499.00"),
                    stock=10,
                    locked_stock=0,
                    enabled=True,
                ),
                Product(
                    id=2,
                    category_id=1,
                    name="Morrow 手冲咖啡礼盒套装",
                    product_no="COFFEE001",
                    subtitle="细口壶、陶瓷滤杯与耐热玻璃分享壶",
                    min_price=Decimal("369.00"),
                    max_price=Decimal("399.00"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=2,
                    product_id=2,
                    sku_no="COFFEE-SKU-1",
                    name="胡桃木经典款",
                    price=Decimal("369.00"),
                    stock=10,
                    locked_stock=0,
                    enabled=True,
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
            1,
            ShoppingGuideRequest(
                message="想给父母挑一件实用、操作简单的礼物",
                max_steps=6,
            ),
        )
        assert run.status == AgentRunStatus.SUCCEEDED
        assert run.recommendation is not None
        assert run.recommendation.items[0].product_name == "Morrow 手冲咖啡礼盒套装"
        assert "相关性较弱" in (run.recommendation.summary or "")
        assert "低相关性备选" in run.recommendation.items[0].reason
        assert "外部 AI 服务暂时不可用" not in (run.final_answer or "")

    await engine.dispose()


@pytest.mark.asyncio
async def test_agent_falls_back_to_verified_catalog_when_model_connection_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    class UnavailableResponses:
        models: list[str] = []

        async def create(self, **kwargs: Any) -> Any:
            self.models.append(kwargs["model"])
            raise APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))

    class FakeClient:
        def __init__(self, **_: Any) -> None:
            self.responses = UnavailableResponses()

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
                    name="人体工学办公椅",
                    product_no="CHAIR001",
                    subtitle="适合久坐和日常办公",
                    min_price=Decimal("1299.00"),
                    max_price=Decimal("1299.00"),
                    rating=Decimal("4.80"),
                    status=ProductStatus.ON_SALE,
                ),
                ProductSku(
                    id=1,
                    product_id=1,
                    sku_no="CHAIR-SKU-1",
                    name="标准款",
                    price=Decimal("1299.00"),
                    stock=10,
                    locked_stock=0,
                    enabled=True,
                ),
            ]
        )
        await session.commit()
        management = AiManagementService(session)
        await management.create_model_config(
            ModelConfigCreate(
                name="连接失败模型",
                api_key="sk-test-agent-key",
                is_default=True,
            )
        )
        await management.seed_builtin_tools()

        run = await ShoppingAgentService(session).run(
            1,
            ShoppingGuideRequest(
                message="预算 5000 元，想买一件适合日常办公的商品",
                max_steps=6,
            ),
        )
        assert run.status == AgentRunStatus.SUCCEEDED
        assert run.recommendation is not None
        assert run.recommendation.items[0].product_name == "人体工学办公椅"
        assert "基础推荐" in (run.recommendation.summary or "")
        assert UnavailableResponses.models == ["qwen3.7-flash", "qwen3.7-plus"]

    await engine.dispose()
