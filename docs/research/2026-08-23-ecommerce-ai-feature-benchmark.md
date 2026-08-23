# AI 智能商城功能完善调研

日期：2026-08-23

## 结论

当前项目已经覆盖商品、购物车、订单、钱包、促销、评价、AI 导购、RAG 知识库和运营分析，继续增加普通 CRUD 页面收益有限。更值得借鉴成熟电商与 AI 平台的生产级能力：搜索发现、售后闭环、幂等支付、可观测、个性化推荐和质量评测。

建议先做“搜索发现 2.0”。它能直接复用当前 Qdrant、商品目录和 Vue 商品列表，用户感知强，风险也低。第二优先级是售后工单闭环；若项目计划接真实支付，则应把支付幂等与 Webhook 提升到同一优先级。

## 当前能力与主要缺口

已具备：

- FastAPI + Vue 3 前后端、商品/SKU/分类/品牌管理。
- 收藏、购物车、地址、订单、库存预占、钱包支付、履约和评价。
- 促销活动、AI 模型与 Prompt 管理、工具白名单及调用日志。
- AI 导购 Agent、商品搜索/价格库存/订单状态等工具。
- Qdrant 商品知识 RAG、引用、知识索引后台。
- AI 评价分析、运营增长报告和推荐结果实时校验。

主要缺口：

- 搜索以基础筛选为主，缺少联想词、拼写容错、同义词、分面筛选、混合召回和搜索效果指标。
- 现有“售后”偏规则与咨询，缺少用户真正发起退货、退款、换货以及后台处理的工单闭环。
- 钱包支付适合演示，但接入真实支付前还缺少请求幂等、回调验签、事件去重、失败重试与对账。
- AI 有运行日志，但缺少跨 HTTP、数据库、向量检索、模型和工具调用的统一链路，以及固定评测集。
- 尚未充分利用浏览、收藏、加购、订单和评价行为做个性化排序与推荐。
- 缺少通知中心、订单/售后时间线、漏斗指标和 A/B 实验。

## Top 8 建议功能

| 优先级 | 功能 | 适合当前项目的实现 | 可借鉴方案 |
| --- | --- | --- | --- |
| P0 | 搜索发现 2.0 | 搜索框联想、热词、历史词、错别字/拼音容错、同义词、分类/品牌/价格/库存/评分分面；关键词 BM25 与 Qdrant 语义向量混合召回，再按库存、销量、评分、促销做业务重排 | Shopify Predictive Search；Qdrant Hybrid Search / RRF / Formula Query |
| P0 | 真实售后工单 | 新增 ReturnRequest、ReturnItem、Refund、Exchange；支持申请、审核、寄回、收货质检、退款/拒绝状态机，区分可重新入库与损坏数量 | Medusa Order Return / Exchange；Saleor Returns |
| P0（真实支付时） | 支付可靠性 | 下单、支付、退款使用 Idempotency-Key；支付回调验签，按第三方事件 ID 去重，先快速返回 2xx，再异步处理和重试；增加对账任务 | Stripe Idempotent Requests / Webhooks |
| P0 | 全链路可观测 | 为请求、SQL、外部 HTTP、Qdrant、LLM、工具调用建立 Trace；统计 p50/p95、错误率、Token、成本、超时和降级率 | OpenTelemetry Python；Langfuse Observability |
| P1 | 个性化推荐 | 用浏览、收藏、加购、购买、评分事件生成“猜你喜欢、相似商品、搭配购买、继续浏览、再次购买”；先做规则和共现推荐，再升级模型排序 | Shopify Product Recommendations；Saleor 可组合架构 |
| P1 | AI 回答评测与反馈 | 从历史失败会话建立固定测试集；检查商品是否在售、价格库存是否来自工具、是否答非所问、是否出现 Markdown 残留；增加赞/踩和原因反馈，Prompt/模型变更前自动回归 | Langfuse Evaluations / Datasets |
| P1 | 通知与订单时间线 | 站内通知中心；支付、发货、签收、退款进度、库存恢复等事件统一写 Outbox，再异步发送；用户页显示完整状态时间线 | Stripe 事件驱动思路；Medusa 订单/退货工作流 |
| P1 | 漏斗分析与实验 | 记录搜索曝光、点击、商品浏览、加购、结算、支付；重点看无结果率、搜索 CTR、AI 推荐加购率/成交率；用功能开关做小流量 A/B | Shopify 搜索发现指标思路；OpenTelemetry Metrics |

