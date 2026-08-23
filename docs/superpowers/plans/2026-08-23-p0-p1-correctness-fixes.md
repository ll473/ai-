# P0/P1 Correctness Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复容器迁移配置、订单重复优惠、价格库存问答工具依赖和多 SKU 优惠错误，同时恢复 CI 质量检查。

**Architecture:** 保留现有公开 API 和数据库结构，新增订单级促销计算入口与独立的商品价格库存查询服务。订单服务只消费促销结果，消费者问答和 Agent 工具共享同一查询服务，但只有 Agent 工具受 FunctionTool 开关控制。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy Async、Alembic、Pytest、Pydantic、Ruff、Mypy、Vue 3、pnpm、Docker

**Spec:** `docs/superpowers/specs/2026-08-23-p0-p1-correctness-fixes-design.md`

## Global Constraints

- 不修改数据库结构、历史订单或前端 API 调用。
- 保留 `best_promotion(session, product_id, amount)` 的名称、参数和单商品行为。
- 全场优惠与商品优惠不叠加，选择优惠金额更高的方案；金额相同时选择全场方案。
- 一个促销在其业务作用域内每个订单最多应用一次。
- `PRICE_STOCK` 不得依赖 FunctionTool 是否存在或启用。
- 每个 SKU 必须返回自己的价格、可售库存和以一件价格计算的优惠。
- 采用红—绿—重构流程；每个行为测试必须先看到预期失败，再修改生产代码。
- 不覆盖或提交当前工作区中与本计划无关的用户改动；每次提交只暂存任务列出的文件。

## File Map

- `Dockerfile`：把 Alembic 配置放入运行镜像。
- `tests/test_deployment_config.py`：部署镜像静态配置回归测试。
- `backend/app/repositories/promotion.py`：仅负责读取指定时间和商品范围内的有效促销。
- `backend/app/services/promotion.py`：单商品与订单级促销选择和金额计算。
- `tests/test_promotion.py`：订单级促销规则的数据库集成测试。
- `backend/app/services/trade.py`：创建订单时一次性调用订单级促销入口。
- `tests/test_trade_flow.py`：订单创建的重复优惠回归测试。
- `backend/app/repositories/catalog.py`：提供按商品读取启用 SKU 的查询。
- `backend/app/services/product_price_stock.py`：价格、库存和逐 SKU 优惠的唯一业务查询入口。
- `backend/app/services/tool_center.py`：把共享查询结果转换为 Agent 工具结果。
- `backend/app/api/v1/routes/ai.py`：消费者 PRICE_STOCK 问答直接调用共享服务并格式化答案。
- `tests/test_product_price_stock.py`：共享查询、Agent 工具和消费者问答回归测试。
- `backend/app/services/shopping_agent.py`、`tests/test_ai_foundation.py`：修复当前两处 Ruff 阻断。

---

### Task 1: Package Alembic configuration in the runtime image

**Files:**
- Create: `tests/test_deployment_config.py`
- Modify: `Dockerfile:15-17`

**Interfaces:**
- Consumes: 根目录 `alembic.ini`，其中 `script_location = backend/alembic`。
- Produces: 运行镜像中的 `/app/alembic.ini`，供 `backend.scripts.migrate.migrate()` 使用。

- [ ] **Step 1: Write the failing deployment configuration test**

```python
from pathlib import Path

from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_image_copies_valid_alembic_configuration() -> None:
    dockerfile = (PROJECT_ROOT / "Dockerfile").read_text(encoding="utf-8")
    config = Config(PROJECT_ROOT / "alembic.ini")

    assert "COPY alembic.ini ./" in dockerfile
    assert config.get_main_option("script_location") == "backend/alembic"
```

- [ ] **Step 2: Run the test and verify the missing COPY causes the failure**

Run: `.venv\Scripts\python.exe -m pytest tests/test_deployment_config.py -v`

Expected: FAIL at `assert "COPY alembic.ini ./" in dockerfile`.

- [ ] **Step 3: Copy the configuration in the runtime stage**

Change the runtime copy block to:

