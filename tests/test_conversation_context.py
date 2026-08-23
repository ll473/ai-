from datetime import UTC, datetime
from types import SimpleNamespace

from backend.app.models.enums import ConversationRole, QuestionType
from backend.app.schemas.ai import ConversationMessagePublic


def test_conversation_message_public_exposes_saved_question_context() -> None:
    message = SimpleNamespace(
        id=1,
        role=ConversationRole.USER,
        content="适合长时间办公吗",
        question_type=QuestionType.PRODUCT_KNOWLEDGE,
        metadata_json={"product_id": 42, "order_no": None},
        created_at=datetime(2026, 8, 23, tzinfo=UTC),
    )

    public = ConversationMessagePublic.model_validate(message)

    assert public.metadata_json == {"product_id": 42, "order_no": None}
