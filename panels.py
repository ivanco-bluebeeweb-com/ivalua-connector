"""Ivalua Connector panel UI, aligned with UI_INTERFACE_STANDARD.md.

The left sidebar contains plain stacked content only: no card containers, all
form controls have visible labels with contextual placeholders, and App
settings is the last element. Setup instructions live solely in the help
dialog and are not duplicated in the form/sidebar. The connect form stretches
to the full width of the sidebar and its fields stretch to the form's width.
"""
from __future__ import annotations

from imperal_sdk import ui

from app import ext
import handlers as h


def _settings_button() -> ui.UINode:
    return ui.Button(
        "App settings", variant="secondary", size="sm", icon="settings", on_click=ui.Call("__panel__ivalua_settings"))


def _field(label: str, node: ui.UINode) -> ui.UINode:
    return ui.Stack(direction="v", gap=1, align="stretch", children=[
        ui.Text(label, variant="caption"), node,
    ])


def _connection_rows(connections: list[dict]) -> ui.UINode:
    if not connections:
        return ui.Text("No Ivalua tenants connected yet.", variant="caption")
    children: list[ui.UINode] = []
    for index, connection in enumerate(connections):
        if index:
            children.append(ui.Divider())
        label = connection.get("label") or connection.get("tenant_url", "")
        children.append(ui.Stack(direction="v", gap=1, align="start", children=[
            ui.Text(label, variant="body"),
            ui.Text(f"Tenant: {connection.get('tenant_url', '')}", variant="caption"),
        ]))
    return ui.Stack(direction="v", gap=2, align="stretch", children=children)


def _connect_form() -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Button("How do I set this up?", variant="ghost", size="sm", icon="HelpCircle",
                  on_click=ui.Call("__panel__ivalua_connect_help")),
        ui.Form(action="connect_ivalua", submit_label="Verify and connect", children=[
            _field("Tenant label (optional)", ui.Input(param_name="label", placeholder="e.g. Acme production tenant")),
            _field("Ivalua tenant URL", ui.Input(param_name="tenant_url", placeholder="https://acme.ivalua.app")),
            _field("API path prefix (optional)", ui.Input(param_name="api_path_prefix", placeholder="/api/v1 — leave default unless your admin says otherwise")),
            _field("OAuth client ID", ui.Input(param_name="client_id", placeholder="Client ID from your Ivalua tenant admin")),
            _field("OAuth client secret", ui.Password(param_name="client_secret", placeholder="Secret for that client ID")),
        ]),
    ])


@ext.panel("ivalua_connect_help", slot="center", title="Connect Ivalua", center_overlay=True)
async def ivalua_connect_help(ctx, **kwargs) -> ui.UINode:
    return ui.Stack(direction="v", gap=3, align="stretch", children=[
        ui.Text("Ask your Ivalua tenant administrator for an OAuth2 client ID/secret, then paste your tenant URL, client ID, and client secret here.", variant="body"),
        ui.Alert(title="No universal API path", message="Ivalua does not publish one universal REST API path across all tenants. Leave the API path prefix at its default (/api/v1) unless your admin tells you it's different — run the access audit after connecting to confirm what's reachable.", type="info"),
        ui.Alert(title="Not included", message="Full Sourcing bid-collection/scoring workflows and Supplier onboarding lifecycle management are separate Ivalua modules not covered by this connector (read-only Sourcing Events/Contracts only).", type="info"),
    ])


