# 商品对比中心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个最多比较四件同分类商品、可分享、基础事实快速呈现，并支持登录用户按需获取单次 AI 选择建议的商品对比中心。

**Architecture:** 公开批量目录接口一次返回全部对比事实，前端 Pinia store 只保存可持久化的最小商品摘要，并通过 `/compare?ids=` 恢复分享链接。基础对比与 AI 完全解耦；AI 使用登录保护的专用单次非思考模型接口，失败或超时不会改变基础表格。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy 2 async、Pydantic v2、Pytest、Vue 3 `<script setup>`、TypeScript、Pinia、Vue Router、Element Plus、Vitest、Vue Test Utils、pnpm。

**Spec:** `docs/superpowers/specs/2026-08-24-product-comparison-design.md`

## Global Constraints

- 对比清单最多四件商品，且所有商品必须属于同一分类。
- 基础对比无需登录，并在 GitHub Pages 展示模式下从本地演示目录读取。
- 地址格式固定为 `/compare?ids=1,2,3`，链接 ID 去重、过滤非法值并最多保留四个。
- 基础对比只发起一次目录请求；正常本地数据下服务端耗时目标低于 500ms。
- AI 只由用户主动触发，只调用模型一次，使用 `extra_body={"enable_thinking": False}`，服务端硬超时不超过 20 秒。
- AI 响应不得包含模型生成的价格或库存字段；页面价格和库存只来自目录事实接口。
- 不增加数据库表或 Alembic 迁移，不提供可恢复的 AI 对比历史。
- 所有行为变更执行红—绿—重构，先观察测试因缺失行为失败，再写实现。
- 每个任务完成后更新本文件复选框并提交；中断后从第一个未勾选步骤恢复。
- 不提交工作区原有 `.github/` 草稿和根目录微信图片。

---

## 文件结构

### 后端

- `backend/app/schemas/catalog.py`：公开批量对比事实 DTO。
- `backend/app/repositories/catalog.py`：固定两次查询读取商品/分类/品牌与启用 SKU。
- `backend/app/services/catalog.py`：输入校验、顺序恢复、失效商品和同分类规则。
- `backend/app/api/v1/routes/catalog.py`：静态批量对比路由。
- `backend/app/schemas/ai.py`：AI 对比请求与结构化响应 DTO。
- `backend/app/services/product_comparison_ai.py`：事实压缩、百炼单次调用、超时与响应校验。
- `backend/app/api/v1/routes/ai.py`：登录保护的 AI 对比路由。
- `tests/test_product_comparison.py`：批量事实服务与查询上界测试。
- `tests/test_product_comparison_ai.py`：AI 服务事实约束、单次调用和超时测试。

### 前端

- `frontend/src/types/catalog.ts`：批量对比目录类型。
- `frontend/src/types/ai.ts`：AI 对比结果类型。
- `frontend/src/demo/catalog.ts`：展示版同形批量结果。
- `frontend/src/api/catalog.ts`：批量事实 API。
- `frontend/src/api/catalog.test.ts`：批量事实短时缓存测试。
- `frontend/src/api/ai.ts`：AI 对比 API。
- `frontend/src/stores/compare.ts`：清单规则、`localStorage` 与分享 ID 同步。
- `frontend/src/stores/compare.test.ts`：store 边界测试。
- `frontend/src/components/catalog/CompareToggleButton.vue`：卡片和详情共用的加入/移除入口。
- `frontend/src/components/catalog/ProductCompareTray.vue`：全局底部对比栏。
- `frontend/src/components/catalog/ProductComparisonAiPanel.vue`：登录、展示模式、会话缓存和 AI 结果状态。
- `frontend/src/components/catalog/ProductComparisonAiPanel.test.ts`：AI 面板行为测试。
- `frontend/src/components/ProductCard.vue`：接入不触发导航的对比按钮。
- `frontend/src/components/ProductCard.test.ts`：商品卡片点击边界测试。
- `frontend/src/layouts/StoreLayout.vue`：挂载全局对比栏。
- `frontend/src/views/store/ProductDetailView.vue`：接入对比入口。
- `frontend/src/views/store/ProductDetailView.test.ts`：详情页对比入口回归。
- `frontend/src/views/store/ProductComparisonView.vue`：地址恢复、基础表格、仅看差异和失效项处理。
- `frontend/src/views/store/ProductComparisonView.test.ts`：基础对比页行为测试。
- `frontend/src/router/index.ts`：公开 `/compare` 路由。
- `README.md`：使用方式、限制、分享和 AI 登录条件。

---

### Task 1: 公开批量商品事实接口

**Files:**
- Create: `tests/test_product_comparison.py`
- Modify: `backend/app/schemas/catalog.py`
- Modify: `backend/app/repositories/catalog.py`
- Modify: `backend/app/services/catalog.py`
- Modify: `backend/app/api/v1/routes/catalog.py`

**Interfaces:**
- Consumes: `Product`、`Category`、`Brand`、`ProductSku` 与现有 `_sku_public()`。
- Produces: `CatalogService.compare_products(product_ids: Sequence[int]) -> ProductComparisonResult`。
- Produces: `GET /api/v1/catalog/products/compare?ids=1,2,3`。
- Produces: `ProductComparisonItem` 与 `ProductComparisonResult` Pydantic DTO。

- [x] **Step 1: 编写批量事实服务失败测试**

在 `tests/test_product_comparison.py` 建立内存 SQLite 数据，包含两件同分类在售商品、一件跨分类商品、一件下架商品、品牌和启用/禁用 SKU。先写以下核心断言：