```dockerfile
COPY pyproject.toml uv.lock README.md alembic.ini ./
COPY backend/ ./backend/
```

- [ ] **Step 4: Re-run the focused test**

Run: `.venv\Scripts\python.exe -m pytest tests/test_deployment_config.py -v`

Expected: PASS.

- [ ] **Step 5: Commit only the deployment change**

```powershell
git add -- Dockerfile tests/test_deployment_config.py
git commit -m "fix: include Alembic config in runtime image"
```

---

### Task 2: Add deterministic order-level promotion calculation

**Files:**
- Create: `backend/app/repositories/promotion.py`
- Modify: `backend/app/services/promotion.py`
- Create: `tests/test_promotion.py`

**Interfaces:**
- Consumes: `Promotion` rows and `PromotionType`; `PromotionLine(product_id: int, amount: Decimal)` values.
- Produces: `best_order_promotion(session, lines, *, at=None) -> OrderPromotionResult`.
- Produces: `OrderPromotionResult(strategy: Literal["NONE", "GLOBAL", "PRODUCT"], discount_amount: Decimal, promotions: tuple[AppliedPromotion, ...])`.
- Preserves: `best_promotion(session, product_id, amount, *, at=None) -> AppliedPromotion | None`.

- [ ] **Step 1: Write order promotion tests against the desired public interface**

Create `tests/test_promotion.py` with an in-memory SQLite session helper and these tests:

```python
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.models import Base
from backend.app.models.enums import PromotionType
from backend.app.models.trade import Promotion
from backend.app.services.promotion import PromotionLine, best_order_promotion


NOW = datetime.now(UTC)


def promotion(
    *,
    name: str,
    product_id: int | None,
    promotion_type: PromotionType,
    value: str,
    minimum: str = "0.00",
    priority: int = 0,
) -> Promotion:
    return Promotion(
        name=name,
        product_id=product_id,
        promotion_type=promotion_type,
        value=Decimal(value),
        minimum_amount=Decimal(minimum),
        starts_at=NOW - timedelta(days=1),
        ends_at=NOW + timedelta(days=1),
        priority=priority,
        enabled=True,
    )


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as value:
        yield value
    await engine.dispose()


@pytest.mark.asyncio
async def test_global_fixed_promotion_applies_once_across_multiple_lines(
    session: AsyncSession,
) -> None:
    session.add(
        promotion(
            name="全场立减",
            product_id=None,
            promotion_type=PromotionType.FIXED,
            value="20.00",
        )
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [
            PromotionLine(product_id=1, amount=Decimal("60.00")),
            PromotionLine(product_id=2, amount=Decimal("60.00")),
        ],
        at=NOW,
    )

    assert result.strategy == "GLOBAL"
    assert result.discount_amount == Decimal("20.00")
    assert len(result.promotions) == 1


@pytest.mark.asyncio
async def test_product_promotion_aggregates_multiple_skus_of_same_product(
    session: AsyncSession,
) -> None:
    session.add(
        promotion(
            name="商品满减",
            product_id=1,
            promotion_type=PromotionType.FIXED,
            value="30.00",
            minimum="100.00",
        )
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [
            PromotionLine(product_id=1, amount=Decimal("60.00")),
            PromotionLine(product_id=1, amount=Decimal("60.00")),
        ],
        at=NOW,
    )

    assert result.strategy == "PRODUCT"
    assert result.discount_amount == Decimal("30.00")
    assert len(result.promotions) == 1


@pytest.mark.asyncio
async def test_product_plan_can_beat_global_plan(session: AsyncSession) -> None:
    session.add_all(
        [
            promotion(
                name="全场减三十",
                product_id=None,
                promotion_type=PromotionType.FIXED,
                value="30.00",
            ),
            promotion(
                name="商品一减二十",
                product_id=1,
                promotion_type=PromotionType.FIXED,
                value="20.00",
            ),
            promotion(
                name="商品二减二十",
                product_id=2,
                promotion_type=PromotionType.FIXED,
                value="20.00",
            ),
        ]
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [
            PromotionLine(product_id=1, amount=Decimal("50.00")),
            PromotionLine(product_id=2, amount=Decimal("50.00")),
        ],
        at=NOW,
    )

    assert result.strategy == "PRODUCT"
    assert result.discount_amount == Decimal("40.00")
    assert {item.name for item in result.promotions} == {
        "商品一减二十",
        "商品二减二十",
    }


@pytest.mark.asyncio
async def test_global_plan_wins_equal_discount_and_caps_at_order_amount(
    session: AsyncSession,
) -> None:
    session.add_all(
        [
            promotion(
                name="全场大额立减",
                product_id=None,
                promotion_type=PromotionType.FIXED,
                value="100.00",
            ),
            promotion(
                name="商品大额立减",
                product_id=1,
                promotion_type=PromotionType.FIXED,
                value="100.00",
            ),
        ]
    )
    await session.commit()

    result = await best_order_promotion(
        session,
        [PromotionLine(product_id=1, amount=Decimal("50.00"))],
        at=NOW,
    )

    assert result.strategy == "GLOBAL"
    assert result.discount_amount == Decimal("50.00")


@pytest.mark.asyncio
async def test_no_active_promotion_returns_zero(session: AsyncSession) -> None:
    result = await best_order_promotion(
        session,
        [PromotionLine(product_id=1, amount=Decimal("50.00"))],
        at=NOW,
    )

    assert result.strategy == "NONE"
    assert result.discount_amount == Decimal("0.00")
    assert result.promotions == ()
```