## 搜索发现 2.0 的推荐落地方式

1. 建立搜索事件表：query、user_id/session_id、filters、result_count、clicked_product_id、add_to_cart、ordered_at。
2. 增加 `/search/suggestions`：返回商品名、分类、品牌、历史词和热词，限制 50–100 ms 内完成。
3. 为商品建立两路索引：结构化关键词/分面索引与 Qdrant 语义向量；使用 RRF 融合结果。
4. 在融合结果上叠加业务分：在售与有库存优先，其次评分、销量、促销和新鲜度；不要让销量完全盖过语义相关性。
5. 对“父母礼物”等宽泛需求，返回“相关性一般的备选推荐”，并明确匹配理由，而不是直接拒答或随机硬凑。
6. 后台增加无结果词、低点击词和高转化词榜单，用真实数据维护同义词与热词。

## 三阶段路线图

### 第一阶段：用户可感知的闭环

- 搜索联想、分面筛选、混合召回、无结果词统计。
- 退货/退款工单与后台处理页。
- 基础 OpenTelemetry Trace 和核心业务指标。
- 如果准备接真实支付，同时完成幂等键与 Webhook Inbox。

### 第二阶段：增长与质量

- 个性化推荐第一版：相似、搭配、继续浏览、再次购买。
- AI 固定评测集、赞/踩反馈、回答格式清洗和发布前回归。
- 站内通知、订单与售后时间线。
- 搜索与 AI 导购转化漏斗。

### 第三阶段：规模化能力

- 多仓库存、拆单/部分发货、物流轨迹。
- 优惠券、会员等级、积分与人群定向促销。
- 内容 CMS、SEO/结构化数据、PWA。
- 多渠道、多币种、税费和运费试算；仅在确有国际化需求时实施。

## 不建议现在照搬的能力

- 不急于引入 Elasticsearch/OpenSearch：当前已有 Qdrant，先用轻量关键词检索 + Qdrant 混合搜索验证业务效果。
- 不急于训练复杂推荐模型：事件数据量不足时，规则、共现和内容相似度更稳定，也更容易解释。
- 不急于做微服务拆分：现有模块化单体更适合当前体量，先补幂等、事件 Outbox、Trace 和领域状态机。
- 不直接引入完整大型电商框架替换当前系统：参考其领域模型与工作流即可，否则会稀释本项目已有 AI 特色。

## 官方参考资料

- [Shopify Predictive Search Storefront API](https://shopify.dev/docs/api/storefront/2026-01/queries/predictiveSearch)
- [Shopify 店面搜索：联想、拼写容错、筛选与推荐](https://help.shopify.com/en/manual/online-store/storefront-search)
- [Shopify 商品推荐](https://help.shopify.com/en/manual/online-store/storefront-search/search-and-discovery-recommendations)
- [Qdrant Hybrid Search with Reranking](https://qdrant.tech/documentation/advanced-tutorials/reranking-hybrid-search/)
- [Qdrant Hybrid and Multi-stage Queries](https://qdrant.tech/documentation/search/hybrid-queries/)
- [Qdrant Production Checklist](https://qdrant.tech/documentation/production-checklist/)
- [Medusa Order Return Module](https://docs.medusajs.com/resources/commerce-modules/order/return)
- [Medusa Exchanges](https://docs.medusajs.com/user-guide/orders/exchanges)
- [Saleor Documentation](https://docs.saleor.io/)
- [Stripe Idempotent Requests](https://docs.stripe.com/api/idempotent_requests)
- [Stripe Webhooks](https://docs.stripe.com/webhooks)
- [OpenTelemetry Python Instrumentation](https://opentelemetry.io/docs/languages/python/instrumentation/)
- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Observability](https://langfuse.com/docs/observability/overview)

## 建议的下一项实施任务

优先实现“搜索发现 2.0 第一阶段”：搜索事件表、搜索联想、分面筛选、Qdrant 混合召回和无结果词后台统计。它对现有交易逻辑侵入较小，同时能改善普通商城搜索和 AI 导购商品召回，后续个性化推荐也可以复用同一套行为数据。