```python
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@asynccontextmanager
async def seeded_session() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            session.add_all([
                Category(id=10, name="数码影音", slug="digital"),
                Category(id=20, name="办公效率", slug="office"),
                Brand(id=1, name="EchoArc", slug="echoarc"),
                Product(id=1, category_id=10, name="耳机 A", product_no="A-1",
                        status=ProductStatus.ON_SALE),
                Product(id=2, category_id=10, brand_id=1, name="耳机 B",
                        product_no="B-2", status=ProductStatus.ON_SALE),
                Product(id=3, category_id=20, name="办公椅", product_no="C-3",
                        status=ProductStatus.ON_SALE),
                Product(id=4, category_id=10, name="下架耳机", product_no="D-4",
                        status=ProductStatus.OFF_SALE),
                ProductSku(id=11, product_id=1, sku_no="A-1-S", name="标准版",
                           price=Decimal("599.00"), stock=5, locked_stock=1,
                           enabled=True),
                ProductSku(id=21, product_id=2, sku_no="B-2-S", name="标准版",
                           price=Decimal("899.00"), stock=9, locked_stock=2,
                           enabled=True),
                ProductSku(id=22, product_id=2, sku_no="B-2-X", name="停用规格",
                           price=Decimal("999.00"), stock=8, locked_stock=0,
                           enabled=False),
            ])
            await session.commit()
            yield session
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_compare_products_preserves_order_and_marks_unavailable() -> None:
    async with seeded_session() as session:
        result = await CatalogService(session).compare_products([2, 999, 1, 4])

    assert [item.id for item in result.items] == [2, 1]
    assert result.unavailable_ids == [999, 4]
    assert result.items[0].category_name == "数码影音"
    assert result.items[0].brand_name == "EchoArc"
    assert result.items[0].total_available_stock == 7
    assert all(sku.enabled for item in result.items for sku in item.skus)


@pytest.mark.asyncio
async def test_compare_products_rejects_cross_category_candidates() -> None:
    async with seeded_session() as session:
        with pytest.raises(AppError, match="只能对比同一分类商品") as captured:
            await CatalogService(session).compare_products([1, 3])

    assert captured.value.status_code == 422
    assert captured.value.code == "COMPARISON_CATEGORY_MISMATCH"
```

- [x] **Step 2: 运行测试并确认因接口不存在而失败**

Run: `uv run pytest tests/test_product_comparison.py -q`

Expected: FAIL，错误明确指向 `CatalogService.compare_products` 或对比 DTO 尚不存在，而不是测试数据建表失败。

- [x] **Step 3: 添加目录 DTO 和固定查询上界的 repository 方法**

在 `backend/app/schemas/catalog.py` 添加：

```python
class ProductComparisonItem(ProductSummary):
    category_name: str
    brand_name: str | None = None
    parameters: dict[str, Any] | None = None
    skus: list[SkuPublic]
    total_available_stock: int


class ProductComparisonResult(BaseModel):
    items: list[ProductComparisonItem]
    unavailable_ids: list[int]
    category_id: int | None = None
    category_name: str | None = None
```

在 `CatalogRepository` 添加固定两次 SELECT 的接口：

```python
ComparisonProductRow = tuple[Product, Category, Brand | None]

async def get_products_for_comparison(
    self, product_ids: Sequence[int]
) -> tuple[list[ComparisonProductRow], list[ProductSku]]:
    rows = list((await self.session.execute(
        select(Product, Category, Brand)
        .join(Category, Category.id == Product.category_id)
        .outerjoin(Brand, Brand.id == Product.brand_id)
        .where(Product.id.in_(product_ids), Product.status == ProductStatus.ON_SALE)
    )).all())
    found_ids = [product.id for product, _, _ in rows]
    skus = list((await self.session.scalars(
        select(ProductSku)
        .where(ProductSku.product_id.in_(found_ids), ProductSku.enabled.is_(True))
        .order_by(ProductSku.product_id, ProductSku.id)
    )).all()) if found_ids else []
    return rows, skus
```

- [x] **Step 4: 实现服务规则与静态路由**

在 `CatalogService` 添加：

```python
def _comparison_item(
    product: Product,
    category: Category,
    brand: Brand | None,
    skus: list[ProductSku],
) -> ProductComparisonItem:
    public_skus = [_sku_public(sku) for sku in skus]
    return ProductComparisonItem(
        **ProductSummary.model_validate(product).model_dump(),
        category_name=category.name,
        brand_name=brand.name if brand else None,
        parameters=product.parameters,
        skus=public_skus,
        total_available_stock=sum(sku.available_stock for sku in public_skus),
    )


async def compare_products(self, product_ids: Sequence[int]) -> ProductComparisonResult:
    ordered_ids = list(dict.fromkeys(product_ids))
    if not 2 <= len(ordered_ids) <= 4:
        raise AppError(
            "请选择 2–4 件商品进行对比",
            code="COMPARISON_SIZE_INVALID",
            status_code=422,
        )
    rows, skus = await self.catalog.get_products_for_comparison(ordered_ids)
    row_by_id = {product.id: (product, category, brand) for product, category, brand in rows}
    categories = {product.category_id for product, _, _ in rows}
    if len(categories) > 1:
        raise AppError(
            "只能对比同一分类商品",
            code="COMPARISON_CATEGORY_MISMATCH",
            status_code=422,
        )
    skus_by_product: dict[int, list[ProductSku]] = defaultdict(list)
    for sku in skus:
        skus_by_product[sku.product_id].append(sku)
    items = [
        _comparison_item(*row_by_id[product_id], skus_by_product[product_id])
        for product_id in ordered_ids
        if product_id in row_by_id
    ]
    unavailable_ids = [product_id for product_id in ordered_ids if product_id not in row_by_id]
    return ProductComparisonResult(
        items=items,
        unavailable_ids=unavailable_ids,
        category_id=items[0].category_id if items else None,
        category_name=items[0].category_name if items else None,
    )
```

