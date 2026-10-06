import base64
import json
import time

from main import build_customer_context_from_token, validate_access_token


def _jwt_from_payload(payload):
    def enc(value):
        return base64.urlsafe_b64encode(json.dumps(value, separators=(",", ":")).encode()).rstrip(b"=").decode()

    header = {"alg": "HS256", "typ": "JWT"}
    return f"{enc(header)}.{enc(payload)}.signature"


def test_validate_access_token_and_build_customer_context():
    now = int(time.time())
    token = _jwt_from_payload(
        {
            "sub": "cust-123",
            "iss": "http://localhost:9090/realms/fintech-realm",
            "aud": "fintech-ai-assistant",
            "session_state": "session-42",
            "realm_access": {"roles": ["admin", "user"]},
            "permissions": ["read:accounts", "write:transactions"],
            "exp": now + 300,
            "iat": now - 30,
        }
    )

    claims = validate_access_token(token)
    customer = build_customer_context_from_token(token, claims)

    assert claims["sub"] == "cust-123"
    assert customer.customer_id == "cust-123"
    assert "admin" in customer.roles
    assert "read:accounts" in customer.permissions
    assert customer.session_id == "session-42"
    assert customer.access_token == token
