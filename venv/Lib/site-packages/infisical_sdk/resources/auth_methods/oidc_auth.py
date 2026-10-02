from infisical_sdk.api_types import MachineIdentityLoginResponse

from typing import Callable
from infisical_sdk.infisical_requests import InfisicalRequests

class OidcAuth:
    def __init__(self, requests: InfisicalRequests, setToken: Callable[[str], None]):
        self.requests = requests
        self.setToken = setToken

    def login(self, identity_id: str, jwt: str) -> MachineIdentityLoginResponse:
        """
        Login with OIDC Auth.

        Args:
            identity_id (str): Your Machine Identity ID.
            jwt (str): Your OIDC JWT.

        Returns:
            MachineIdentityLoginResponse: A response object containing the access token and related information.
        """

        requestBody = {
            "identityId": identity_id,
            "jwt": jwt
        }

        result = self.requests.post(
          path="/api/v1/auth/oidc-auth/login",
          json=requestBody,
          model=MachineIdentityLoginResponse
        )

        self.setToken(result.data.accessToken)

        return result.data