- [ ] **Step 2: Run the new tests and verify the new interface is missing**

Run: `.venv\Scripts\python.exe -m pytest tests/test_promotion.py -v`

Expected: collection FAIL because `PromotionLine` and `best_order_promotion` do not exist.

- [ ] **Step 3: Add the promotion repository**

Create `backend/app/repositories/promotion.py`:

```python
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
```

- [ ] **Step 4: Implement the order-level types and calculator**

Refactor `backend/app/services/promotion.py` so both public entry points use shared `_apply_promotion()` and `_best_promotion()` helpers. Add these exact public types and signature:

```python
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from backend.app.repositories.promotion import PromotionRepository


@dataclass(frozen=True)
class PromotionLine:
    product_id: int
    amount: Decimal


@dataclass(frozen=True)
class OrderPromotionResult:
    strategy: Literal["NONE", "GLOBAL", "PRODUCT"]
    discount_amount: Decimal
    promotions: tuple[AppliedPromotion, ...]


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
```

Implement `_apply_promotion(promotion: Promotion, amount: Decimal) -> AppliedPromotion | None` with the existing threshold, percentage/fixed amount, money rounding and amount cap. Implement `_best_promotion(promotions: Iterable[Promotion], amount: Decimal)` by retaining the first candidate on equal discount; repository ordering therefore resolves priority and ID ties. Update `best_promotion()` to query via `PromotionRepository` and filter the returned global/product candidates without changing its result semantics.

- [ ] **Step 5: Run promotion tests and the existing compatibility test**

Run: `.venv\Scripts\python.exe -m pytest tests/test_promotion.py tests/test_feature_completion.py::test_best_promotion_uses_largest_valid_discount -v`

Expected: all tests PASS.

- [ ] **Step 6: Commit the promotion domain change**

```powershell
git add -- backend/app/repositories/promotion.py backend/app/services/promotion.py tests/test_promotion.py
git commit -m "fix: calculate promotions once per order scope"
```

---

### Task 3: Use the order-level promotion result during checkout

**Files:**
- Modify: `backend/app/services/trade.py:300-333`
- Modify: `tests/test_trade_flow.py`

**Interfaces:**
- Consumes: `PromotionLine` and `best_order_promotion()` from Task 2.
- Produces: persisted `Order.discount_amount` and `Order.payable_amount` based on exactly one selected promotion strategy.

- [ ] **Step 1: Add an order integration regression test**

Append a test that creates two products, two selected cart rows worth `60.00` each, and one global fixed promotion worth `20.00`. Use the existing in-memory database pattern from `test_cart_order_wallet_payment_closes_inventory_loop()` and assert:

