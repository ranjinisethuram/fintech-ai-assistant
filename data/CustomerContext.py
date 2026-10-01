@dataclass
class CustomerContext:
    customer_id: str
    roles: list[str]
    permissions: list[str]
    session_id: str
    access_token: str
    default_account_id: str | None = None