在动态 `/products/{product_id}` 之前注册路由，并用一个小函数解析逗号 ID、拒绝非整数：

```python
@router.get("/products/compare", response_model=ApiResponse[ProductComparisonResult])
async def compare_products(
    session: DbSession,
    ids: Annotated[str, Query(min_length=3, max_length=100)],
) -> ApiResponse[ProductComparisonResult]:
    try:
        product_ids = [int(value.strip()) for value in ids.split(",") if value.strip()]
    except ValueError as exc:
        raise AppError(
            "商品对比链接无效", code="COMPARISON_IDS_INVALID", status_code=422
        ) from exc
    return ApiResponse(data=await CatalogService(session).compare_products(product_ids))
```

- [x] **Step 5: 添加查询次数和路由顺序回归测试**

在种子数据提交完成后监听 SQLAlchemy `before_cursor_execute`，只统计 `compare_products()` 阶段的 SELECT，并断言恰好两次。再从 `catalog.router.routes` 取路径顺序，断言静态路径先于动态路径：

```python
assert select_count == 2
paths = [route.path for route in catalog_routes.router.routes]
assert paths.index("/catalog/products/compare") < paths.index("/catalog/products/{product_id}")
```

- [x] **Step 6: 运行目标测试和后端静态检查**

Run: `uv run pytest tests/test_product_comparison.py -q`

Expected: PASS。

Run: `uv run ruff check backend/app/schemas/catalog.py backend/app/repositories/catalog.py backend/app/services/catalog.py backend/app/api/v1/routes/catalog.py tests/test_product_comparison.py`

Expected: exit 0。

- [x] **Step 7: 提交公开批量接口**

```powershell
git add backend/app/schemas/catalog.py backend/app/repositories/catalog.py backend/app/services/catalog.py backend/app/api/v1/routes/catalog.py tests/test_product_comparison.py docs/superpowers/plans/2026-08-24-product-comparison.md
git commit -m "feat: add product comparison catalog API"
```

---

### Task 2: 前端目录类型、展示数据与本地对比 Store

**Files:**
- Modify: `frontend/src/types/catalog.ts`
- Modify: `frontend/src/demo/catalog.ts`
- Modify: `frontend/src/api/catalog.ts`
- Create: `frontend/src/api/catalog.test.ts`
- Create: `frontend/src/stores/compare.ts`
- Create: `frontend/src/stores/compare.test.ts`

**Interfaces:**
- Consumes: Task 1 的 `ProductComparisonResult` JSON 形状。
- Produces: `getProductComparison(productIds: number[]) -> Promise<ProductComparisonResult>`。
- Produces: `useCompareStore()`，公开 `items`、`ids`、`contains`、`add`、`remove`、`clear`、`replaceFromProducts`。
- Produces: `CompareAddResult = { ok: true } | { ok: false; reason: 'category_mismatch' | 'limit_reached' }`。

- [x] **Step 1: 编写 store 失败测试**

在每条测试前执行 `localStorage.clear()` 和 `setActivePinia(createPinia())`，使用字面量摘要断言：

```ts
function summary(id: number, categoryId: number): ProductSummary {
  return {
    id,
    category_id: categoryId,
    brand_id: null,
    name: `商品 ${id}`,
    subtitle: null,
    product_no: `P-${id}`,
    main_image_url: null,
    min_price: '1.00',
    max_price: '1.00',
    rating: '0.00',
    review_count: 0,
    sales_count: 0,
    status: 'ON_SALE',
    created_at: '2026-01-01T00:00:00Z',
  }
}

it('keeps at most four unique products from one category', () => {
  const store = useCompareStore()
  expect(store.add(summary(1, 10))).toEqual({ ok: true })
  expect(store.add(summary(1, 10))).toEqual({ ok: true })
  expect(store.add(summary(2, 11))).toEqual({ ok: false, reason: 'category_mismatch' })
  store.add(summary(3, 10))
  store.add(summary(4, 10))
  store.add(summary(5, 10))
  expect(store.add(summary(6, 10))).toEqual({ ok: false, reason: 'limit_reached' })
  expect(store.ids).toEqual([1, 3, 4, 5])
})

it('recovers from malformed persisted state', () => {
  localStorage.setItem('ai-commerce-product-compare-v1', '{broken')
  const store = useCompareStore()
  expect(store.items).toEqual([])
  expect(localStorage.getItem('ai-commerce-product-compare-v1')).toBeNull()
})
```

- [x] **Step 2: 运行测试并确认 store 缺失**

Run: `pnpm exec vitest run src/stores/compare.test.ts`（工作目录 `frontend`）

Expected: FAIL，提示 `./compare` 模块不存在。

- [x] **Step 3: 添加目录类型、展示版批量函数和 API**

在 `frontend/src/types/catalog.ts` 添加与后端一致的接口：

```ts
export interface ProductComparisonItem extends ProductSummary {
  category_name: string
  brand_name: string | null
  parameters: Record<string, unknown> | null
  skus: ProductSku[]
  total_available_stock: number
}

export interface ProductComparisonResult {
  items: ProductComparisonItem[]
  unavailable_ids: number[]
  category_id: number | null
  category_name: string | null
}
```

在演示目录添加 `getDemoProductComparison(productIds)`：去重、限制 2–4 件、只保留在售商品、验证同分类，并从 `demoCategories`/`demoBrands` 填充名称和总可售库存。在 API 层添加 30 秒内存缓存，缓存只存在当前页面进程且不写入 compare store：

