from typing import Optional, Dict, Any, List, Union

from infisical_sdk.infisical_requests import InfisicalRequests
from infisical_sdk.api_types import (
    DynamicSecret,
    DynamicSecretLease,
    DynamicSecretProviders,
    SingleDynamicSecretResponse,
    CreateLeaseResponse,
    SingleLeaseResponse,
)


class DynamicSecretLeases:
    """Manages dynamic secret leases."""

    def __init__(self, requests: InfisicalRequests) -> None:
        self.requests = requests

    def create(
            self,
            dynamic_secret_name: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/",
            ttl: str = None) -> CreateLeaseResponse:
        """Create a new lease for a dynamic secret.

        Args:
            dynamic_secret_name: The name of the dynamic secret to create a lease for.
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path to the dynamic secret. Defaults to "/".
            ttl: The time to live for the lease (e.g., "1h", "30m").

        Returns:
            CreateLeaseResponse containing lease, dynamicSecret, and data (credentials).
        """
        request_body = {
            "dynamicSecretName": dynamic_secret_name,
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
            "ttl": ttl,
        }

        result = self.requests.post(
            path="/api/v1/dynamic-secrets/leases",
            json=request_body,
            model=CreateLeaseResponse
        )

        return result.data

    def revoke(
            self,
            lease_id: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/",
            is_forced: bool = False) -> DynamicSecretLease:
        """Revoke a dynamic secret lease.

        Args:
            lease_id: The ID of the lease to revoke.
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path to the dynamic secret. Defaults to "/".
            is_forced: A boolean flag to delete the the dynamic secret from Infisical without trying to remove it from external provider. Used when the dynamic secret got modified externally.

        Returns:
            The revoked lease.
        """
        request_body = {
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
            "isForced": is_forced,
        }

        result = self.requests.delete(
            path=f"/api/v1/dynamic-secrets/leases/{lease_id}",
            json=request_body,
            model=SingleLeaseResponse
        )

        return result.data.lease

    def renew(
            self,
            lease_id: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/",
            ttl: str = None) -> DynamicSecretLease:
        """Renew a dynamic secret lease.

        Args:
            lease_id: The ID of the lease to renew.
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path to the dynamic secret. Defaults to "/".
            ttl: The new time to live for the lease (e.g., "1h", "30m").

        Returns:
            The renewed lease.
        """
        request_body = {
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
            "ttl": ttl,
        }

        result = self.requests.post(
            path=f"/api/v1/dynamic-secrets/leases/{lease_id}/renew",
            json=request_body,
            model=SingleLeaseResponse
        )

        return result.data.lease

    def get(
            self,
            lease_id: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/") -> DynamicSecretLease:
        """Get a dynamic secret lease by ID.

        Args:
            lease_id: The ID of the lease to retrieve.
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path to the dynamic secret. Defaults to "/".

        Returns:
            The lease with dynamicSecret included.
        """
        params = {
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
        }

        result = self.requests.get(
            path=f"/api/v1/dynamic-secrets/leases/{lease_id}",
            params=params,
            model=SingleLeaseResponse
        )

        return result.data.lease


class DynamicSecrets:
    """Manages dynamic secrets in Infisical."""

    def __init__(self, requests: InfisicalRequests) -> None:
        self.requests = requests
        self.leases = DynamicSecretLeases(requests)

    def create(
            self,
            name: str,
            provider_type: Union[DynamicSecretProviders, str],
            inputs: Dict[str, Any],
            default_ttl: str,
            max_ttl: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/",
            metadata: Optional[List[Dict[str, str]]] = None) -> DynamicSecret:
        """Create a new dynamic secret.

        Args:
            name: The name of the dynamic secret.
            provider_type: The provider type (e.g., DynamicSecretProviders.SQL_DATABASE).
            inputs: The provider-specific configuration inputs. Check the Infisical documentation for the specific provider for the inputs: https://infisical.com/docs/api-reference/endpoints/dynamic-secrets/create#body-provider
            default_ttl: The default time to live for leases (e.g., "1h", "30m").
            max_ttl: The maximum time to live for leases (e.g., "24h").
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path where the dynamic secret will be created. Defaults to "/".
            metadata: Optional list of metadata items with 'key' and 'value'.

        Returns:
            The created dynamic secret.
        """
        provider_value = provider_type.value if isinstance(provider_type, DynamicSecretProviders) else provider_type

        request_body = {
            "name": name,
            "provider": {
                "type": provider_value,
                "inputs": inputs,
            },
            "defaultTTL": default_ttl,
            "maxTTL": max_ttl,
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
            "metadata": metadata,
        }

        result = self.requests.post(
            path="/api/v1/dynamic-secrets",
            json=request_body,
            model=SingleDynamicSecretResponse
        )

        return result.data.dynamicSecret

    def delete(
            self,
            name: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/",
            is_forced: bool = False) -> DynamicSecret:
        """Delete a dynamic secret.

        Args:
            name: The name of the dynamic secret to delete.
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path to the dynamic secret. Defaults to "/".
            is_forced: A boolean flag to delete the the dynamic secret from Infisical without trying to remove it from external provider. Used when the dynamic secret got modified externally.

        Returns:
            The deleted dynamic secret.
        """
        request_body = {
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
            "isForced": is_forced,
        }

        result = self.requests.delete(
            path=f"/api/v1/dynamic-secrets/{name}",
            json=request_body,
            model=SingleDynamicSecretResponse
        )

        return result.data.dynamicSecret

    def get_by_name(
            self,
            name: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/") -> DynamicSecret:
        """Get a dynamic secret by name.

        Args:
            name: The name of the dynamic secret.
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path to the dynamic secret. Defaults to "/".

        Returns:
            The dynamic secret.
        """
        params = {
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
        }

        result = self.requests.get(
            path=f"/api/v1/dynamic-secrets/{name}",
            params=params,
            model=SingleDynamicSecretResponse
        )

        return result.data.dynamicSecret

    def update(
            self,
            name: str,
            project_slug: str,
            environment_slug: str,
            path: str = "/",
            default_ttl: Optional[str] = None,
            max_ttl: Optional[str] = None,
            new_name: Optional[str] = None,
            inputs: Optional[Dict[str, Any]] = None,
            metadata: Optional[List[Dict[str, str]]] = None,
            username_template: Optional[str] = None) -> DynamicSecret:
        """Update an existing dynamic secret.

        Args:
            name: The current name of the dynamic secret.
            project_slug: The slug of the project.
            environment_slug: The slug of the environment.
            path: The path to the dynamic secret. Defaults to "/".
            default_ttl: The new default time to live for leases (e.g., "1h").
            max_ttl: The new maximum time to live for leases (e.g., "24h").
            new_name: The new name for the dynamic secret.
            inputs: Updated provider-specific configuration inputs.
            metadata: Updated metadata list with 'key' and 'value' items.
            username_template: The new username template for the dynamic secret.

        Returns:
            The updated dynamic secret.
        """
        data: Dict[str, Any] = {}
        if inputs is not None:
            data["inputs"] = inputs
        if default_ttl is not None:
            data["defaultTTL"] = default_ttl
        if max_ttl is not None:
            data["maxTTL"] = max_ttl
        if new_name is not None:
            data["newName"] = new_name
        if metadata is not None:
            data["metadata"] = metadata
        if username_template is not None:
            data["usernameTemplate"] = username_template

        request_body = {
            "projectSlug": project_slug,
            "environmentSlug": environment_slug,
            "path": path,
            "data": data,
        }

        result = self.requests.patch(
            path=f"/api/v1/dynamic-secrets/{name}",
            json=request_body,
            model=SingleDynamicSecretResponse
        )

        return result.data.dynamicSecret

