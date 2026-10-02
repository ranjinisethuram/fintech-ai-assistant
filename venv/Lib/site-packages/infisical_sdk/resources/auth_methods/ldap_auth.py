from infisical_sdk.api_types import MachineIdentityLoginResponse

from typing import Callable
from infisical_sdk.infisical_requests import InfisicalRequests

class LdapAuth:
    def __init__(self, requests: InfisicalRequests, setToken: Callable[[str], None]):
        self.requests = requests
        self.setToken = setToken

    def login(self, identity_id: str, username: str, password: str) -> MachineIdentityLoginResponse:
        """
        Login with LDAP Auth.

        Args:
            identity_id (str): Your Machine Identity ID.
            username (str): Your LDAP username.
            password (str): Your LDAP password.

        Returns:
            MachineIdentityLoginResponse: A response containing the access token and related information.
        """

        requestBody = {
            "identityId": identity_id,
            "username": username,
            "password": password
        }

        result = self.requests.post(
            path="/api/v1/auth/ldap-auth/login",
            json=requestBody,
            model=MachineIdentityLoginResponse
        )

        self.setToken(result.data.accessToken)

        return result.data
