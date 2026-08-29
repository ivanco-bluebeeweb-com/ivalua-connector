"""Ivalua Connector App settings center panel.

Connection setup guidance lives exclusively in ivalua_connect_help.
This panel contains current connection state and destructive disconnect actions only.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers as h


def _connection_row(connection: dict) -> ui.UINode:
    label = connection.get("label") or connection.get("tenant_url", "")
    return ui.Stack(direction="v", gap=1, align="start", children=[
        ui.Text(label, variant="body"),
        ui.Text(f"Tenant: {connection.get('tenant_url', '')}", variant="caption"),
        ui.Text(f"API path prefix: {connection.get('api_path_prefix', '/api/v1')}", variant="caption"),
        ui.Button(
            "Disconnect", variant="danger", size="sm",
            on_click=ui.Call("disconnect_ivalua", {"connection_id": connection.get("id", "")}),
        ),
    ])


@ext.panel("ivalua_settings", slot="center", title="Ivalua settings", icon="settings", center_overlay=True)
async def ivalua_settings_panel(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Stack(direction="v", gap=2, align="start", children=[
            ui.Header(text="App settings", level=2, subtitle="Manage saved Ivalua tenants"),
            ui.Text("No Ivalua tenants are connected yet.", variant="caption"),
        ])
    rows: list[ui.UINode] = [
        ui.Header(text="App settings", level=2, subtitle="Manage saved Ivalua tenants"),
        ui.Text("Connections", variant="subtitle"),
    ]
    for index, connection in enumerate(connections):
        if index:
            rows.append(ui.Divider())
        rows.append(_connection_row(connection))
    return ui.Stack(direction="v", gap=3, align="stretch", children=rows)
