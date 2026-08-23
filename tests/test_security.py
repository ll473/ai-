import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.core.security import create_access_token, decode_access_token
from backend.app.schemas.ai import ModelConfigCreate


def test_access_token_round_trip() -> None:
    token = create_access_token("42", extra={"role": "USER"})
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["role"] == "USER"
    assert payload["type"] == "access"


def test_production_rejects_default_secret() -> None:
    with pytest.raises(ValidationError, match="Production requires an explicit SECRET_KEY"):
        Settings(
            app_env="production",
            secret_key="development-only-change-me-at-least-32-bytes",
        )


def test_ai_base_url_rejects_untrusted_or_insecure_hosts() -> None:
    with pytest.raises(ValidationError, match="必须使用 HTTPS"):
        ModelConfigCreate(name="unsafe", base_url="http://127.0.0.1:8000/v1")
    with pytest.raises(ValidationError, match="不在可信服务商列表"):
        ModelConfigCreate(name="exfiltration", base_url="https://attacker.example/v1")
