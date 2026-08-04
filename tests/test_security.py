from backend.app.core.security import create_access_token, decode_access_token


def test_access_token_round_trip() -> None:
    token = create_access_token("42", extra={"role": "USER"})
    payload = decode_access_token(token)

    assert payload["sub"] == "42"
    assert payload["role"] == "USER"
    assert payload["type"] == "access"