```ts
const comparisonCache = new Map<string, {
  expiresAt: number
  data: ProductComparisonResult
}>()

export async function getProductComparison(productIds: number[]) {
  const key = productIds.join(',')
  const cached = comparisonCache.get(key)
  if (cached && cached.expiresAt > Date.now()) return cached.data
  const data = demoMode
    ? getDemoProductComparison(productIds)
    : (await http.get<ApiResponse<ProductComparisonResult>>(
        '/catalog/products/compare',
        { params: { ids: key } },
      )).data.data
  comparisonCache.set(key, { data, expiresAt: Date.now() + 30_000 })
  return data
}
```

在 `frontend/src/api/catalog.test.ts` 使用 `vi.resetModules()` 隔离模块级 Map，mock `http.get` 返回完整 `ProductComparisonResult`。同一 ID 组合连续调用两次时断言只请求一次；`vi.setSystemTime()` 前进 30,001ms 后第三次调用断言请求次数变为两次。

- [x] **Step 4: 实现最小 Pinia store**

持久化结构只保存最小摘要：

```ts
export interface CompareSelection {
  id: number
  category_id: number
  name: string
  main_image_url: string | null
}

const STORAGE_KEY = 'ai-commerce-product-compare-v1'

function toSelection(product: ProductSummary): CompareSelection {
  return {
    id: product.id,
    category_id: product.category_id,
    name: product.name,
    main_image_url: product.main_image_url,
  }
}

function isSelection(value: unknown): value is CompareSelection {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  return Number.isInteger(item.id)
    && Number(item.id) > 0
    && Number.isInteger(item.category_id)
    && Number(item.category_id) > 0
    && typeof item.name === 'string'
    && (item.main_image_url === null || typeof item.main_image_url === 'string')
}

function persist(items: CompareSelection[]) {
  if (items.length) localStorage.setItem(STORAGE_KEY, JSON.stringify(items))
  else localStorage.removeItem(STORAGE_KEY)
}

function readStoredSelections(): CompareSelection[] {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (!stored) return []
  try {
    const parsed: unknown = JSON.parse(stored)
    if (!Array.isArray(parsed)) throw new Error('invalid comparison state')
    const selections: CompareSelection[] = []
    for (const value of parsed) {
      if (!isSelection(value) || selections.some(item => item.id === value.id)) continue
      if (selections.length && selections[0].category_id !== value.category_id) continue
      selections.push(value)
      if (selections.length === 4) break
    }
    persist(selections)
    return selections
  } catch {
    localStorage.removeItem(STORAGE_KEY)
    return []
  }
}

export const useCompareStore = defineStore('compare', () => {
  const items = shallowRef<CompareSelection[]>(readStoredSelections())
  const ids = computed(() => items.value.map(item => item.id))
  const contains = (productId: number) => items.value.some(item => item.id === productId)

  function add(product: ProductSummary): CompareAddResult {
    if (contains(product.id)) return { ok: true }
    if (items.value.length && items.value[0].category_id !== product.category_id)
      return { ok: false, reason: 'category_mismatch' }
    if (items.value.length >= 4) return { ok: false, reason: 'limit_reached' }
    items.value = [...items.value, toSelection(product)]
    persist(items.value)
    return { ok: true }
  }

  function remove(productId: number) {
    items.value = items.value.filter(item => item.id !== productId)
    persist(items.value)
  }

  function clear() {
    items.value = []
    persist(items.value)
  }

  function replaceFromProducts(products: ProductSummary[]) {
    items.value = products.slice(0, 4).map(toSelection)
    persist(items.value)
  }

  return { items: readonly(items), ids, contains, add, remove, clear, replaceFromProducts }
})
```

`readStoredSelections()` 必须验证数组、整数 ID、整数分类 ID、字符串名称，并过滤重复/超量项；无效 JSON 时删除版本键。`replaceFromProducts()` 使用批量接口真实商品修正分享链接恢复后的摘要。

- [x] **Step 5: 运行 store 与类型构建测试**

Run: `pnpm exec vitest run src/stores/compare.test.ts src/api/catalog.test.ts`（工作目录 `frontend`）

Expected: PASS。

Run: `pnpm typecheck`（工作目录 `frontend`）

Expected: exit 0。

- [x] **Step 6: 提交前端数据基础**

```powershell
git add frontend/src/types/catalog.ts frontend/src/demo/catalog.ts frontend/src/api/catalog.ts frontend/src/api/catalog.test.ts frontend/src/stores/compare.ts frontend/src/stores/compare.test.ts docs/superpowers/plans/2026-08-24-product-comparison.md
git commit -m "feat: add local product comparison state"
```

---

### Task 3: 商品入口与全局对比栏

**Files:**
- Create: `frontend/src/components/catalog/CompareToggleButton.vue`
- Create: `frontend/src/components/catalog/ProductCompareTray.vue`
- Create: `frontend/src/components/ProductCard.test.ts`
- Modify: `frontend/src/components/ProductCard.vue`
- Modify: `frontend/src/layouts/StoreLayout.vue`
- Modify: `frontend/src/views/store/ProductDetailView.vue`
- Modify: `frontend/src/views/store/ProductDetailView.test.ts`

**Interfaces:**
- Consumes: Task 2 的 `useCompareStore()` 与 `CompareAddResult`。
- Produces: `CompareToggleButton` props `{ product: ProductSummary; compact?: boolean }`。
- Produces: `ProductCompareTray` 无 props，全局读取 store。

- [x] **Step 1: 编写商品卡片和详情入口失败测试**

新增卡片测试，使用真实 Pinia 和 RouterLink stub，点击对比按钮后断言 store 更新且导航未触发：

