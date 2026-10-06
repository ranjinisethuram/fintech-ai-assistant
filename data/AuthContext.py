from dataclasses import dataclass

@dataclass
class AuthContext:
    customer_id: str
    roles: list[str]
    permissions: list[str]
    session_id: str
    access_token: str
    refresh_token: str
    refresh_token_expiry: int