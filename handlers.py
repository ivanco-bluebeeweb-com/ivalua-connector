"""Chat functions for the tenant-scoped Ivalua Connector.

Every handler resolves the target tenant connection explicitly (by
connection_id, or the sole connection if only one exists) and never assumes
a resource path is correct before a real call confirms it -- Ivalua does not
publish one universal REST API path (see CONNECTOR_DISCOVERY.md Section 1).
"""
from __future__ import annotations

import json
import uuid

from imperal_sdk import ActionResult

import ivalua_client as ic
from app import chat
from schemas import (
    AccessAudit, ApprovePurchaseOrderParams, AuditAccessParams, Capability,
    ConnectionList, ConnectIvaluaParams, CreatePurchaseOrderParams,
    CreateRequisitionParams, CreateSupplierParams, DeleteResult,
    DisconnectIvaluaParams, GetContractParams, GetInvoiceParams,
    GetPurchaseOrderParams, GetRequisitionParams, GetSourcingEventParams,
    GetSupplierParams, IvaluaConnection, IvaluaRecord, IvaluaRecordList,
    ListCatalogItemsParams, ListContractsParams, ListInvoicesParams,
    ListPurchaseOrdersParams, ListRequisitionsParams, ListSourcingEventsParams,
    ListSuppliersParams, NoParams,
    ListResourceParams, GetResourceParams, CreateResourceParams,
    UpdateResourceParams, DeleteResourceParams,
)

_SECRET_NAME = "ivalua_connections"


async def _load_connections(ctx) -> list[dict]:
    raw = await ctx.secrets.get(_SECRET_NAME)
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except (TypeError, ValueError):
        return []
    return data if isinstance(data, list) else []


async def _save_connections(ctx, connections: list[dict]) -> None:
    await ctx.secrets.set(_SECRET_NAME, json.dumps(connections))


def _connection_entity(connection: dict) -> IvaluaConnection:
    label = connection.get("label") or connection.get("tenant_url", "")
    return IvaluaConnection(
        id=connection.get("id", ""),
        title=label,
        label=label,
        tenant_url=connection.get("tenant_url", ""),
    )


async def _resolve_connection(ctx, connection_id: str) -> dict | None:
    connections = await _load_connections(ctx)
    if not connections:
        return None
    if connection_id:
        for connection in connections:
            if connection.get("id") == connection_id:
                return connection
        return None
    return connections[0]


async def _no_connection_error() -> ActionResult:
    return ActionResult.error(
        "No Ivalua tenant is connected yet. Use connect_ivalua first.",
        code="IVALUA_NOT_CONNECTED",
    )


def _client_from(connection: dict) -> ic.IvaluaClient:
    return ic.IvaluaClient(
        connection["tenant_url"], connection["client_id"], connection["client_secret"],
        api_path_prefix=connection.get("api_path_prefix", "/api/v1"),
    )


def _record(body: dict, id_key: str, title_keys: list[str]) -> IvaluaRecord:
    rid = str(body.get(id_key, ""))
    title = ""
    for key in title_keys:
        if body.get(key):
            title = str(body[key])
            break
    return IvaluaRecord(id=rid, title=title or rid, fields=body)


@chat.function("connect_ivalua", "Connect an Ivalua Source-to-Pay tenant (OAuth2 client credentials), after validating connectivity.", action_type="write", chain_callable=True, data_model=IvaluaConnection, event="ivalua-connector.connect_ivalua", effects=["ivalua.provider.connected"])
async def connect_ivalua(ctx, params: ConnectIvaluaParams) -> ActionResult:
    """Imperal action: connect_ivalua."""
    client = ic.IvaluaClient(
        params.tenant_url, params.client_id, params.client_secret,
        api_path_prefix=params.api_path_prefix,
    )
    try:
        await client.request("get", "/requisitions", params={"limit": 1})
    except ic.IvaluaError as exc:
        if "not licensed" not in str(exc).lower() and "not found" not in str(exc).lower():
            return ActionResult.error(str(exc), code="IVALUA_CONNECT_FAILED", retryable=exc.retryable)

    connections = await _load_connections(ctx)
    connection = {
        "id": str(uuid.uuid4()),
        "label": params.label.strip() or params.tenant_url,
        "tenant_url": client.tenant_url,
        "api_path_prefix": client.api_path_prefix,
        "client_id": params.client_id,
        "client_secret": params.client_secret,
    }
    connections.append(connection)
    await _save_connections(ctx, connections)
    return ActionResult.ok(_connection_entity(connection))