```python
order = await TradeService(session).create_order(1, CheckoutRequest(address_id=1))

assert order.product_amount == Decimal("120.00")
assert order.discount_amount == Decimal("20.00")
assert order.payable_amount == Decimal("100.00")
```

The fixture rows must include `User(id=1)`, `UserAddress(id=1, user_id=1)`, one `Category`, two on-sale `Product` rows, two enabled `ProductSku` rows, two selected `CartItem` rows and this promotion:

```python
Promotion(
    name="全场立减",
    product_id=None,
    promotion_type=PromotionType.FIXED,
    value=Decimal("20.00"),
    minimum_amount=Decimal("0.00"),
    starts_at=datetime.now(UTC) - timedelta(days=1),
    ends_at=datetime.now(UTC) + timedelta(days=1),
    enabled=True,
)
```

- [ ] **Step 2: Run the integration test and observe the duplicate discount**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trade_flow.py::test_checkout_applies_global_fixed_promotion_once -v`

Expected: FAIL because the current loop reports `discount_amount == Decimal("40.00")`.

- [ ] **Step 3: Replace per-line promotion calculation with one order calculation**

In `TradeService.create_order()`, collect `PromotionLine` instances while validating rows, then calculate once after `product_amount` is normalized:

```python
promotion_lines: list[PromotionLine] = []
order_lines: list[tuple[CartItem, Product, ProductSku]] = []

# Inside the validated cart loop:
line_amount = _money(sku.price * cart_item.quantity)
product_amount += line_amount
promotion_lines.append(PromotionLine(product_id=product.id, amount=line_amount))
order_lines.append((cart_item, product, sku))

# After the loop:
product_amount = _money(product_amount)
promotion_result = await best_order_promotion(self.session, promotion_lines)
discount_amount = promotion_result.discount_amount
```

Remove the per-row `best_promotion()` call and import `PromotionLine, best_order_promotion` instead.

- [ ] **Step 4: Run focused trade and promotion tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_trade_flow.py tests/test_promotion.py -v`

Expected: all tests PASS.

- [ ] **Step 5: Commit the checkout integration**

```powershell
git add -- backend/app/services/trade.py tests/test_trade_flow.py
git commit -m "fix: apply order promotion plan during checkout"
```

---

### Task 4: Create the shared per-SKU price and stock query service

**Files:**
- Modify: `backend/app/repositories/catalog.py`
- Create: `backend/app/services/product_price_stock.py`
- Modify: `backend/app/services/tool_center.py:201-234`
- Create: `tests/test_product_price_stock.py`

**Interfaces:**
- Produces: `CatalogRepository.list_product_skus(product_id: int, *, enabled_only: bool = True) -> list[ProductSku]`.
- Produces: `ProductPriceStockService.get(product_id: int) -> ProductPriceStockResult`.
- Produces: `ProductPriceStockResult(product_id: int, product_name: str, skus: tuple[SkuPriceStock, ...])`.
- Produces: `SkuPriceStock(sku_id: int, sku_name: str, price: Decimal, available_stock: int, attributes: dict[str, Any] | None, promotion: AppliedPromotion | None)`.
- Preserves: Agent executor key `catalog.get_product_price_stock` and tool argument `{ "product_id": int }`.

- [ ] **Step 1: Write failing service tests for per-SKU promotions and empty/zero stock states**

In `tests/test_product_price_stock.py`, use the same in-memory SQLite fixture pattern as Task 2. Insert one on-sale product with two enabled SKUs priced `400.00` and `600.00`, plus a product fixed promotion of `100.00` with minimum `500.00`. Assert:

```python
result = await ProductPriceStockService(session).get(1)

assert result.product_name == "测试商品"
assert [item.available_stock for item in result.skus] == [0, 7]
assert result.skus[0].promotion is None
assert result.skus[1].promotion is not None
assert result.skus[1].promotion.discount_amount == Decimal("100.00")
```

Use `stock=3, locked_stock=3` for the first SKU and `stock=10, locked_stock=3` for the second. Add a second test with an on-sale product that has only disabled SKUs and assert `result.skus == ()`. Add a third test with an off-sale product and assert `NotFoundError` with message `商品不存在或已下架`.