```ts
await wrapper.get('button[aria-label="加入商品对比"]').trigger('click')
expect(compare.ids).toEqual([42])
expect(routerPush).not.toHaveBeenCalled()
expect(wrapper.get('button').text()).toContain('已加入对比')
```

在 `ProductDetailView.test.ts` 增加相同用户可见行为测试，并为 compare store 使用测试 Pinia，不访问 `wrapper.vm`。

- [x] **Step 2: 运行入口测试并确认按钮缺失**

Run: `pnpm exec vitest run src/components/ProductCard.test.ts src/views/store/ProductDetailView.test.ts`（工作目录 `frontend`）

Expected: FAIL，找不到 `aria-label="加入商品对比"`。

- [x] **Step 3: 实现共用切换按钮并重构商品卡片交互边界**

`CompareToggleButton.vue` 通过 store 判断状态：

```ts
function toggle() {
  if (compare.contains(props.product.id)) {
    compare.remove(props.product.id)
    return
  }
  const result = compare.add(props.product)
  if (!result.ok) {
    ElMessage.warning(result.reason === 'category_mismatch'
      ? '只能对比同一分类商品，请先清空当前对比'
      : '最多只能同时对比 4 件商品')
  }
}
```

将 `ProductCard` 根节点改为 `article.product-card`，商品内容放入单独的 `RouterLink.product-card__link`，对比按钮作为 link 的同级元素，避免按钮嵌套链接和事件冒泡。详情页在收藏操作附近传入已经加载的 `product`。

- [x] **Step 4: 编写并实现全局对比栏行为**

先新增失败测试或在组件测试中断言：一件商品后出现对比栏；一件时“开始对比”禁用；两件时路由到 `/compare?ids=1,2`；移除和清空更新 store。

`ProductCompareTray.vue` 的核心导航：

```ts
const canCompare = computed(() => compare.ids.length >= 2)
function openComparison() {
  if (!canCompare.value) return
  void router.push({ path: '/compare', query: { ids: compare.ids.join(',') } })
}
```

在 `StoreLayout.vue` 的 `RouterView` 后挂载 `<ProductCompareTray />`。对比页自身不重复显示对比栏，使用 `useRoute()` 在 `route.name === 'product-comparison'` 时隐藏。其他页面使用 `position: fixed`、安全区底部间距和移动端横向缩略列表，不改变 footer 数据流。

- [x] **Step 5: 运行入口、对比栏和现有商品页测试**

Run: `pnpm exec vitest run src/components/ProductCard.test.ts src/views/store/ProductDetailView.test.ts src/views/store/ProductListView.test.ts`（工作目录 `frontend`）

Expected: PASS。

Run: `pnpm typecheck`（工作目录 `frontend`）

Expected: exit 0。

- [x] **Step 6: 提交商品入口和对比栏**

```powershell
git add frontend/src/components/catalog/CompareToggleButton.vue frontend/src/components/catalog/ProductCompareTray.vue frontend/src/components/ProductCard.vue frontend/src/components/ProductCard.test.ts frontend/src/layouts/StoreLayout.vue frontend/src/views/store/ProductDetailView.vue frontend/src/views/store/ProductDetailView.test.ts docs/superpowers/plans/2026-08-24-product-comparison.md
git commit -m "feat: add product comparison entry points"
```

---

### Task 4: 基础商品对比页与分享链接

**Files:**
- Create: `frontend/src/views/store/ProductComparisonView.vue`
- Create: `frontend/src/views/store/ProductComparisonView.test.ts`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: `getProductComparison(ids)`、`useCompareStore()` 与 Task 1 的批量响应。
- Produces: 公开 `/compare` 页面、规范化 URL、参数行和“仅看差异”。

- [ ] **Step 1: 编写分享恢复和过期请求失败测试**

mock `route.query.ids = '2,bad,2,3,9,10,11'`，mock 批量接口返回商品 2、3 与失效 ID 9、10。断言只请求前四个去重合法 ID、最终 URL 和 store 只保留真实商品：

```ts
expect(catalogMocks.getProductComparison).toHaveBeenCalledWith([2, 3, 9, 10])
expect(routerMocks.replace).toHaveBeenLastCalledWith({
  path: '/compare',
  query: { ids: '2,3' },
})
expect(compare.ids).toEqual([2, 3])
expect(wrapper.text()).toContain('部分商品已失效，已从对比中移除')
```

再用两个 deferred Promise 验证旧组合晚返回时不能覆盖新组合。

- [ ] **Step 2: 编写参数并集与仅看差异失败测试**

使用两件商品字面量：共有“续航=40 小时”，不同“重量”和只有一方拥有“降噪”。默认断言三行都显示；点击“仅看差异”后共有续航行隐藏，缺失值显示“未提供”。

```ts
expect(wrapper.text()).toContain('续航')
await wrapper.get('[aria-label="仅看差异"]').setValue(true)
expect(wrapper.find('[data-parameter="续航"]').exists()).toBe(false)
expect(wrapper.get('[data-parameter="降噪"]').text()).toContain('未提供')
```

- [ ] **Step 3: 运行页面测试并确认路由/页面缺失**

Run: `pnpm exec vitest run src/views/store/ProductComparisonView.test.ts`（工作目录 `frontend`）

Expected: FAIL，页面模块或对比行为不存在。

- [ ] **Step 4: 实现 ID 规范化、请求时序和基础派生行**

页面只保留服务端数据与 UI 状态；参数行使用纯 `computed`：

