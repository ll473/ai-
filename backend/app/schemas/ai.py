from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Self
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.core.config import get_settings
from backend.app.models.enums import (
    AgentRunStatus,
    AgentStepType,
    ConversationRole,
    DocumentStatus,
    QuestionType,
    StepStatus,
)

ExecutorKey = Literal[
    "catalog.search_products",
    "catalog.get_product_price_stock",
    "orders.get_user_order_status",
    "profile.get_user_summary",
    "recommendations.submit",
]


class ModelConfigBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider: str = Field(default="ALIBABA_BAILIAN", min_length=1, max_length=50)
    base_url: str | None = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1", max_length=500
    )
    chat_model: str = Field(default="qwen3.7-plus", min_length=1, max_length=120)
    embedding_model: str | None = Field(default="qwen3.7-text-embedding", max_length=120)
    temperature: Decimal = Field(default=Decimal("0.20"), ge=0, le=2)
    max_tokens: int | None = Field(default=2048, ge=128, le=128000)
    enabled: bool = True
    is_default: bool = False

    @model_validator(mode="after")
    def validate_base_url(self) -> Self:
        _validate_ai_base_url(self.base_url)
        return self


class ModelConfigCreate(ModelConfigBase):
    api_key: str | None = Field(default=None, min_length=8, max_length=500)


class ModelConfigUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = Field(default=None, min_length=1, max_length=50)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, min_length=8, max_length=500)
    chat_model: str | None = Field(default=None, min_length=1, max_length=120)
    embedding_model: str | None = Field(default=None, max_length=120)
    temperature: Decimal | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=128, le=128000)
    enabled: bool | None = None
    is_default: bool | None = None

    @model_validator(mode="after")
    def validate_base_url(self) -> Self:
        _validate_ai_base_url(self.base_url)
        return self


def _validate_ai_base_url(value: str | None) -> None:
    if value is None:
        return
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not host:
        raise ValueError("AI base URL 必须使用 HTTPS")
    allowed = get_settings().ai_allowed_host_list
    if host not in allowed and not any(host.endswith(f".{item}") for item in allowed):
        raise ValueError("AI base URL 不在可信服务商列表中")