- [ ] **Step 2: Run the service tests and verify the module is missing**

Run: `.venv\Scripts\python.exe -m pytest tests/test_product_price_stock.py -v`

Expected: collection FAIL because `backend.app.services.product_price_stock` does not exist.

- [ ] **Step 3: Add the focused catalog repository query**

Add to `CatalogRepository`:

```python
async def list_product_skus(
    self, product_id: int, *, enabled_only: bool = True
) -> list[ProductSku]:
    statement = select(ProductSku).where(ProductSku.product_id == product_id)
    if enabled_only:
        statement = statement.where(ProductSku.enabled.is_(True))
    return list((await self.session.scalars(statement.order_by(ProductSku.id))).all())
```

- [ ] **Step 4: Implement the shared query service**

Create `backend/app/services/product_price_stock.py`:

```python
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
```

- [ ] **Step 5: Re-run service tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_product_price_stock.py -v`

Expected: the service tests PASS.

- [ ] **Step 6: Route the Agent executor through the shared service**

Replace direct `Product`/`ProductSku` queries and the minimum-price promotion in `_get_product_price_stock()` with:

```python
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
```

Remove imports made unused by this replacement. Update the existing ToolCenter price-stock assertion in `tests/test_ai_foundation.py` to verify that each SKU dictionary owns its `promotion` field and that no top-level `promotion` key is returned.

- [ ] **Step 7: Run shared service and Agent foundation tests**

Run: `.venv\Scripts\python.exe -m pytest tests/test_product_price_stock.py tests/test_ai_foundation.py -v`

Expected: all tests PASS.

- [ ] **Step 8: Commit the shared query service and Agent adapter**

```powershell
git add -- backend/app/repositories/catalog.py backend/app/services/product_price_stock.py backend/app/services/tool_center.py tests/test_product_price_stock.py tests/test_ai_foundation.py
git commit -m "fix: query price stock and promotions per SKU"
```

---

### Task 5: Make consumer PRICE_STOCK independent of FunctionTool state

**Files:**
- Modify: `backend/app/api/v1/routes/ai.py:98-124`
- Modify: `tests/test_product_price_stock.py`

**Interfaces:**
- Consumes: `ProductPriceStockService.get()` from Task 4.
- Produces: unchanged `ApiResponse[ProductQuestionResponse]` with per-SKU promotion text.
- Removes: consumer dependency on `ToolCenter.execute_by_name()` and `ToolContext`.

- [ ] **Step 1: Add a failing direct route test with a disabled tool record**

Append an async test that inserts a user, category, on-sale product, enabled SKU, applicable promotion and this disabled tool row:

```python
FunctionTool(
    name="get_product_price_stock",
    display_name="查询商品价格库存",
    description="禁用状态不应影响消费者问答",
    input_schema={"type": "object"},
    executor="catalog.get_product_price_stock",
    enabled=False,
)
```

Call the route function directly so the test uses the real service and transaction behavior:

```python
response = await product_question(
    ProductQuestionRequest(
        question="这个商品各规格多少钱，还有库存吗？",
        question_type=QuestionType.PRICE_STOCK,
        product_id=1,
    ),
    session,
    user,
)

assert response.data is not None
assert "标准款：¥600.00，可售库存 7 件" in response.data.answer
assert "优惠" in response.data.answer
```

Add a second version without inserting any `FunctionTool` row and assert the same successful answer. Use separate test sessions so missing and disabled states cannot leak into each other.

- [ ] **Step 2: Run the focused route tests and observe tool-state failure**

Run: `.venv\Scripts\python.exe -m pytest tests/test_product_price_stock.py -k "consumer" -v`

Expected: FAIL with `工具不存在或已停用` or `价格库存查询失败`.

- [ ] **Step 3: Call ProductPriceStockService directly and format per-SKU promotions**

Replace the PRICE_STOCK branch with this flow:

```python
price_stock = await ProductPriceStockService(session).get(payload.product_id)
lines: list[str] = []
for item in price_stock.skus:
    line = f"{item.sku_name}：¥{item.price}，可售库存 {item.available_stock} 件"
    if item.promotion is not None:
        line += (
            f"，优惠 {item.promotion.name}，"
            f"预计优惠 ¥{item.promotion.discount_amount}"
        )
    lines.append(line)
