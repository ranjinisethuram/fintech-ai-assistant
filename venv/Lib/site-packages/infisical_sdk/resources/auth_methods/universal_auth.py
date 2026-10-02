from infisical_sdk.api_types import MachineIdentityLoginResponse

from typing import Callable
from infisical_sdk.infisical_requests import InfisicalRequests
class UniversalAuth:
    def __init__(self, requests: InfisicalRequests, setToken: Callable[[str], None]):
        self.requests = requests
        self.setToken = setToken

    def login(self, client_id: str, client_secret: str) -> MachineIdentityLoginResponse:
        """
        Login with Universal Auth.

        Args:
            client_id (str): Your Machine Identity Client ID.
            client_secret (str): Your Machine Identity Client Secret.

        Returns:
            Dict: A dictionary containing the access token and related information.
        """

        requestBody = {
            "clientId": client_id,
            "clientSecret": client_secret
        }

        result = self.requests.post(
          path="/api/v1/auth/universal-auth/login",
          json=requestBody,
          model=MachineIdentityLoginResponse
        )

        self.setToken(result.data.accessToken)

        return result.data