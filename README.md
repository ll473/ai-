# AI 智能商城

Python + Vue 的前后端分离商城，在完整交易闭环之上提供 RAG、Function Calling 和可追踪的自主导购 Agent。

## 当前进度

当前已经完成后端基础、商品域与用户交易闭环第一版：

- FastAPI 应用、CORS、统一响应和异常处理。
- SQLAlchemy 2 异步 MySQL 会话。
- 用户注册、JWT 登录和当前用户接口。
- 商城、钱包、订单、知识库、工具中心和 Agent Run/Step 基础数据模型。
- 分类、品牌、商品、SKU、真实价格区间和商品图片上传接口。
- Alembic 配置、本地建表脚本和基础测试。
- Vue 3 商城首页、商品列表、商品详情、登录页和管理端商品维护页面。
- 用户收藏、个人中心、AI 导购历史与商品详情收藏状态。
- 消费者导购页只展示购买需求、推荐理由、实时价格库存和加购入口；运行步骤与工具日志仅在管理端查看。
- 购物车数量与选中状态、收货地址管理、订单价格快照与库存预占。
- 站内钱包充值、余额支付、支付流水、取消订单与库存释放。
- Vue 3 购物车、结算、订单、钱包和收货地址页面。
- 管理员订单发货与完成、用户确认收货和已购商品评价。
- 商品详情真实评价展示、评分重算和后台评价显示状态审核。
- AI 模型配置、Prompt 模板、Function Tool 白名单中心与调用日志。
- 基于阿里云百炼 OpenAI 兼容 Responses API 的自主工具调用循环和 Agent Run/Step 时间线。
- 内置商品搜索、价格库存、用户订单状态、消费概况和提交推荐五个白名单工具。
- 商品知识资料同步、确定性切片、`qwen3.7-text-embedding` 向量化与 Qdrant 余弦检索。
- 商品详情 RAG 问答、资料引用，以及后台知识文档与索引状态管理。
- 推荐候选商品/SKU 二次校验、真实价格库存快照、幂等落库与导购结果一键加购。
- AI 评价分析：只读取周期内前台可见的真实评价，结构化输出好评关键词、差评原因、售后风险、详情缺失与优化建议。
- AI 运营增长报告：后端聚合成交、评价、导购、推荐与商品排行并固化指标快照，Qwen 生成 Markdown 报告供后台预览和历史复盘。

## 环境要求

- Python 3.12
- MySQL 8.x（推荐）
- Node.js 18+
- Qdrant 1.x

## 本地启动

```powershell
uv venv --python 3.12
uv sync --extra dev --locked
Copy-Item .env.example .env
```

## 公开部署

项目已经提供 `Dockerfile` 与 `render.yaml`。将仓库公开到 GitHub 后，可通过下面的按钮创建完整的商城网页、FastAPI 后端和 PostgreSQL 数据库：

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ll473/ai-)

部署会自动完成以下工作：

- 构建 Vue 商城页面并由 FastAPI 在同一个网址提供访问；
- 创建数据库表并写入演示商品；
- 生成独立的登录密钥；
- 开放注册、登录、商品浏览、收藏、购物车和订单等完整功能。

如需启用 AI 导购，请在部署平台中补充 `AI_API_KEY`；如需启用知识库向量检索，还需要填写 `QDRANT_URL` 和 `QDRANT_API_KEY`。

先在 MySQL 创建数据库：

```sql
CREATE DATABASE ai_commerce CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

修改 `.env` 中的 `DATABASE_URL`，然后初始化本地表并创建管理员：

```powershell
uv run python -m backend.scripts.init_db
uv run python -m backend.scripts.create_admin admin
```

启动后端：

```powershell
uv run python main.py
```

启动前端：

```powershell
cd frontend
pnpm install
pnpm dev
```

- OpenAPI：http://127.0.0.1:8001/docs
- 健康检查：http://127.0.0.1:8001/health

## 接口前缀

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/health`
- `GET /api/v1/catalog/categories`
- `GET /api/v1/catalog/brands`
- `GET /api/v1/catalog/products`
- `GET /api/v1/catalog/products/{product_id}`
- `/api/v1/admin/catalog/*` 管理端分类、品牌、商品、SKU 与图片接口
- `/api/v1/cart/*` 用户购物车接口
- `/api/v1/addresses/*` 用户收货地址接口
- `/api/v1/wallet/*` 钱包与余额流水接口
- `/api/v1/orders/*` 下单、余额支付和取消订单接口
- `POST /api/v1/reviews` 已购商品评价接口
- `GET /api/v1/catalog/products/{product_id}/reviews` 商品公开评价接口
- `/api/v1/admin/orders/*` 管理端订单履约接口
- `/api/v1/admin/reviews/*` 管理端评价审核接口
- `/api/v1/admin/ai/*` 模型、Prompt、工具、日志和 Agent Run 管理接口
- `/api/v1/admin/knowledge/*` 知识文档、商品资料同步与向量索引接口
- `/api/v1/admin/operations/*` 运营指标、评价分析与增长报告接口
- `POST /api/v1/ai/shopping-guide` AI 自主导购入口
- `POST /api/v1/ai/product-qa` 商品知识库 RAG 问答入口
- `GET /api/v1/ai/runs` 当前用户的导购历史
- `/api/v1/favorites/*` 用户商品收藏

## AI 导购初始化

1. 使用管理员账号进入“AI 配置中心”。
2. 创建阿里云百炼模型配置：语言模型 `qwen3.7-plus`、向量模型 `qwen3.7-text-embedding`，并保存 API Key；密钥会使用项目 `SECRET_KEY` 派生密钥加密后落库。
3. 将模型配置设为默认并保持启用。
4. 在 Function Tools 页点击“初始化内置工具”。
5. 可选：创建 `SHOPPING_GUIDE` 场景 Prompt；未创建时使用后端最小安全 Prompt。

模型给出具体商品推荐时会先调用 `submit_recommendation`。模型只提交商品/SKU ID 与理由，后端重新校验商品状态、SKU 归属、可售库存和真实价格；校验后的推荐卡片可以直接加入购物车。

## 商品知识库初始化

1. 启动 Qdrant，并确认 `.env` 中的 `QDRANT_URL` 可访问。
2. 在“AI 配置中心”完成百炼模型配置，Base URL 默认使用北京公共 OpenAI 兼容地址。
3. 进入“商品知识库”，选择商品同步详情，或新增手工资料。
4. 点击“执行索引”；状态变为“可检索”后，登录用户可在商品详情页提问。

向量默认使用 1024 维。更换向量模型或维度时，应使用新的 `QDRANT_COLLECTION`，避免同一集合维度冲突。

没有 API Key 时不会发起模型请求，商品、库存、订单等工具仍可独立测试。

## AI 运营分析

1. 先在“AI 配置中心”启用默认百炼配置，语言模型保持 `qwen3.7-plus`。
2. 可选创建 `REVIEW_ANALYSIS` 与 `OPERATIONS_REPORT` 场景 Prompt；未配置时使用后端安全默认模板。
3. 进入“AI 运营分析”，选择统计周期和可选商品后生成评价洞察。
4. 点击“生成报告”可基于当前真实指标快照生成 Markdown 增长报告。

评价分析使用百炼结构化 JSON 输出，并经 Pydantic 严格校验后才会落库。运营指标、收入与商品排行均由数据库聚合，模型无法覆盖历史指标快照。

架构约束见 [docs/architecture.md](docs/architecture.md)。
