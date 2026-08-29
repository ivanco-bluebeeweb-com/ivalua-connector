"""Thin OAuth2 REST client for Ivalua tenant-scoped REST web services.

Ivalua does not publish a public REST API reference (see CONNECTOR_DISCOVERY.md
Section 1). The client speaks generic REST/JSON, uses a configurable
api_path_prefix (default "/api/v1"), and never assumes a resource path is
correct for a given tenant before a real response confirms it -- a 404/501 is
surfaced as a distinct "check your API path prefix" hint rather than a generic
connection error.
"""
from __future__ import annotations

import time
from typing import Any
from urllib.parse import urljoin

import httpx


class IvaluaError(RuntimeError):
    """A safe provider-facing error; never includes credentials."""

    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


def normalise_base_url(value: str) -> str:
    url = (value or "").strip().rstrip("/")
    if not url.startswith("https://"):
        raise IvaluaError("Tenant URL must be an HTTPS host, e.g. https://acme.ivalua.app.")
    return url


def normalise_path_prefix(value: str) -> str:
    prefix = (value or "").strip()
    if not prefix:
        return "/api/v1"
    if not prefix.startswith("/"):
        prefix = "/" + prefix
    return prefix.rstrip("/")


def rest_items(body: Any) -> list[dict[str, Any]]:
    """Normalise Ivalua REST list envelopes to a list of objects."""
    if isinstance(body, list):
        return [item for item in body if isinstance(item, dict)]
    if not isinstance(body, dict):
        return []
    for key in ("items", "results", "value", "data"):
        items = body.get(key)
        if isinstance(items, list):
            return items
    return []


class IvaluaClient:
    """OAuth2 client-credentials REST client for a tenant-scoped Ivalua instance."""

    def __init__(
        self,
        tenant_url: str,
        client_id: str,
        client_secret: str,
        *,
        api_path_prefix: str = "/api/v1",
        timeout: float = 30.0,
    ):
        self.tenant_url = normalise_base_url(tenant_url)
        self.api_path_prefix = normalise_path_prefix(api_path_prefix)
        self.token_url = f"{self.tenant_url}/oauth2/token"
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._token: str | None = None
        self._token_expiry: float = 0.0

    async def _ensure_token(self, http: httpx.AsyncClient) -> None:
        if self._token and time.time() < self._token_expiry - 30:
            return
        try:
            resp = await http.post(
                self.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=self.timeout,
            )
        except httpx.HTTPError as exc:
            raise IvaluaError(f"Could not reach Ivalua OAuth2 token endpoint: {exc}", retryable=True) from exc
        if resp.status_code >= 400:
            raise IvaluaError(
                f"Ivalua OAuth2 token request failed (HTTP {resp.status_code}). Check client ID/secret and tenant URL.",
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise IvaluaError("Ivalua OAuth2 response did not include an access_token.")
        self._token = token
        self._token_expiry = time.time() + int(payload.get("expires_in", 3600))

    async def request(self, method: str, path: str, *, params: dict | None = None, json_body: dict | None = None) -> Any:
        full_path = self.api_path_prefix + "/" + path.lstrip("/")
        url = urljoin(self.tenant_url + "/", full_path.lstrip("/"))
        async with httpx.AsyncClient() as http:
            await self._ensure_token(http)
            headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
            try:
                resp = await http.request(method, url, headers=headers, params=params, json=json_body, timeout=self.timeout)
            except httpx.HTTPError as exc:
                raise IvaluaError(f"Could not reach the Ivalua tenant: {exc}", retryable=True) from exc
        if resp.status_code in (404, 501):
            raise IvaluaError(
                "Resource not found at this path. Ivalua does not use one universal API path across tenants -- "
                "check the API path prefix in this connection's settings.",
                retryable=False,
            )
        if resp.status_code == 403:
            raise IvaluaError("This Ivalua module is not licensed/scoped for the connected OAuth client.", retryable=False)
        if resp.status_code == 429:
            raise IvaluaError("Ivalua API rate limit hit. Retry shortly.", retryable=True)
        if resp.status_code >= 400:
            raise IvaluaError(f"Ivalua API request failed (HTTP {resp.status_code}).", retryable=resp.status_code >= 500)
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {}

    async def list_resource(self, resource_name: str, *, params: dict | None = None) -> list[dict]:
        """Generic passthrough: list records of any tenant-configured resource path."""
        body = await self.request("GET", resource_name, params=params)
        return rest_items(body)

    async def get_resource(self, resource_name: str, record_id: str) -> dict:
        """Generic passthrough: read one record of any tenant-configured resource path."""
        return await self.request("GET", f"{resource_name}/{record_id}")

    async def create_resource(self, resource_name: str, values: dict) -> dict:
        """Generic passthrough: create a record on any tenant-configured resource path."""
        return await self.request("POST", resource_name, json_body=values)

    async def update_resource(self, resource_name: str, record_id: str, values: dict) -> dict:
        """Generic passthrough: update a record on any tenant-configured resource path."""
        return await self.request("PATCH", f"{resource_name}/{record_id}", json_body=values)

    async def delete_resource(self, resource_name: str, record_id: str) -> None:
        """Generic passthrough: delete a record on any tenant-configured resource path."""
        await self.request("DELETE", f"{resource_name}/{record_id}")