result = ProductQuestionResponse(
    answer="；".join(lines) or "当前没有可售规格。",
    question_type=payload.question_type,
    citations=[],
)
```

Import `ProductPriceStockService`; remove `ToolCenter` and `ToolContext` from this route when no other branch uses them.

- [ ] **Step 4: Run consumer, service and Agent tests together**

Run: `.venv\Scripts\python.exe -m pytest tests/test_product_price_stock.py tests/test_ai_foundation.py -v`

Expected: missing-tool and disabled-tool consumer tests PASS; Agent tool tests also PASS.

- [ ] **Step 5: Commit the consumer query change**

```powershell
git add -- backend/app/api/v1/routes/ai.py tests/test_product_price_stock.py
git commit -m "fix: decouple consumer price stock QA from tools"
```

---

### Task 6: Restore CI quality gates and perform full verification

**Files:**
- Modify: `backend/app/services/shopping_agent.py:404`
- Modify: `tests/test_ai_foundation.py:1-8`
- Inspect only: all files listed in this plan and `git status --short`

**Interfaces:**
- Consumes: completed Tasks 1–5.
- Produces: clean Ruff/Mypy/test/build/migration verification without changing runtime behavior.

- [ ] **Step 1: Reproduce the two current Ruff failures**

Run: `.venv\Scripts\ruff.exe check backend tests main.py`

Expected: FAIL with `E501` at `backend/app/services/shopping_agent.py:404` and `I001` at `tests/test_ai_foundation.py:1`.

- [ ] **Step 2: Apply the exact formatting fixes**

Split the long user-facing string without changing its text:

```python
return (
    "外部 AI 服务暂时无法连接，商城中也没有找到符合当前预算的在售商品，"
    "请稍后重试或调整预算。",
    step_no,
)
```

Order third-party imports with `httpx` before `pytest`:

```python
import httpx
import pytest
```

- [ ] **Step 3: Verify Ruff and Mypy**

Run: `.venv\Scripts\ruff.exe check backend tests main.py`

Expected: exit code 0 and `All checks passed!`.

Run: `.venv\Scripts\mypy.exe backend main.py`

Expected: exit code 0 and no type errors.

- [ ] **Step 4: Run the complete backend test suite**

Run: `.venv\Scripts\python.exe -m pytest`

Expected: exit code 0 with zero failed tests.

- [ ] **Step 5: Verify the migration chain using an isolated in-memory database**

```powershell
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"
.venv\Scripts\python.exe -m backend.scripts.migrate
Remove-Item Env:DATABASE_URL
```

Expected: every migration from the initial revision through `promotion01` runs and the process exits 0.

- [ ] **Step 6: Verify frontend integration**

Run: `pnpm --dir frontend typecheck`

Expected: exit code 0.

Run: `pnpm --dir frontend build`

Expected: exit code 0. Existing chunk-size warnings may remain because frontend optimization is outside this scope.

- [ ] **Step 7: Build the production container**

Run: `docker build -t ai-commerce:test .`

Expected: exit code 0; the runtime stage includes `/app/alembic.ini` and finishes dependency installation and frontend copy.

- [ ] **Step 8: Inspect the final diff and protect user changes**

Run: `git status --short`

Run: `git diff --check`

Run: `git diff --stat 380cc15..HEAD`

Expected: no whitespace errors. Review every listed file against the File Map; leave unrelated pre-existing modified and untracked files untouched.

- [ ] **Step 9: Commit only the CI cleanup if it was not included earlier**

```powershell
git add -- backend/app/services/shopping_agent.py tests/test_ai_foundation.py
git commit -m "chore: restore CI lint checks"
```

Do not create an empty commit if Task 4 already committed the import-order correction in `tests/test_ai_foundation.py`; in that case commit only `backend/app/services/shopping_agent.py`.
