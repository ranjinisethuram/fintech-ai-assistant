from typing import Callable

class TokenAuth:
    def __init__(self, setToken: Callable[[str], None]):
        self.setToken = setToken

    def login(self, token: str) -> str:
        """
        Authenticate using a token. This can be either a machine identity token or a user JWT token.
        
        Machine Identity Token: Generated from Token Auth method in Infisical.
        User JWT Token: A valid JWT token for user authentication.
        
        Args:
            token (str): Your authentication token (machine identity token or user JWT).
        
        Returns:
            str: The token that was set.
        """
        self.setToken(token)
        return token