@chat.function("disconnect_ivalua", "Disconnect one Ivalua tenant: deletes only the credentials saved in Imperal. Nothing is changed in Ivalua.", action_type="write", chain_callable=True, data_model=DeleteResult, event="ivalua-connector.disconnect_ivalua", effects=["ivalua.provider.disconnected"])
async def disconnect_ivalua(ctx, params: DisconnectIvaluaParams) -> ActionResult:
    """Imperal action: disconnect_ivalua."""
    connections = await _load_connections(ctx)
    remaining = [c for c in connections if c.get("id") != params.connection_id]
    if len(remaining) == len(connections):
        return ActionResult.error("No connection found with that id.", code="IVALUA_CONNECTION_NOT_FOUND")
    await _save_connections(ctx, remaining)
    return ActionResult.ok(DeleteResult(deleted=True, id=params.connection_id))


@chat.function("list_connections", "List the connected Ivalua tenants.", action_type="read", chain_callable=True, data_model=ConnectionList, event="ivalua-connector.list_connections")
async def list_connections(ctx, params: NoParams) -> ActionResult:
    """Imperal action: list_connections."""
    connections = await _load_connections(ctx)
    items = [_connection_entity(c) for c in connections]
    return ActionResult.ok(ConnectionList(items=items, total=len(items)))


async def _list_resource(ctx, params, path: str, id_key: str, title_keys: list[str], extra_params: dict | None = None) -> ActionResult:
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    query = {"limit": params.top}
    if extra_params:
        query.update({k: v for k, v in extra_params.items() if v})
    try:
        body = await client.request("get", path, params=query)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc), code="IVALUA_REQUEST_FAILED", retryable=exc.retryable)
    items = ic.rest_items(body)
    records = [_record(item, id_key, title_keys) for item in items]
    return ActionResult.ok(IvaluaRecordList(items=records, total=len(records)))


async def _get_resource(ctx, params, path: str, id_key: str, title_keys: list[str]) -> ActionResult:
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    try:
        body = await client.request("get", path)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc), code="IVALUA_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.ok(_record(body, id_key, title_keys))