```ts
interface ComparisonRow {
  key: string
  label: string
  values: string[]
  different: boolean
}

function formatParameter(value: unknown): string {
  if (value === null || value === undefined || value === '') return '未提供'
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean')
    return String(value)
  return JSON.stringify(value)
}

const parameterRows = computed<ComparisonRow[]>(() => {
  const keys = [...new Set(products.value.flatMap(product =>
    Object.keys(product.parameters || {}),
  ))]
  return keys.map((key) => {
    const values = products.value.map(product => formatParameter(product.parameters?.[key]))
    return { key, label: key, values, different: new Set(values).size > 1 }
  })
})

const skuAttributeRows = computed<ComparisonRow[]>(() => {
  const keys = [...new Set(products.value.flatMap(product =>
    product.skus.flatMap(sku => Object.keys(sku.attributes || {})),
  ))]
  return keys.map((key) => {
    const values = products.value.map((product) => {
      const variants = product.skus
        .map(sku => formatParameter(sku.attributes?.[key]))
        .filter(value => value !== '未提供')
      return [...new Set(variants)].join(' / ') || '未提供'
    })
    return { key: `sku:${key}`, label: key, values, different: new Set(values).size > 1 }
  })
})

const visibleRows = computed(() => {
  const rows = [...parameterRows.value, ...skuAttributeRows.value]
  return differencesOnly.value ? rows.filter(row => row.different) : rows
})
```

请求使用递增 `requestSequence`；只有最后一次请求能写 `products`、store 和 URL。少于两件不请求 API，显示返回商品列表的入口。固定事实行必须包含品牌、价格区间、评分、评价数、销量和总可售库存，随后拼接 `parameterRows` 与 `skuAttributeRows`。`visibleRows` 对两组规格行统一执行仅看差异过滤。

- [ ] **Step 5: 实现响应式对比表和公开路由**

在 router 商城 children 中添加：

```ts
{
  path: 'compare',
  name: 'product-comparison',
  component: () => import('../views/store/ProductComparisonView.vue'),
}
```

页面用语义化 table 呈现固定事实行与参数行。桌面端参数名单元格 `position: sticky; left: 0`，商品列 `min-width: 240px`；容器 `overflow-x: auto`。每列提供查看详情和移除操作。

移除操作立即同步三处状态，不等待重新请求：

```ts
async function removeProduct(productId: number) {
  products.value = products.value.filter(product => product.id !== productId)
  compare.remove(productId)
  await router.replace({
    path: '/compare',
    query: compare.ids.length ? { ids: compare.ids.join(',') } : {},
  })
}
```

- [ ] **Step 6: 运行目标测试、回归和构建**

Run: `pnpm exec vitest run src/views/store/ProductComparisonView.test.ts src/stores/compare.test.ts src/components/ProductCard.test.ts`（工作目录 `frontend`）

Expected: PASS。

Run: `pnpm build`（工作目录 `frontend`）

Expected: exit 0；允许已有包体积与演示图片运行时解析警告，不允许类型错误。

- [ ] **Step 7: 提交基础对比页**

```powershell
git add frontend/src/views/store/ProductComparisonView.vue frontend/src/views/store/ProductComparisonView.test.ts frontend/src/router/index.ts docs/superpowers/plans/2026-08-24-product-comparison.md
git commit -m "feat: add shareable product comparison page"
```

---

### Task 5: 后端快速 AI 对比服务

**Files:**
- Create: `backend/app/services/product_comparison_ai.py`
- Create: `tests/test_product_comparison_ai.py`
- Modify: `backend/app/schemas/ai.py`
- Modify: `backend/app/api/v1/routes/ai.py`

**Interfaces:**
- Consumes: `CatalogService.compare_products()` 与默认 `AiModelConfig`。
- Produces: `ProductComparisonRequest`、`ProductComparisonAiResult`。
- Produces: `ProductComparisonAiService.compare(payload) -> ProductComparisonAiResult`。
- Produces: 登录接口 `POST /api/v1/ai/product-comparison`。

- [ ] **Step 1: 编写结构化服务失败测试**

使用 `FakeComparisonGateway` 捕获 facts 和调用次数：

```python
class FakeComparisonGateway:
    def __init__(self, result: ProductComparisonAiResult) -> None:
        self.calls = 0
        self.facts: list[dict[str, Any]] = []
        self.result = result

    async def compare(self, facts: list[dict[str, Any]], preference: str | None):
        self.calls += 1
        self.facts = facts
        return self.result

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_ai_comparison_uses_server_facts_once() -> None:
    service = ProductComparisonAiService(session, gateway=fake_gateway)
    result = await service.compare(ProductComparisonRequest(product_ids=[2, 1]))

    assert fake_gateway.calls == 1
    assert [fact["product_id"] for fact in fake_gateway.facts] == [2, 1]
    assert "detail_markdown" not in fake_gateway.facts[0]
    assert result.recommended_product_id == 2
```

增加候选外 `recommended_product_id=999`、下架候选、跨分类和重复后不足两件的测试。

- [ ] **Step 2: 编写超时和非思考请求失败测试**

给 service 注入 `timeout_seconds=0.01` 和一个永不及时返回的 gateway，断言 `AI_COMPARISON_TIMEOUT`、504。给百炼 gateway 注入 fake OpenAI client，断言一次调用参数：

```python
assert create_mock.call_count == 1
kwargs = create_mock.call_args.kwargs
assert kwargs["extra_body"] == {"enable_thinking": False}
assert kwargs["response_format"] == {"type": "json_object"}
assert kwargs["max_tokens"] <= 800
assert kwargs["temperature"] == 0.2
```

- [ ] **Step 3: 运行测试并确认 AI 服务缺失**

Run: `uv run pytest tests/test_product_comparison_ai.py -q`

Expected: FAIL，提示 `product_comparison_ai` 或 AI DTO 不存在。

