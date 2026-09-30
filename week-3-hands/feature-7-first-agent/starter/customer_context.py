from dataclasses import dataclass
from uuid import UUID


@dataclass
class CustomerContext:
    customer_id: UUID
    customer_name: str
    account_id: UUID
