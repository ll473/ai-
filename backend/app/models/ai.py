from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, IdMixin, TimestampMixin
from backend.app.models.enums import (
    AgentRunStatus,
    AgentStepType,
    ConversationRole,
    DocumentStatus,
    QuestionType,
    StepStatus,
)


class AiModelConfig(IdMixin, TimestampMixin, Base):
    __tablename__ = "ai_model_configs"

    name: Mapped[str] = mapped_column(String(100), unique=True)
    provider: Mapped[str] = mapped_column(String(50), index=True)
    base_url: Mapped[str | None] = mapped_column(String(500))
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text)
    chat_model: Mapped[str] = mapped_column(String(120))
    embedding_model: Mapped[str | None] = mapped_column(String(120))
    temperature: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.20"))
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class PromptTemplate(IdMixin, TimestampMixin, Base):
    __tablename__ = "prompt_templates"
    __table_args__ = (UniqueConstraint("code", "version"),)

    code: Mapped[str] = mapped_column(String(80), index=True)
    name: Mapped[str] = mapped_column(String(120))
    scene: Mapped[str] = mapped_column(String(60), index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    system_prompt: Mapped[str] = mapped_column(Text)
    user_prompt_template: Mapped[str | None] = mapped_column(Text)
    variables: Mapped[list[str] | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class KnowledgeDocument(IdMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_documents"

    title: Mapped[str] = mapped_column(String(255))
    source_type: Mapped[str] = mapped_column(String(40), index=True)
    source_id: Mapped[str | None] = mapped_column(String(64), index=True)
    product_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("products.id"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(64), index=True)
    status: Mapped[DocumentStatus] = mapped_column(
        String(20), default=DocumentStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text)


class KnowledgeChunk(IdMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (UniqueConstraint("document_id", "chunk_index"),)

    document_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("knowledge_documents.id"), index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("products.id"), index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int | None] = mapped_column(Integer)
    vector_point_id: Mapped[str | None] = mapped_column(String(100), unique=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class FunctionTool(IdMixin, TimestampMixin, Base):
    __tablename__ = "function_tools"

    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON)
    executor: Mapped[str] = mapped_column(
        String(255), comment="Allow-listed Python executor key, never arbitrary code"
    )
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=10)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class Conversation(IdMixin, TimestampMixin, Base):
    __tablename__ = "conversations"

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(255))
    scene: Mapped[str] = mapped_column(String(40), default="SHOPPING_GUIDE", index=True)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)


class ConversationMessage(IdMixin, TimestampMixin, Base):
    __tablename__ = "conversation_messages"

    conversation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("conversations.id"), index=True
    )
    role: Mapped[ConversationRole] = mapped_column(String(20), index=True)
    content: Mapped[str] = mapped_column(Text)
    question_type: Mapped[QuestionType | None] = mapped_column(String(30), index=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(100), index=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)


class AgentRun(IdMixin, TimestampMixin, Base):
    __tablename__ = "agent_runs"

    run_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    conversation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("conversations.id"), index=True
    )
    model_config_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_model_configs.id"), index=True
    )
    request_text: Mapped[str] = mapped_column(Text)
    status: Mapped[AgentRunStatus] = mapped_column(
        String(30), default=AgentRunStatus.RUNNING, index=True
    )
    max_steps: Mapped[int] = mapped_column(Integer, default=8)
    actual_steps: Mapped[int] = mapped_column(Integer, default=0)
    final_answer: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_duration_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AgentStep(IdMixin, TimestampMixin, Base):
    __tablename__ = "agent_steps"
    __table_args__ = (UniqueConstraint("agent_run_id", "step_no"),)

    agent_run_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("agent_runs.id"), index=True)
    step_no: Mapped[int] = mapped_column(Integer)
    step_type: Mapped[AgentStepType] = mapped_column(String(30), index=True)
    status: Mapped[StepStatus] = mapped_column(String(20), index=True)
    tool_name: Mapped[str | None] = mapped_column(String(80), index=True)
    model_reason_summary: Mapped[str | None] = mapped_column(
        Text, comment="Short explanation only; never store private chain-of-thought"
    )
    input_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    output_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ToolCallLog(IdMixin, TimestampMixin, Base):
    __tablename__ = "tool_call_logs"

    call_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    tool_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("function_tools.id"), index=True)
    agent_run_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_runs.id"), index=True
    )
    agent_step_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("agent_steps.id"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    arguments_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[StepStatus] = mapped_column(String(20), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class Recommendation(IdMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"

    agent_run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("agent_runs.id"), unique=True, index=True
    )
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), index=True)
    summary: Mapped[str] = mapped_column(Text)


class RecommendationItem(IdMixin, TimestampMixin, Base):
    __tablename__ = "recommendation_items"
    __table_args__ = (UniqueConstraint("recommendation_id", "product_id"),)

    recommendation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("recommendations.id"), index=True
    )
    product_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("products.id"), index=True)
    sku_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("product_skus.id"), index=True
    )
    reason: Mapped[str] = mapped_column(Text)
    price_snapshot: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    stock_snapshot: Mapped[int] = mapped_column(Integer)
    promotion_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    validation_passed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


class ReviewAnalysis(IdMixin, TimestampMixin, Base):
    __tablename__ = "review_analyses"

    product_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("products.id"), index=True
    )
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    positive_keywords: Mapped[list[str] | None] = mapped_column(JSON)
    negative_reasons: Mapped[list[str] | None] = mapped_column(JSON)
    after_sale_risks: Mapped[list[str] | None] = mapped_column(JSON)
    missing_information: Mapped[list[str] | None] = mapped_column(JSON)
    suggestions: Mapped[list[str] | None] = mapped_column(JSON)
    source_review_count: Mapped[int] = mapped_column(Integer, default=0)


class OperationReport(IdMixin, TimestampMixin, Base):
    __tablename__ = "operation_reports"

    title: Mapped[str] = mapped_column(String(255))
    report_type: Mapped[str] = mapped_column(String(50), index=True)
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    content_markdown: Mapped[str] = mapped_column(Text)
    metrics_snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    model_config_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("ai_model_configs.id"), index=True
    )
