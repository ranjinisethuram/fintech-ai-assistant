from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.exceptions import NoCredentialsError

from infisical_sdk.infisical_requests import InfisicalRequests
from infisical_sdk.api_types import MachineIdentityLoginResponse

from typing import Callable

import requests
import boto3
import base64
import json
import os
import datetime

from typing import Dict, Any


class AWSAuth:
    def __init__(self, requests: InfisicalRequests, setToken: Callable[[str], None]) -> None:
        self.requests = requests
        self.setToken = setToken

    def login(self, identity_id: str) -> MachineIdentityLoginResponse:
        """
        Login with AWS Authentication.

        Args:
            identity_id (str): Your Machine Identity ID that has AWS Auth configured.

        Returns:
            Dict: A dictionary containing the access token and related information.
        """

        identity_id = identity_id or os.getenv("INFISICAL_AWS_IAM_AUTH_IDENTITY_ID")
        if not identity_id:
            raise ValueError(
              "Identity ID must be provided or set in the environment variable" +
              "INFISICAL_AWS_IAM_AUTH_IDENTITY_ID."
            )

        aws_region = self.get_aws_region()
        session = boto3.Session(region_name=aws_region)

        credentials = self._get_aws_credentials(session)

        iam_request_url = f"https://sts.{aws_region}.amazonaws.com/"
        iam_request_body = "Action=GetCallerIdentity&Version=2011-06-15"

        request_headers = self._prepare_aws_request(
          iam_request_url,
          iam_request_body,
          credentials,
          aws_region
        )

        requestBody = {
          "identityId": identity_id,
          "iamRequestBody": base64.b64encode(iam_request_body.encode()).decode(),
          "iamRequestHeaders": base64.b64encode(json.dumps(request_headers).encode()).decode(),
          "iamHttpRequestMethod": "POST"
        }

        result = self.requests.post(
          path="/api/v1/auth/aws-auth/login",
          json=requestBody,
          model=MachineIdentityLoginResponse
        )

        self.setToken(result.data.accessToken)

        return result.data

    def _get_aws_credentials(self, session: boto3.Session) -> Any:
        try:
            credentials = session.get_credentials()
            if credentials is None:
                raise NoCredentialsError("AWS credentials not found.")
            return credentials.get_frozen_credentials()
        except NoCredentialsError as e:
            raise RuntimeError(f"AWS IAM Auth Login failed: {str(e)}")

    def _prepare_aws_request(
      self,
      url: str,
      body: str,
      credentials: Any,
      region: str) -> Dict[str, str]:

        current_time = datetime.datetime.now(datetime.timezone.utc)
        amz_date = current_time.strftime('%Y%m%dT%H%M%SZ')

        request = AWSRequest(method="POST", url=url, data=body)
        request.headers["X-Amz-Date"] = amz_date
        request.headers["Host"] = f"sts.{region}.amazonaws.com"
        request.headers["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"
        request.headers["Content-Length"] = str(len(body))

        signer = SigV4Auth(credentials, "sts", region)
        signer.add_auth(request)

        return {k: v for k, v in request.headers.items() if k.lower() != "content-length"}

    @staticmethod
    def get_aws_region() -> str:
        region = os.getenv("AWS_REGION")  # Typically found in lambda runtime environment
        if region:
            return region

        try:
            return AWSAuth._get_aws_ec2_identity_document_region()
        except Exception as e:
            raise Exception("Failed to retrieve AWS region") from e

    @staticmethod
    def _get_aws_ec2_identity_document_region(timeout: int = 5000) -> str:
        session = requests.Session()
        token_response = session.put(
            "http://169.254.169.254/latest/api/token",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "21600"},
            timeout=timeout / 1000
        )
        token_response.raise_for_status()
        metadata_token = token_response.text

        identity_response = session.get(
            "http://169.254.169.254/latest/dynamic/instance-identity/document",
            headers={"X-aws-ec2-metadata-token": metadata_token, "Accept": "application/json"},
            timeout=timeout / 1000
        )

        identity_response.raise_for_status()
        return identity_response.json().get("region")