@chat.function("list_requisitions", "List Requisitions on the connected Ivalua tenant, optionally filtered by status.", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_requisitions")
async def list_requisitions(ctx, params: ListRequisitionsParams) -> ActionResult:
    """Imperal action: list_requisitions."""
    extra = {"status": params.status} if params.status else None
    return await _list_resource(ctx, params, "/requisitions", "id", ["justification", "name", "title"], extra)


@chat.function("get_requisition", "Read one Requisition in full by its unique identifier.", action_type="read", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.get_requisition")
async def get_requisition(ctx, params: GetRequisitionParams) -> ActionResult:
    """Imperal action: get_requisition."""
    return await _get_resource(ctx, params, f"/requisitions/{params.requisition_id}", "id", ["justification", "name", "title"])


@chat.function("create_requisition", "Create a new Requisition with line items.", action_type="write", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.create_requisition", effects=["ivalua.requisition.created"])
async def create_requisition(ctx, params: CreateRequisitionParams) -> ActionResult:
    """Imperal action: create_requisition."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    payload = {
        "justification": params.justification,
        "requested_by": {"email": params.requested_by_email},
        "lines": params.lines,
    }
    try:
        body = await client.request("post", "/requisitions", json_body=payload)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc), code="IVALUA_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.ok(_record(body, "id", ["justification", "name", "title"]))


@chat.function("list_purchase_orders", "List Purchase Orders, optionally filtered by supplier.", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_purchase_orders")
async def list_purchase_orders(ctx, params: ListPurchaseOrdersParams) -> ActionResult:
    """Imperal action: list_purchase_orders."""
    extra = {"supplier": params.supplier} if params.supplier else None
    return await _list_resource(ctx, params, "/purchase_orders", "id", ["po_number", "name", "title"], extra)


@chat.function("get_purchase_order", "Read one Purchase Order in full by its unique identifier.", action_type="read", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.get_purchase_order")
async def get_purchase_order(ctx, params: GetPurchaseOrderParams) -> ActionResult:
    """Imperal action: get_purchase_order."""
    return await _get_resource(ctx, params, f"/purchase_orders/{params.order_id}", "id", ["po_number", "name", "title"])


@chat.function("create_purchase_order", "Create a new Purchase Order with line items.", action_type="write", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.create_purchase_order", effects=["ivalua.purchase_order.created"])
async def create_purchase_order(ctx, params: CreatePurchaseOrderParams) -> ActionResult:
    """Imperal action: create_purchase_order."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    payload = {"supplier_id": params.supplier_id, "lines": params.lines}
    try:
        body = await client.request("post", "/purchase_orders", json_body=payload)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc), code="IVALUA_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.ok(_record(body, "id", ["po_number", "name", "title"]))


@chat.function("approve_purchase_order", "Approve/release a Purchase Order that is pending approval.", action_type="write", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.approve_purchase_order", effects=["ivalua.purchase_order.approved"])
async def approve_purchase_order(ctx, params: ApprovePurchaseOrderParams) -> ActionResult:
    """Imperal action: approve_purchase_order."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    try:
        body = await client.request("post", f"/purchase_orders/{params.order_id}/approve", json_body={})
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc), code="IVALUA_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.ok(_record(body, "id", ["po_number", "name", "title"]))


@chat.function("list_suppliers", "List Suppliers registered on this Ivalua tenant.", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_suppliers")
async def list_suppliers(ctx, params: ListSuppliersParams) -> ActionResult:
    """Imperal action: list_suppliers."""
    extra = {"name": params.query} if params.query else None
    return await _list_resource(ctx, params, "/suppliers", "id", ["name"], extra)


@chat.function("get_supplier", "Read one Supplier in full by its Supplier ID.", action_type="read", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.get_supplier")
async def get_supplier(ctx, params: GetSupplierParams) -> ActionResult:
    """Imperal action: get_supplier."""
    return await _get_resource(ctx, params, f"/suppliers/{params.supplier_id}", "id", ["name"])


@chat.function("create_supplier", "Create a new Supplier record (onboarding).", action_type="write", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.create_supplier", effects=["ivalua.supplier.created"])
async def create_supplier(ctx, params: CreateSupplierParams) -> ActionResult:
    """Imperal action: create_supplier."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    payload = {"name": params.name, "email": params.email, **params.fields}
    try:
        body = await client.request("post", "/suppliers", json_body=payload)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc), code="IVALUA_REQUEST_FAILED", retryable=exc.retryable)
    return ActionResult.ok(_record(body, "id", ["name"]))


@chat.function("list_invoices", "List Invoices, optionally filtered by status (including 3-way match status).", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_invoices")
async def list_invoices(ctx, params: ListInvoicesParams) -> ActionResult:
    """Imperal action: list_invoices."""
    extra = {"status": params.status} if params.status else None
    return await _list_resource(ctx, params, "/invoices", "id", ["invoice_number", "name", "title"], extra)


@chat.function("get_invoice", "Read one Invoice in full by its unique identifier.", action_type="read", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.get_invoice")
async def get_invoice(ctx, params: GetInvoiceParams) -> ActionResult:
    """Imperal action: get_invoice."""
    return await _get_resource(ctx, params, f"/invoices/{params.invoice_id}", "id", ["invoice_number", "name", "title"])


@chat.function("list_sourcing_events", "List Sourcing Events (RFQ/RFP/auction projects), optionally filtered by status.", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_sourcing_events")
async def list_sourcing_events(ctx, params: ListSourcingEventsParams) -> ActionResult:
    """Imperal action: list_sourcing_events."""
    extra = {"status": params.status} if params.status else None
    return await _list_resource(ctx, params, "/sourcing_events", "id", ["title", "name"], extra)


@chat.function("get_sourcing_event", "Read one Sourcing Event in full by its unique identifier.", action_type="read", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.get_sourcing_event")
async def get_sourcing_event(ctx, params: GetSourcingEventParams) -> ActionResult:
    """Imperal action: get_sourcing_event."""
    return await _get_resource(ctx, params, f"/sourcing_events/{params.event_id}", "id", ["title", "name"])


@chat.function("list_contracts", "List Contracts, optionally filtered by status.", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_contracts")
async def list_contracts(ctx, params: ListContractsParams) -> ActionResult:
    """Imperal action: list_contracts."""
    return await _list_resource(ctx, params, "/contracts", "id", ["name", "title"])


@chat.function("get_contract", "Read one Contract in full by its unique identifier.", action_type="read", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.get_contract")
async def get_contract(ctx, params: GetContractParams) -> ActionResult:
    """Imperal action: get_contract."""
    return await _get_resource(ctx, params, f"/contracts/{params.contract_id}", "id", ["name", "title"])


@chat.function("list_catalog_items", "List catalog items (punch-out/internal catalog), optionally filtered by name/SKU.", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_catalog_items")
async def list_catalog_items(ctx, params: ListCatalogItemsParams) -> ActionResult:
    """Imperal action: list_catalog_items."""
    extra = {"query": params.query} if params.query else None
    return await _list_resource(ctx, params, "/catalog_items", "id", ["name", "title"], extra)


@chat.function("audit_ivalua_access", "Probe every core Ivalua module (Requisitions, POs, Suppliers, Invoices, Sourcing Events, Contracts, Catalog Items) and report which are actually reachable for this tenant, without changing anything.", action_type="read", chain_callable=True, data_model=AccessAudit, event="ivalua-connector.audit_ivalua_access")
async def audit_ivalua_access(ctx, params: AuditAccessParams) -> ActionResult:
    """Imperal action: audit_ivalua_access."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    probes = [
        ("Requisitions", "/requisitions"),
        ("Purchase Orders", "/purchase_orders"),
        ("Suppliers", "/suppliers"),
        ("Invoices", "/invoices"),
        ("Sourcing Events", "/sourcing_events"),
        ("Contracts", "/contracts"),
        ("Catalog Items", "/catalog_items"),
    ]
    checks: list[Capability] = []
    for name, path in probes:
        try:
            await client.request("get", path, params={"limit": 1})
            checks.append(Capability(name=name, available=True, note="Reachable"))
        except ic.IvaluaError as exc:
            checks.append(Capability(name=name, available=False, note=str(exc)))
    available = sum(1 for c in checks if c.available)
    return ActionResult.ok(AccessAudit(
        tenant_url=connection.get("tenant_url", ""),
        capabilities=checks,
        checks=checks,
        available_count=available,
        unavailable_count=len(checks) - available,
    ))


def _generic_record(item: dict) -> IvaluaRecord:
    title = str(item.get("name") or item.get("title") or item.get("id") or "")
    return IvaluaRecord(id=str(item.get("id", "")), title=title, fields=item)


@chat.function("list_resource", "Generic REST passthrough: list records of any tenant-configured Ivalua resource path (e.g. 'purchase-orders', 'suppliers'). Use this when a typed function (list_purchase_orders etc.) does not match this tenant's own Ivalua Studio object model -- Ivalua is a no-code platform and object names/paths can be customised per tenant.", action_type="read", chain_callable=True, data_model=IvaluaRecordList, event="ivalua-connector.list_resource")
async def list_resource(ctx, params: ListResourceParams) -> ActionResult:
    """Imperal action: list_resource (generic passthrough)."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    try:
        items = await client.list_resource(params.resource_name, params={"limit": params.top})
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc))
    records = [_generic_record(item) for item in items]
    return ActionResult.ok(IvaluaRecordList(items=records, total=len(records)))


@chat.function("get_resource", "Generic REST passthrough: read one record of any tenant-configured Ivalua resource path by id. Use when a typed get_* function does not match this tenant's own object model.", action_type="read", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.get_resource")
async def get_resource(ctx, params: GetResourceParams) -> ActionResult:
    """Imperal action: get_resource (generic passthrough)."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    try:
        item = await client.get_resource(params.resource_name, params.record_id)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc))
    return ActionResult.ok(_generic_record(item))


@chat.function("create_resource", "Generic REST passthrough: create a record on any tenant-configured Ivalua resource path, using the tenant's own configured field names. Use when a typed create_* function does not match this tenant's own object model.", action_type="write", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.create_resource", effects=["ivalua.resource.created"])
async def create_resource(ctx, params: CreateResourceParams) -> ActionResult:
    """Imperal action: create_resource (generic passthrough)."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    try:
        item = await client.create_resource(params.resource_name, params.values)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc))
    return ActionResult.ok(_generic_record(item))


@chat.function("update_resource", "Generic REST passthrough: update selected fields of an existing record on any tenant-configured Ivalua resource path. Only given fields change.", action_type="write", chain_callable=True, data_model=IvaluaRecord, event="ivalua-connector.update_resource", effects=["ivalua.resource.updated"])
async def update_resource(ctx, params: UpdateResourceParams) -> ActionResult:
    """Imperal action: update_resource (generic passthrough)."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    try:
        item = await client.update_resource(params.resource_name, params.record_id, params.values)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc))
    return ActionResult.ok(_generic_record(item))


@chat.function("delete_resource", "Generic REST passthrough: permanently delete a record on any tenant-configured Ivalua resource path. Cannot be undone.", action_type="write", chain_callable=True, data_model=DeleteResult, event="ivalua-connector.delete_resource", effects=["ivalua.resource.deleted"])
async def delete_resource(ctx, params: DeleteResourceParams) -> ActionResult:
    """Imperal action: delete_resource (generic passthrough)."""
    connection = await _resolve_connection(ctx, params.connection_id)
    if not connection:
        return await _no_connection_error()
    client = _client_from(connection)
    try:
        await client.delete_resource(params.resource_name, params.record_id)
    except ic.IvaluaError as exc:
        return ActionResult.error(str(exc))
    return ActionResult.ok(DeleteResult(id=params.record_id, deleted=True))
