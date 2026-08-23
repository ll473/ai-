from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    USER = "USER"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ProductStatus(StrEnum):
    DRAFT = "DRAFT"
    ON_SALE = "ON_SALE"
    OFF_SALE = "OFF_SALE"


class PromotionType(StrEnum):
    PERCENT = "PERCENT"
    FIXED = "FIXED"


class OrderStatus(StrEnum):
    PENDING_PAYMENT = "PENDING_PAYMENT"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class WalletTransactionType(StrEnum):
    RECHARGE = "RECHARGE"
    PAYMENT = "PAYMENT"
    REFUND = "REFUND"
    ADJUSTMENT = "ADJUSTMENT"


class DocumentStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    READY = "READY"
    FAILED = "FAILED"


class AgentRunStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    MAX_STEPS_REACHED = "MAX_STEPS_REACHED"


class AgentStepType(StrEnum):
    MODEL_DECISION = "MODEL_DECISION"
    TOOL_CALL = "TOOL_CALL"
    TOOL_RESULT = "TOOL_RESULT"
    FINAL_ANSWER = "FINAL_ANSWER"
    VALIDATION = "VALIDATION"


class StepStatus(StrEnum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ConversationRole(StrEnum):
    SYSTEM = "SYSTEM"
    USER = "USER"
    ASSISTANT = "ASSISTANT"
    TOOL = "TOOL"


class QuestionType(StrEnum):
    PRODUCT_KNOWLEDGE = "PRODUCT_KNOWLEDGE"
    PRICE_STOCK = "PRICE_STOCK"
    ORDER_STATUS = "ORDER_STATUS"
    AFTER_SALE = "AFTER_SALE"