class ModelConfigPublic(ModelConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    has_api_key: bool
    created_at: datetime
    updated_at: datetime


class PromptTemplateBase(BaseModel):
    code: str = Field(min_length=1, max_length=80, pattern=r"^[A-Z0-9_]+$")
    name: str = Field(min_length=1, max_length=120)
    scene: str = Field(min_length=1, max_length=60)
    version: int = Field(default=1, ge=1)
    system_prompt: str = Field(min_length=1, max_length=20000)
    user_prompt_template: str | None = Field(default=None, max_length=10000)
    variables: list[str] | None = None
    enabled: bool = True


class PromptTemplateCreate(PromptTemplateBase):
    pass


class PromptTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    scene: str | None = Field(default=None, min_length=1, max_length=60)
    system_prompt: str | None = Field(default=None, min_length=1, max_length=20000)
    user_prompt_template: str | None = Field(default=None, max_length=10000)
    variables: list[str] | None = None
    enabled: bool | None = None


class PromptTemplatePublic(PromptTemplateBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class FunctionToolBase(BaseModel):
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z][a-z0-9_]*$")
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    input_schema: dict[str, Any]
    executor: ExecutorKey
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    enabled: bool = True

    @model_validator(mode="after")
    def validate_json_schema(self) -> Self:
        if self.input_schema.get("type") != "object":
            raise ValueError("input_schema 顶层 type 必须为 object")
        if not isinstance(self.input_schema.get("properties", {}), dict):
            raise ValueError("input_schema.properties 必须为对象")
        return self


class FunctionToolCreate(FunctionToolBase):
    pass


class FunctionToolUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    input_schema: dict[str, Any] | None = None
    executor: ExecutorKey | None = None
    timeout_seconds: int | None = Field(default=None, ge=1, le=60)
    enabled: bool | None = None


class FunctionToolPublic(FunctionToolBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class ToolExecuteRequest(BaseModel):
    arguments: dict[str, Any]


class ToolExecutionPublic(BaseModel):
    call_no: str
    tool_name: str
    status: StepStatus
    result: dict[str, Any] | None
    error_message: str | None
    duration_ms: int


class ToolCallLogPublic(BaseModel):
    id: int
    call_no: str
    tool_id: int
    tool_name: str
    user_id: int | None
    arguments_json: dict[str, Any]
    result_json: dict[str, Any] | None
    status: StepStatus
    error_message: str | None
    duration_ms: int | None
    created_at: datetime


class ShoppingGuideRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    max_steps: int = Field(default=6, ge=1, le=10)
    conversation_id: int | None = Field(default=None, ge=1)


class ProductComparisonRequest(BaseModel):
    product_ids: list[int] = Field(min_length=2, max_length=16)
    preference: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def unique_products(self) -> Self:
        self.product_ids = list(dict.fromkeys(self.product_ids))
        if len(self.product_ids) < 2:
            raise ValueError("至少需要两件不同商品")
        if len(self.product_ids) > 4:
            raise ValueError("最多只能对比四件商品")
        if self.preference is not None:
            self.preference = self.preference.strip() or None
        return self


class ProductComparisonAiItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    strengths: list[str] = Field(max_length=5)
    weaknesses: list[str] = Field(max_length=5)
    suitable_for: list[str] = Field(max_length=5)


class ProductComparisonAiResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recommended_product_id: int
    summary: str = Field(min_length=1, max_length=1000)
    items: list[ProductComparisonAiItem]
    considerations: list[str] = Field(max_length=8)


class RecommendationItemPublic(BaseModel):
    product_id: int
    sku_id: int | None
    product_name: str
    sku_name: str | None
    main_image_url: str | None
    reason: str
    price_snapshot: Decimal
    stock_snapshot: int
    validation_passed: bool


class RecommendationPublic(BaseModel):
    id: int
    summary: str
    items: list[RecommendationItemPublic]


class AgentStepPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    step_no: int
    step_type: AgentStepType
    status: StepStatus
    tool_name: str | None
    input_json: dict[str, Any] | None
    output_json: dict[str, Any] | None
    error_message: str | None
    duration_ms: int | None
    started_at: datetime
    finished_at: datetime | None


class AgentRunPublic(BaseModel):
    id: int
    run_no: str
    conversation_id: int | None
    status: AgentRunStatus
    request_text: str
    final_answer: str | None
    error_message: str | None
    actual_steps: int
    max_steps: int
    total_duration_ms: int | None
    started_at: datetime
    finished_at: datetime | None
    recommendation: RecommendationPublic | None = None


class AgentRunAdminPublic(AgentRunPublic):
    steps: list[AgentStepPublic]


class KnowledgeDocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    source_type: str = Field(default="MANUAL", min_length=1, max_length=40)
    source_id: str | None = Field(default=None, max_length=64)
    product_id: int | None = Field(default=None, ge=1)
    content: str = Field(min_length=2, max_length=100000)


class KnowledgeDocumentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    source_type: str | None = Field(default=None, min_length=1, max_length=40)
    source_id: str | None = Field(default=None, max_length=64)
    product_id: int | None = Field(default=None, ge=1)
    content: str | None = Field(default=None, min_length=2, max_length=100000)


class KnowledgeDocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    source_type: str
    source_id: str | None
    product_id: int | None
    content: str
    checksum: str | None
    status: DocumentStatus
    error_message: str | None
    chunk_count: int = 0
    created_at: datetime
    updated_at: datetime


class KnowledgeChunkPublic(BaseModel):
    id: int
    document_id: int
    document_title: str
    product_id: int | None
    chunk_index: int
    content: str
    token_count: int | None
    vector_point_id: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime


class ProductKnowledgeSyncRequest(BaseModel):
    product_id: int = Field(ge=1)


class ProductQuestionRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    question_type: QuestionType = QuestionType.PRODUCT_KNOWLEDGE
    product_id: int | None = Field(default=None, ge=1)
    order_no: str | None = Field(default=None, min_length=1, max_length=64)
    conversation_id: int | None = Field(default=None, ge=1)
    top_k: int = Field(default=5, ge=1, le=8)


class KnowledgeCitation(BaseModel):
    document_id: int
    document_title: str
    chunk_index: int
    excerpt: str
    score: float


class ProductQuestionResponse(BaseModel):
    answer: str
    question_type: QuestionType = QuestionType.PRODUCT_KNOWLEDGE
    conversation_id: int | None = None
    citations: list[KnowledgeCitation]


class ConversationMessagePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: ConversationRole
    content: str
    question_type: QuestionType | None
    metadata_json: dict[str, Any] | None
    created_at: datetime


class ConversationPublic(BaseModel):
    id: int
    title: str | None
    scene: str
    last_message_at: datetime | None
    message_count: int
    created_at: datetime


class ConversationDetail(ConversationPublic):
    messages: list[ConversationMessagePublic]


class ReviewAnalysisGenerateRequest(BaseModel):
    product_id: int | None = Field(default=None, ge=1)
    days: int = Field(default=30, ge=1, le=365)


class ReviewAnalysisResult(BaseModel):
    positive_keywords: list[str] = Field(default_factory=list, max_length=10)
    negative_reasons: list[str] = Field(default_factory=list, max_length=10)
    after_sale_risks: list[str] = Field(default_factory=list, max_length=10)
    missing_information: list[str] = Field(default_factory=list, max_length=10)
    suggestions: list[str] = Field(default_factory=list, max_length=10)


class ReviewAnalysisPublic(ReviewAnalysisResult):
    id: int
    product_id: int | None
    product_name: str | None
    period_start: datetime | None
    period_end: datetime | None
    source_review_count: int
    created_at: datetime


class OperationReportGenerateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=255)
    days: int = Field(default=30, ge=1, le=365)


class TopProductMetric(BaseModel):
    product_id: int
    product_name: str
    order_count: int
    quantity: int
    revenue: Decimal


class FrequentlyAskedQuestion(BaseModel):
    question: str
    count: int


class OperationsDashboardPublic(BaseModel):
    period_start: datetime
    period_end: datetime
    orders_total: int
    paid_orders: int
    revenue: Decimal
    reviews_total: int
    average_rating: float
    positive_reviews: int
    negative_reviews: int
    agent_runs: int
    successful_agent_runs: int
    recommendations: int
    recommendation_items: int
    product_views: int = 0
    unique_viewers: int = 0
    conversion_rate: float = 0
    questions_total: int = 0
    frequent_questions: list[FrequentlyAskedQuestion] = Field(default_factory=list)
    top_products: list[TopProductMetric]


class OperationReportPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    report_type: str
    period_start: datetime | None
    period_end: datetime | None
    content_markdown: str
    metrics_snapshot: dict[str, Any] | None
    model_config_id: int | None
    created_at: datetime
