"""Ivalua Connector extension declaration and tenant-scoped credential storage.

Ivalua does not publish a public REST API reference (see CONNECTOR_DISCOVERY.md
Section 1 -- honesty gate). Each tenant configures its own base URL and API path
prefix; handlers must treat any resource path as potentially wrong for a given
tenant until a real response confirms it, and surface a clear "check your API
path prefix" message on 404/501 instead of a generic connection error.
"""
from __future__ import annotations

from imperal_sdk import ChatExtension, Extension

ext = Extension(
    "ivalua-connector",
    version="0.1.0",
    display_name="Ivalua",
    description=(
        "Connect your own Ivalua Source-to-Pay tenant through OAuth2 client "
        "credentials. Read and safely manage Requisitions, Purchase Orders, "
        "Suppliers, Invoices, Sourcing Events, Contracts, and Catalog Items "
        "through the tenant's configured REST web services."
    ),
    icon="icon.svg",
    capabilities=["ivalua:read", "ivalua:write"],
    actions_explicit=True,
    system=False,
)

chat = ChatExtension(
    ext,
    tool_name="ivalua",
    description=(
        "Ivalua Connector -- tenant-scoped REST operations for Requisitions, "
        "Purchase Orders, Suppliers, Invoices, Sourcing Events, Contracts, and "
        "Catalog Items, against a customer-configured Ivalua tenant."
    ),
)

ext.secret(
    "ivalua_connections",
    "JSON list of connected Ivalua tenants and encrypted OAuth credentials. Managed only through connect_ivalua and disconnect_ivalua.",
    required=True,
    write_mode="both",
    max_bytes=65536,
    rotation_hint_days=90,
)(lambda: None)


@ext.health_check
async def health_check(ctx) -> dict:
    """Report whether at least one Ivalua tenant is connected."""
    import json

    raw = await ctx.secrets.get("ivalua_connections")
    connections = []
    if raw:
        try:
            connections = json.loads(raw)
        except (TypeError, ValueError):
            connections = []
    return {"connected": bool(connections), "connection_count": len(connections)}
