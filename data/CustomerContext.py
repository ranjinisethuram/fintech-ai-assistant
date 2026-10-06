from dataclasses import dataclass


@dataclass
class CustomerContext:
    customer_id: str
    customer_name: str
    default_account_id: str | None = None
    AccountSummary: list[AccountSummary] | None = None
    BeneficiaryResponse: list[BeneficiaryResponse] | None = None