- [ ] **Step 4: 添加请求和响应 DTO**

在 `backend/app/schemas/ai.py` 添加：

```python
class ProductComparisonRequest(BaseModel):
    product_ids: list[int] = Field(min_length=2, max_length=16)
    preference: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def unique_products(self) -> "ProductComparisonRequest":
        self.product_ids = list(dict.fromkeys(self.product_ids))
        if len(self.product_ids) < 2:
            raise ValueError("至少需要两件不同商品")
        if len(self.product_ids) > 4:
            raise ValueError("最多只能对比四件商品")
        if self.preference is not None:
            self.preference = self.preference.strip() or None
        return self


class ProductComparisonAiItem(BaseModel):
    product_id: int
    strengths: list[str] = Field(max_length=5)
    weaknesses: list[str] = Field(max_length=5)
    suitable_for: list[str] = Field(max_length=5)


class ProductComparisonAiResult(BaseModel):
    recommended_product_id: int
    summary: str = Field(min_length=1, max_length=1000)
    items: list[ProductComparisonAiItem]
    considerations: list[str] = Field(max_length=8)
```

- [ ] **Step 5: 实现 gateway 和领域服务**

`ProductComparisonGateway` Protocol 只暴露 `compare(facts, preference)` 与 `close()`。`BailianProductComparisonGateway` 使用默认配置解密后的 key，通过一次 `chat.completions.create()` 返回 JSON 并执行 `ProductComparisonAiResult.model_validate_json(content)`。

`ProductComparisonAiService.compare()` 的顺序固定为：读取 Task 1 事实；要求所有请求 ID 均有效；压缩字段；在 `asyncio.timeout(self.timeout_seconds)` 中调用 gateway；校验推荐 ID 和每项 ID 属于候选；finally 关闭自建 gateway。超时映射为：

```python
raise AppError(
    "AI 对比分析超时，请稍后重试",
    code="AI_COMPARISON_TIMEOUT",
    status_code=504,
)
```

无默认启用配置或密钥时返回 `AI_MODEL_UNAVAILABLE`、503。非法模型 JSON 返回 `AI_INVALID_RESPONSE`、502。响应 DTO 不定义价格或库存字段。

- [ ] **Step 6: 注册登录保护路由**

```python
@router.post(
    "/product-comparison",
    response_model=ApiResponse[ProductComparisonAiResult],
)
async def compare_products_with_ai(
    payload: ProductComparisonRequest,
    session: DbSession,
    user: CurrentUser,
) -> ApiResponse[ProductComparisonAiResult]:
    return ApiResponse(
        message="AI 对比分析完成",
        data=await ProductComparisonAiService(session).compare(payload),
    )
```

`user` 必须保留为依赖，即使领域服务不读取 user ID，确保 FastAPI 在创建模型调用前完成登录校验。

- [ ] **Step 7: 运行 AI 测试和后端检查**

Run: `uv run pytest tests/test_product_comparison.py tests/test_product_comparison_ai.py -q`

Expected: PASS。

Run: `uv run ruff check backend/app/schemas/ai.py backend/app/services/product_comparison_ai.py backend/app/api/v1/routes/ai.py tests/test_product_comparison_ai.py`

Expected: exit 0。

Run: `uv run mypy backend/app/services/product_comparison_ai.py backend/app/api/v1/routes/ai.py`

Expected: exit 0。

- [ ] **Step 8: 提交快速 AI 后端**

```powershell
git add backend/app/schemas/ai.py backend/app/services/product_comparison_ai.py backend/app/api/v1/routes/ai.py tests/test_product_comparison_ai.py docs/superpowers/plans/2026-08-24-product-comparison.md
git commit -m "feat: add fast AI product comparison"
```

---

### Task 6: 前端按需 AI 对比面板

**Files:**
- Modify: `frontend/src/types/ai.ts`
- Modify: `frontend/src/api/ai.ts`
- Create: `frontend/src/components/catalog/ProductComparisonAiPanel.vue`
- Create: `frontend/src/components/catalog/ProductComparisonAiPanel.test.ts`
- Modify: `frontend/src/views/store/ProductComparisonView.vue`

**Interfaces:**
- Consumes: Task 5 的 `ProductComparisonAiResult`。
- Produces: `compareProductsWithAi(productIds: number[], preference?: string) -> Promise<ProductComparisonAiResult>`。
- Produces: `ProductComparisonAiPanel` props `{ products: ProductComparisonItem[] }`，组件从真实商品建立 ID 到名称的映射。

- [ ] **Step 1: 编写登录、展示模式和成功结果失败测试**

三条黑盒测试分别断言：

```ts
await wrapper.get('button').trigger('click')
expect(routerPush).toHaveBeenCalledWith({
  name: 'login',
  query: { redirect: '/compare?ids=2,3' },
})
expect(aiMocks.compareProductsWithAi).not.toHaveBeenCalled()
```

```ts
expect(wrapper.text()).toContain('完整部署并登录后可使用 AI 对比')
expect(wrapper.find('button').exists()).toBe(false)
```

```ts
await wrapper.get('textarea').setValue('办公室使用，重视续航')
await wrapper.get('button').trigger('click')
await flushPromises()
expect(aiMocks.compareProductsWithAi).toHaveBeenCalledWith(
  [2, 3],
  '办公室使用，重视续航',
)
expect(wrapper.text()).toContain('更推荐 EchoArc H1')
```

- [ ] **Step 2: 编写缓存、旧请求和超时恢复失败测试**

先把成功结果写入 `sessionStorage` 后重新 mount，断言不调用 API 且立即显示。用 deferred Promise 修改 `products` props，断言旧结果不覆盖新组合。mock API reject 后断言需求文本仍存在、基础面板未卸载且“重新分析”按钮可点击。