@ext.panel("ivalua_sidebar", slot="left", title="Ivalua", default_width=340, min_width=280, max_width=460)
async def ivalua_sidebar(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    body: list[ui.UINode] = [ui.Text("Ivalua", variant="title")]
    if connections:
        body.append(_connection_rows(connections))
        body.append(ui.Divider())
        body.append(ui.ListItem(title="Overview", icon="LayoutDashboard",
                                 on_click=ui.Call("__panel__ivalua_center")))
        for label, key in [
            ("Requisitions", "requisitions"), ("Purchase Orders", "purchase_orders"),
            ("Suppliers", "suppliers"), ("Invoices", "invoices"),
            ("Sourcing Events", "sourcing_events"), ("Contracts", "contracts"),
            ("Catalog Items", "catalog_items"),
        ]:
            body.append(ui.ListItem(title=label, icon="ChevronRight",
                                     on_click=ui.Call("__panel__ivalua_center", {"section": key})))
    else:
        body.append(_connect_form())
    body.append(ui.Divider())
    body.append(_settings_button())
    return ui.Stack(direction="v", gap=3, align="stretch", children=body)


@ext.panel("ivalua_center", slot="center", title="Ivalua overview", icon="ShoppingCart", center_overlay=True)
async def ivalua_center_panel(ctx, **kwargs) -> ui.UINode:
    connections = await h._load_connections(ctx)
    if not connections:
        return ui.Empty(message="Connect an Ivalua tenant from the sidebar to see it here.", icon="🟦")

    from schemas import (
        AuditAccessParams, ListRequisitionsParams, ListPurchaseOrdersParams,
        ListSuppliersParams, ListInvoicesParams, ListSourcingEventsParams,
        ListContractsParams, ListCatalogItemsParams)

    conn_id = connections[0].get("id", "")
    section = kwargs.get("section", "")
    body: list[ui.UINode] = []

    async def _section_table(title: str, result, columns) -> None:
        body.append(ui.Text(title, variant="subtitle"))
        if result.success and result.data and result.data.items:
            rows = [{"id": r.id, "title": r.title} for r in result.data.items]
            body.append(ui.DataTable(columns=columns, rows=rows))
        else:
            body.append(ui.Empty(message=f"No {title.lower()} found, or this module isn't reachable for this tenant.", icon="Inbox"))

    if not section:
        body.append(ui.Text("Access audit", variant="subtitle"))
        audit_result = await h.audit_ivalua_access(ctx, AuditAccessParams(connection_id=conn_id))
        if audit_result.success and audit_result.data:
            r = audit_result.data
            body.append(ui.Stats(children=[
                ui.Stat(label="Available", value=str(r.available_count)),
                ui.Stat(label="Unavailable", value=str(r.unavailable_count)),
            ]))
            for c in r.checks:
                color = "green" if c.available else "red"
                body.append(ui.Stack(direction="h", gap=2, align="center", children=[
                    ui.Badge(label="OK" if c.available else "BLOCKED", color=color),
                    ui.Text(c.name, variant="body"),
                ]))
        else:
            body.append(ui.Text("Could not run the access audit.", variant="caption"))
    elif section == "requisitions":
        result = await h.list_requisitions(ctx, ListRequisitionsParams(connection_id=conn_id, top=25))
        await _section_table("Requisitions", result, [{"key": "id", "label": "ID"}, {"key": "title", "label": "Title"}])
    elif section == "purchase_orders":
        result = await h.list_purchase_orders(ctx, ListPurchaseOrdersParams(connection_id=conn_id, top=25))
        await _section_table("Purchase Orders", result, [{"key": "id", "label": "PO"}, {"key": "title", "label": "Title"}])
    elif section == "suppliers":
        result = await h.list_suppliers(ctx, ListSuppliersParams(connection_id=conn_id, top=25))
        await _section_table("Suppliers", result, [{"key": "id", "label": "ID"}, {"key": "title", "label": "Name"}])
    elif section == "invoices":
        result = await h.list_invoices(ctx, ListInvoicesParams(connection_id=conn_id, top=25))
        await _section_table("Invoices", result, [{"key": "id", "label": "ID"}, {"key": "title", "label": "Title"}])
    elif section == "sourcing_events":
        result = await h.list_sourcing_events(ctx, ListSourcingEventsParams(connection_id=conn_id, top=25))
        await _section_table("Sourcing Events", result, [{"key": "id", "label": "ID"}, {"key": "title", "label": "Title"}])
    elif section == "contracts":
        result = await h.list_contracts(ctx, ListContractsParams(connection_id=conn_id, top=25))
        await _section_table("Contracts", result, [{"key": "id", "label": "ID"}, {"key": "title", "label": "Title"}])
    elif section == "catalog_items":
        result = await h.list_catalog_items(ctx, ListCatalogItemsParams(connection_id=conn_id, top=25))
        await _section_table("Catalog Items", result, [{"key": "id", "label": "ID"}, {"key": "title", "label": "Title"}])

    return ui.Stack(direction="v", gap=3, align="stretch", children=body)
