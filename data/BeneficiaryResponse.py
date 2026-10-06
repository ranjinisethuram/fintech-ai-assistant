from dataclasses import dataclass

@dataclass
class BeneficiaryResponse:
    beneficiary_id: str
    name: str
    account_id: str