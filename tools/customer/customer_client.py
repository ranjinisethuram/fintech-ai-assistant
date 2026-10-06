from typing import Optional

import httpx

from data.CustomerContext import CustomerContext
from data.AccountSummary import AccountSummary
from data.BeneficiaryResponse import BeneficiaryResponse


async def fetch_customer_profile(customer_id: str, access_token: str, base_url: str = "http://localhost:8080") -> CustomerContext:
    """Fetch customer profile from Java backend and map to the existing CustomerContext dataclass.

    GET {base_url}/api/v1/customers/profile/{customerId}
    Authorization: Bearer {accessToken}
    """
    url = f"{base_url.rstrip('/')}/api/v1/customers/profile/{customer_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise httpx.HTTPStatusError(f"Failed to fetch customer profile: {resp.status_code}", request=resp.request, response=resp)

    payload = resp.json()

    accounts = []
    for a in payload.get("accounts", []) or []:
        accounts.append(
            AccountSummary(
                account_id=a.get("accountId") or a.get("account_id"),
                account_type=a.get("accountType") or a.get("account_type"),
                is_default=bool(a.get("default") or a.get("isDefault") or False),
            )
        )

    beneficiaries = []
    for b in payload.get("beneficiaries", []) or []:
        beneficiaries.append(
            BeneficiaryResponse(
                beneficiary_id=b.get("beneficiaryId") or b.get("beneficiary_id"),
                name=b.get("name"),
                account_id=b.get("accountId") or b.get("account_id"),
            )
        )

    profile = CustomerContext(
        customer_id=payload.get("customerId") or payload.get("customer_id"),
        customer_name=payload.get("customerName") or payload.get("customer_name"),
        default_account_id=payload.get("defaultAccountId") or payload.get("default_account_id"),
        AccountSummary=accounts,
        BeneficiaryResponse=beneficiaries,
    )

    return profile
