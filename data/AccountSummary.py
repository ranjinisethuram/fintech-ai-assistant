from dataclasses import dataclass

@dataclass
class AccountSummary:
    account_id: str
    account_type: str
    is_default: bool
