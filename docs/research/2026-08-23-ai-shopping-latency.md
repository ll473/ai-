# AI 导购延迟研究与优化建议

日期：2026-08-23
范围：本项目的 AI 导购调用链；仅采用阿里云百炼、OpenAI Python SDK、FastAPI、HTTPX、SQLAlchemy 的官方文档或官方仓库作为外部依据。社区文章可用于发现线索，但不作为本文结论依据。

## 结论摘要

当前“慢”主要不是单一网络问题，而是四段延迟叠加：

1. 项目为 `qwen3.7-plus` 设置了 `reasoning={"effort": "low"}`。`low` 仍然开启轻度思考，并不是关闭思考；百炼官方针对 `qwen3.7-plus` 的排查说明称，该模型默认开启思考，推理 Token 常占输出的大部分，关闭思考的实测总耗时可降低 60%～75%。[百炼：深度思考模型的用法](https://help.aliyun.com/zh/model-studio/deep-thinking/)
2. 后端使用非流式 `responses.create()`，并在整次 Agent、工具调用和数据库写入全部结束后才返回普通 JSON；前端因此直到最后才看见结果。百炼 Responses API 和 OpenAI Python SDK 都支持 SSE 流式事件。[百炼：创建响应](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses)、[OpenAI Python SDK：Streaming responses](https://github.com/openai/openai-python#streaming-responses)
3. 一次导购最多 6 步，代码将单轮工具调用限制为 1；“模型决定工具 → 后端执行工具 → 模型读取结果”的每轮都是串行网络往返。Function Calling 官方流程本身就至少包含两次模型调用；更多串行工具会继续线性增加耗时。[百炼：Function Calling](https://help.aliyun.com/zh/model-studio/qwen-function-calling)
4. 每次 HTTP 导购请求都会新建并关闭 `AsyncOpenAI`，因此同一次 Agent 内可以复用连接，但不同用户请求之间无法复用 TCP/TLS 连接池。HTTPX 官方说明，长生命周期 Client 的连接池可避免重复握手并降低延迟。[HTTPX：Clients](https://github.com/encode/httpx/blob/master/docs/advanced/clients.md)

建议先实施低风险高收益项：将普通导购切为 `reasoning.effort="none"`，把客户端提升为应用级长生命周期资源，并增加端到端及逐轮延迟指标；随后增加 SSE 流式进度与最终文本；最后再评估减少模型轮次、批量数据库查询和 Flash 模型路由。

## 本地调用链证据

### 1. 模型调用仍在思考模式

`backend/app/services/shopping_agent.py:162-175`：

- 使用 `client.responses.create(...)`；
- 传入 `reasoning={"effort": "low"}`；
- 每轮传入全部可用工具；
- 传入 `max_tool_calls=1`。

百炼 Responses API 明确列出 `none`、`minimal`、`low`、`medium`、`high`、`xhigh`、`max` 七档，且说明降低档位可减少推理 Token 并加快响应；响应中只有 `effort` 非 `none` 或显式开启思考时才包含 reasoning 输出项。[百炼 Responses API 参数说明](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses)

因此，本项目当前的 `low` 是“低强度推理”，不是“无推理”。这是首要优化点。

### 2. 用户看到的是整次完成后的结果

`backend/app/api/v1/routes/ai.py:36-43` 直接等待 `ShoppingAgentService.run()` 完成后返回 `ApiResponse`。`frontend/src/api/ai.ts:71-80` 使用普通 POST 并把超时放宽到 120 秒；`frontend/src/views/store/ShoppingGuideView.vue:53-67` 在 Promise 完成前只展示等待状态。

这意味着即使模型在几秒后已经生成工具调用或文字，浏览器也收不到任何增量内容。FastAPI 官方提供 `StreamingResponse`，可把异步生成器产生的块逐块传给客户端；百炼 Responses API 的流式事件包含 `response.output_text.delta` 和 `response.completed`。[FastAPI：StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)、[百炼：Responses 流式输出](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses)

流式输出主要改善首屏和体感延迟，不一定减少完成整次任务的总耗时。工具依赖链仍需执行完毕。

### 3. 工具与模型往返是串行的

`backend/app/services/shopping_agent.py:141-300` 中，循环每轮先调用模型，再执行工具，再把 `function_call_output` 送入下一轮模型。默认 `max_steps=6`（`backend/app/schemas/ai.py:187-190`）。典型推荐可能经历：

1. 模型选择商品搜索；
2. 后端搜索并写日志；
3. 模型选择价格库存工具；
4. 后端查库并写日志；
5. 模型提交推荐；
6. 后端再次校验商品、SKU、库存与促销。

代码中的 `max_tool_calls=1` 是为了确定性而主动关闭单轮多工具。百炼官方支持 `parallel_tool_calls=true`，但只建议对互不依赖的工具并行；存在数据依赖时应继续串行。[百炼：并行工具调用](https://help.aliyun.com/zh/model-studio/qwen-function-calling#section-dyg-bzb-84y)

本项目的“搜索 → 基于搜索结果查库存 → 提交推荐”有明显依赖，不适合整条链并行。可并行或批量的是搜索后多个候选商品的只读价格/库存查询；更好的做法通常是一个后端批量查询，而不是让模型逐商品生成多个工具调用。

### 4. 客户端生命周期只覆盖单次请求

`backend/app/services/shopping_agent.py:127` 每次 `run()` 创建一个 `AsyncOpenAI`，`322-323` 在本次导购结束后关闭。因此同一个导购 Agent 内的多轮调用共享连接池，但下一个用户请求要重新建立连接。

OpenAI Python SDK 的异步客户端底层使用 HTTP 客户端；其官方 README 还给出可选 `aiohttp` 后端用于改善高并发性能。[OpenAI Python SDK：Async usage](https://github.com/openai/openai-python#async-usage) HTTPX 官方则明确指出 Client 会复用 TCP 连接，减少握手、CPU 和网络往返。[HTTPX：Why use a Client](https://github.com/encode/httpx/blob/master/docs/advanced/clients.md#why-use-a-client)

FastAPI 官方推荐通过 lifespan 初始化需跨请求共享且需要关闭的资源，并在应用关闭时清理。[FastAPI：Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)

### 5. 数据库工具路径还有次要放大项

`backend/app/services/tool_center.py:151` 在工具执行内部提交事务，而 Agent 循环在 `shopping_agent.py:264` 又提交一次。提交往返可能不大，但在每个工具步骤里都会累积。

`backend/app/services/product_price_stock.py:39-51` 对同一商品的每个 SKU 顺序调用一次 `best_promotion()`，是 N+1 查询形态。`tool_center.py:280-350` 的推荐校验也逐候选读取商品、SKU 和促销。这些是可测量、可批量化的后端延迟，但通常仍小于多轮远程模型推理。

## 官方资料给出的关键事实

### `qwen3.7-plus` 与思考模式

- `qwen3.7-plus` 是混合思考模型，默认开启思考。[百炼：深度思考](https://help.aliyun.com/zh/model-studio/deep-thinking/)
- 官方专项排查称，推理 Token 实测可占总输出 60% 以上，模型生成速度本身可能正常，慢主要来自生成更多 Token；关闭思考实测总耗时降低 60%～75%。[同一官方文档：qwen3.7-plus 调用慢排查](https://help.aliyun.com/zh/model-studio/deep-thinking/#section-wit-qlr-kl9)
- Responses API 中 `reasoning.effort="none"` 才是关闭；`low` 仍会产生 reasoning Token。可通过 `usage.output_tokens_details.reasoning_tokens` 验证。[百炼：Responses API 参数与 usage](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses)
- `qwen3.7-plus` 支持 Function Calling 和上下文缓存。[百炼：qwen3.7-plus 模型信息](https://help.aliyun.com/zh/model-studio/qwen3-7-plus)

### 专属业务空间域名

百炼建议北京和新加坡地域迁移到带 WorkspaceId 的专属域名，并称其可提供更好的性能和稳定性。[百炼：Responses API 地域地址](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses)

如果当前配置已经是正确业务空间的专属地址，就应保留；继续切换域名不再是主要优化手段。专属域名不能消除思考 Token 和多轮工具往返。

### Streaming

- 百炼 Responses API 设置 `stream=true` 后通过 SSE 实时返回，并以 `response.output_text.delta` 提供文本增量。[百炼：Responses 流式输出](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses)
- OpenAI Python SDK 的同步和异步客户端都支持 `responses.create(..., stream=True)`；异步版本使用 `async for` 消费事件。[OpenAI Python SDK：Streaming responses](https://github.com/openai/openai-python#streaming-responses)
- FastAPI 可用 `StreamingResponse` 传输异步迭代器的块。[FastAPI：Custom Response](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- 流必须完整消费或可靠关闭，以释放连接；OpenAI SDK 的流实现会在结束时关闭响应。[OpenAI Python SDK 流实现](https://github.com/openai/openai-python/blob/main/src/openai/_streaming.py)

### Session 缓存与多轮上下文

百炼 Responses API 可在客户端启用 `x-dashscope-session-cache: enable`，再配合 `previous_response_id` 使用 Session 缓存；命中情况可从 `usage.input_tokens_details.cached_tokens` 查看。缓存有 1024 Token 的最低触发门槛，且依赖精确前缀/系统提示匹配。[百炼：Responses Session 缓存](https://help.aliyun.com/zh/model-studio/qwen-api-via-openai-responses#section-dv5-n1g-vip)

当前 Agent 在单次 `run()` 内使用 `previous_response_id`，但新的用户 HTTP 请求会把它重新设为 `None`，并重新发送数据库中的历史消息。若持久化最近的 response id 或使用 Responses conversation，同时开启 Session 缓存，长对话可能降低输入处理延迟和成本。短对话或输入不足 1024 Token 时收益有限。

### 并行工具与数据库会话安全

百炼支持并行 Function Calling，但前提是工具互不依赖。[百炼：Function Calling 进阶用法](https://help.aliyun.com/zh/model-studio/qwen-function-calling)

如果后端真的用 `asyncio.gather()` 并发执行数据库工具，不能共享当前同一个 `AsyncSession`。SQLAlchemy 官方明确说明 `AsyncSession` 是可变、有状态对象，不可被多个 asyncio task 并发使用；并发任务应各自使用独立 `AsyncSession`。[SQLAlchemy：Session/AsyncSession 并发安全](https://docs.sqlalchemy.org/en/20/orm/session_basics.html#is-the-session-thread-safe-is-asyncsession-safe-to-share-in-concurrent-tasks)

## 分阶段优化方案

### P0：先做，风险最低

#### A. 普通导购关闭思考

将普通商品搜索、价格比较、库存问答和常规推荐改为：

```python
reasoning={"effort": "none"}
```

保留一个按意图升级的策略：只有复杂多约束、明显需要权衡解释的请求才使用 `minimal` 或 `low`。不要默认所有导购都用 `low`。

如果复杂请求必须保留思考，还可用官方 `thinking_budget` 限制推理 Token 上限，但应先确认当前模型与 `reasoning.effort` 的组合约束，避免同时传入不兼容参数。[百炼：限制思考长度](https://help.aliyun.com/zh/model-studio/deep-thinking)

预期：这是总耗时降幅最大的单项。必须用项目真实问题做 A/B，比较推荐正确率、工具选择成功率与 P95 延迟，不能只看文字质量。

#### B. 复用 `AsyncOpenAI`

在 FastAPI lifespan 中创建并保存按 `(base_url, API Key 标识)` 管理的长生命周期客户端，应用关闭时统一 `close()`。不要在每个 `run()` 末尾关闭共享客户端。

注意：模型配置和密钥支持后台热更新时，客户端池需要按配置版本或密钥指纹失效，日志只能记录不可逆指纹，不能记录密钥。

#### C. 建立延迟基线

当前已有 `AgentRun.total_duration_ms` 和工具 `duration_ms`，但仍缺少逐次模型调用指标。每轮至少记录：

- 模型请求序号、模型名、reasoning effort；
- 请求开始到首事件/首文本的 TTFT；
- 请求完成耗时；
- input/output/reasoning/cached tokens；
- 工具名与执行耗时；
- SDK `_request_id`（不记录 Authorization）；
- 是否发生重试、超时或 429/5xx。

OpenAI SDK 官方提供响应 `_request_id`，默认会对连接错误、408、409、429 和 5xx 自动重试两次；隐藏重试可能显著拉高尾延迟。[OpenAI Python SDK：Request IDs、Retries、Timeouts](https://github.com/openai/openai-python#request-ids)

同时可用百炼模型监控交叉核对调用总时长、首 Token 延迟、非首 Token 延迟、输入 Token 及限流情况；这样能区分模型排队/生成、网络和本地工具各自的耗时。[百炼：模型监控](https://help.aliyun.com/zh/model-studio/model-telemetry)

### P1：改善体感与交互

#### D. 新增 SSE 导购端点

保留现有 JSON 端点兼容旧前端，另增一个 SSE 端点。建议只向用户发送：

- `run.created`
- `status`（理解需求、搜索商品、校验价格库存）
- `answer.delta`
- `recommendation`
- `done` / `error`

不要把 `response.reasoning_text.delta` 或内部思维链展示给用户。工具调用前的模型输出通常只是结构化调用，不一定有可展示正文，因此服务端应主动发送简短状态事件；最后一轮再转发 `response.output_text.delta`。

#### E. 限制最终回答长度

当前模型配置默认允许 2048 输出 Token。导购最终答案通常只需 3 个候选及简短理由。可按阶段设置更紧的输出预算，并通过模板控制字数。官方明确说明输出 Token 越多，总耗时越长。[百炼：影响模型响应速度的因素](https://help.aliyun.com/zh/model-studio/rate-limit#section-9eg-lmr-xhd)

不要把预算压得过低，以免工具参数或最终结构被截断；需观察 `status=incomplete` 和完成原因。

### P2：减少总模型轮次

#### F. 将确定性的导购流程下沉到后端

对常见购买意图可用一次模型调用只做结构化意图提取（关键词、预算、用途、排序偏好），之后由后端一次批量查询商品、SKU、库存和促销，再用模板或一次短模型调用生成解释。这样可把当前最多 6 轮模型/工具循环压到 1～2 次模型调用。

安全边界保持不变：价格、库存、促销仍来自数据库，最终候选仍经后端校验。该方案通常比无限制并行工具更可控。

#### G. 批量化数据库查询

- 一次查询多个候选商品及首选可售 SKU；
- 一次查询候选相关促销，使用同一个时间快照；
- 工具日志和 AgentStep 尽量同一事务写入，减少重复 commit；
- 给真实 SQL 增加计数和耗时指标后再改，避免无证据微优化。

#### H. 有条件地并行独立只读工具

只有当一次请求中的多个工具互不依赖时才允许 `parallel_tool_calls`。执行层可选择：

- 不并发 ORM，而是把多个 ID 合并成一条批量 SQL；优先推荐；
- 若必须并发，每个任务使用独立 `AsyncSession`，之后汇总纯数据结果。

不能直接把当前 `self.session` 放进多个 `asyncio` 任务。

### P3：模型路由和缓存

#### I. 简单请求路由到 Flash

百炼将 Qwen Flash 定位为低延迟、适合快速响应的简单任务；`qwen3.7-flash` 支持 Function Calling、结构化输出和上下文缓存。[百炼产品说明](https://help.aliyun.com/zh/model-studio/what-is-model-studio/)、[qwen3.7-flash 模型信息](https://help.aliyun.com/zh/model-studio/qwen3-7-flash)

建议做双路由 A/B：

- 简单商品搜索、价格库存：`qwen3.7-flash` + `effort=none`；
- 多条件权衡、长对话：`qwen3.7-plus` + `none/minimal/low` 动态选择。

只有在工具选择准确率、合法参数率和推荐接受率达到门槛后才扩大 Flash 流量。

如果实测仅在高并发或高峰期变慢，且关闭思考、减少轮次后仍不满足 SLO，再评估预付费吞吐量（PTU）以获得更确定的推理资源；它不应作为低并发单请求慢的第一步。[百炼：模型部署与 PTU](https://help.aliyun.com/zh/model-studio/model-deployment-introduction)

#### J. 开启 Session 缓存

适用于稳定且较长的 system prompt、工具 schema 和长对话。需要：

- 保持 system prompt 字符串稳定；
- 客户端默认头启用 Session 缓存；
- 记录 `cached_tokens` 和 `cache_creation_input_tokens`；
- 对话跨请求时持久化服务端上下文引用，或采用 Responses conversation；
- 正确处理 response id 的有效期及失效回退。

不要对实时价格、库存和订单状态做长 TTL 结果缓存。商品文本搜索候选可考虑短 TTL，但提交推荐前仍须实时校验。

## 建议的验收基准

准备至少 30 条真实导购问题，分为简单查询、预算推荐、多约束推荐、追问四组；每个方案重复多次并错峰测试。记录：

| 指标 | 建议关注点 |
| --- | --- |
| 首状态时间 | HTTP 请求后多久出现“正在搜索”等事件 |
| 首文字时间 | 用户看到第一个最终答案字符的时间 |
| 完成时间 | 整次 Agent 完成时间 |
| 模型轮数 | 一次导购调用 Responses API 的次数 |
| 工具轮数 | 搜索、库存、提交推荐各调用次数 |
| 推理 Token 占比 | `reasoning_tokens / output_tokens` |
| 缓存命中 | `cached_tokens` 与创建缓存 Token |
| 正确率 | 工具参数合法率、推荐后端校验通过率 |
| 尾延迟 | P50、P95、P99；不能只看单次最快值 |

推荐实验矩阵：

1. 当前基线：Plus + `low` + 非流式；
2. Plus + `none` + 非流式；
3. Plus + `none` + SSE；
4. Plus + `none` + SSE + 共享客户端；
5. Flash + `none` + SSE；
6. 批量后端流程 + Plus/Flash 各一组。

先用第 2、3、4 组取得低风险收益，再决定是否做流程重构和模型路由。

## 不建议直接采用的做法

- 只把前端超时从 120 秒继续调大：只能减少超时报错，不会提速。
- 默认开启思考并仅改成流式：体感会改善，但总 Token 和总耗时仍高。
- 无条件打开并行工具：本项目工具有依赖关系，且当前共享 `AsyncSession` 不支持并发。
- 缓存价格、库存或订单状态作为最终答案：会破坏项目已有的实时校验约束。
- 在日志中打印完整请求头、SDK Client 配置或密钥：延迟诊断只需 request id、域名、模型、耗时和用量。
- 依据单次测速立刻换模型：模型负载会波动，应按问题分组比较 P50/P95 和正确率。

## 推荐实施顺序

1. 加逐轮观测字段，跑一轮当前基线。
2. 将普通导购的 `reasoning.effort` 从 `low` 改为 `none`，保留复杂问题升级策略。
3. 把 `AsyncOpenAI` 改为 lifespan 管理的共享客户端。
4. 增加 SSE 端点与前端增量状态/回答。
5. 压缩输出预算并审查 system prompt、工具 schema 的重复 Token。
6. 批量化候选商品、SKU、促销查询，减少 commit。
7. 用真实问题 A/B `qwen3.7-flash`。
8. 长对话达到缓存门槛后，再启用 Session 缓存并验证命中率。

这套顺序先解决已被官方明确确认的推理 Token 和连接/等待体验问题，再处理需要更多业务判断的 Agent 流程重构。