- [ ] **Step 3: 运行测试并确认组件缺失**

Run: `pnpm exec vitest run src/components/catalog/ProductComparisonAiPanel.test.ts`（工作目录 `frontend`）

Expected: FAIL，组件模块不存在。

- [ ] **Step 4: 添加 TypeScript 类型和 API**

```ts
export interface ProductComparisonAiItem {
  product_id: number
  strengths: string[]
  weaknesses: string[]
  suitable_for: string[]
}

export interface ProductComparisonAiResult {
  recommended_product_id: number
  summary: string
  items: ProductComparisonAiItem[]
  considerations: string[]
}

export async function compareProductsWithAi(productIds: number[], preference?: string) {
  return (await http.post('/ai/product-comparison', {
    product_ids: productIds,
    preference: preference?.trim() || null,
  }, { timeout: 20_000 })).data.data as ProductComparisonAiResult
}
```

- [ ] **Step 5: 实现会话缓存与非阻塞面板**

缓存键固定包含排序保持不变的 ID 和规范化需求：

```ts
const cacheKey = computed(() => [
  'ai-commerce-product-comparison-v1',
  props.products.map(product => product.id).join(','),
  preference.value.trim(),
].join(':'))
```

组件用 `computed(() => new Map(props.products.map(product => [product.id, product.name])))` 为逐商品优缺点显示真实名称。展示模式只显示说明；未登录时跳登录；已登录时设置局部 `loading` 并调用 API。请求使用序号校验 props 与需求未变化后才写结果。成功结果写入 `sessionStorage`；JSON 损坏时删除该键。catch 只设置局部错误，不清空输入或触碰父页面事实。

- [ ] **Step 6: 接入对比页并运行目标测试**

在基础表格之后添加：

```vue
<ProductComparisonAiPanel
  v-if="products.length >= 2"
  :products="products"
/>
```

Run: `pnpm exec vitest run src/components/catalog/ProductComparisonAiPanel.test.ts src/views/store/ProductComparisonView.test.ts`（工作目录 `frontend`）

Expected: PASS。

Run: `pnpm typecheck`（工作目录 `frontend`）

Expected: exit 0。

- [ ] **Step 7: 提交 AI 对比面板**

```powershell
git add frontend/src/types/ai.ts frontend/src/api/ai.ts frontend/src/components/catalog/ProductComparisonAiPanel.vue frontend/src/components/catalog/ProductComparisonAiPanel.test.ts frontend/src/views/store/ProductComparisonView.vue docs/superpowers/plans/2026-08-24-product-comparison.md
git commit -m "feat: add on-demand AI comparison panel"
```

---

### Task 7: README、完整回归、展示构建与恢复标记

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/plans/2026-08-24-product-comparison.md`

**Interfaces:**
- Consumes: Tasks 1–6 的完整功能。
- Produces: 用户文档、全部验证证据和完成状态。

- [ ] **Step 1: 更新 README**

在“当前进度”加入商品对比中心，并新增简短小节，明确：

```markdown
## 商品对比中心

- 商品列表和详情页可将最多 4 件同分类商品加入对比。
- 对比清单保存在当前浏览器，对比页链接可直接复制分享。
- 基础表格展示实时价格、库存、评分与规格，并支持仅看差异。
- 基础对比无需登录；“AI 帮我选”需要登录和可用的默认语言模型。
- AI 采用单次非思考请求，失败或超时不会影响基础表格。
```

在接口前缀补充批量目录和 AI 对比接口。

- [ ] **Step 2: 运行后端完整验证**

Run: `uv run ruff check backend tests`

Expected: exit 0。

Run: `uv run mypy backend`

Expected: exit 0。

Run: `uv run pytest -q`

Expected: 0 failed。

- [ ] **Step 3: 运行前端完整验证**

Run: `pnpm test:unit`（工作目录 `frontend`）

Expected: 0 failed。

Run: `pnpm build`（工作目录 `frontend`）

Expected: exit 0。

Run: `pnpm build:pages`（工作目录 `frontend`）

Expected: exit 0，并确认展示版对比使用本地目录；已有包体积警告允许保留。

- [ ] **Step 4: 浏览器验收核心路径**

启动本地前后端后验证：

```text
商品列表加入两件同分类商品
→ 底部对比栏出现
→ 打开 /compare?ids=...
→ 切换“仅看差异”
→ 复制链接并在新标签恢复
→ 未登录点击 AI 返回登录
→ 登录后回到原对比 URL
→ AI 成功或超时均保留基础表格
```

移动视口验证参数名列可见、商品列横向滚动且操作按钮可达。

- [ ] **Step 5: 检查性能与差异范围**

使用后端测试中的 SQL 查询计数证明批量事实读取固定为两次 SELECT；记录本地批量接口耗时并确认低于 500ms。然后运行：

Run: `git diff --check`

Expected: exit 0。

Run: `git status --short`

Expected: 只包含 README、当前计划复选框，以及明确属于本功能的文件；`.github/` 和根目录微信图片保持未跟踪且不暂存。

- [ ] **Step 6: 标记计划完成并提交文档**

将本计划所有复选框改为 `[x]`，并提交最后文档：

```powershell
git add README.md docs/superpowers/plans/2026-08-24-product-comparison.md
git commit -m "docs: document product comparison center"
```

- [ ] **Step 7: 推送并核对远端**

```powershell
git push origin main
git rev-parse HEAD
git ls-remote origin refs/heads/main
```

Expected: 本地 HEAD 与远端 `refs/heads/main` 哈希完全一致。
