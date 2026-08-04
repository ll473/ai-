# AI 智能商城架构说明

## 核心原则

1. 商城交易数据是唯一事实来源。价格、库存、优惠、钱包和订单状态不得由模型生成。
2. AI 只负责理解需求、选择工具、综合非确定性信息以及生成可解释理由。
3. 每次 Agent 执行都保存 `agent_runs`，每次模型决策、工具调用和校验都保存 `agent_steps`。
4. 推荐落库前重新查询 SKU 价格、可售库存和优惠，模型提交的数值不直接入库。
5. 不保存模型的私有思维链，只保存可展示的决策摘要、工具入参、工具结果、状态和耗时。
6. 评价分析只读取可见评价；结构化模型输出必须通过 Schema 校验后才能保存。
7. 运营报告先固化数据库统计快照，再将快照交给模型撰写，模型不能回写或修改业务指标。

前端实现还必须遵守 [frontend-design-constraints.md](frontend-design-constraints.md)，以 Taste Skill 和 Impeccable 作为设计与验收依据。

## 模块边界

- `models/user.py`：用户、地址、钱包和钱包流水。
- `models/catalog.py`：分类、品牌、商品、SKU、库存和收藏。
- `models/trade.py`：购物车、订单快照、支付、评价和售后规则。
- `models/ai.py`：模型、Prompt、知识库、工具、对话、Agent 轨迹、推荐和运营分析。
- `repositories/`：只负责数据库访问。
- `services/`：事务、业务规则和跨仓储编排。
- `agents/`：模型决策循环与工具注册，不直接绕过 service 访问数据库。
- `api/`：请求校验、身份鉴权和响应转换。

## Agent 运行边界

Agent 的工具执行器必须来自代码中的允许列表。数据库中的 `function_tools.executor` 只能引用允许列表中的键，不能保存并执行任意 Python 代码。

当前已实现工具：

- `search_products`
- `get_product_price_stock`
- `get_my_order_status`
- `get_user_summary`
- `submit_recommendation`

`submit_recommendation` 只接受商品/SKU ID 与推荐理由。服务层负责二次校验并写入真实快照。

## 问答路由

- `PRODUCT_KNOWLEDGE`：知识切片向量检索后由模型组织答案。
- `PRICE_STOCK`：调用真实商品服务，直接组织确定性答案。
- `ORDER_STATUS`：校验订单归属后调用订单服务，直接组织答案。
- `AFTER_SALE`：匹配售后规则表，直接组织答案。

## 运营分析边界

- 成交订单仅统计 `PAID`、`SHIPPED`、`COMPLETED` 状态，收入取订单真实 `paid_amount`。
- 评价总量、平均分与正负向数量只统计管理员设为可见的评价。
- 导购任务、成功任务、推荐单与推荐商品数直接从 Agent Run 和推荐表聚合。
- 评价分析默认最多向模型提供周期内最近 200 条可见评价，避免无界上下文。
- `REVIEW_ANALYSIS` 使用 `qwen3.7-plus` JSON Object 模式，输出通过 Pydantic 校验。
- `OPERATIONS_REPORT` 只接收序列化后的指标快照与最近评价分析，最终 Markdown 与快照一同落库。
