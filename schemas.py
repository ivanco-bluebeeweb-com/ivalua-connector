"""Pydantic input contracts and SDL result entities for Ivalua Connector."""
from __future__ import annotations

from imperal_sdk import sdl
from pydantic import BaseModel, Field


class NoParams(BaseModel):
    pass


class ConnectionRefParams(BaseModel):
    connection_id: str = Field("", description="Optional saved Ivalua tenant connection ID. Omit to use the first connected tenant.")


class ConnectIvaluaParams(BaseModel):
    label: str = Field("", description="Friendly tenant label, e.g. 'Acme Production'.")
    tenant_url: str = Field(..., description="Ivalua tenant base URL, e.g. https://acme.ivalua.app.")
    api_path_prefix: str = Field("/api/v1", description="API path prefix for this tenant. Ivalua does not publish one universal path -- leave the default unless your Ivalua admin tells you otherwise.")
    client_id: str = Field(..., description="OAuth2 client ID issued by your Ivalua tenant administrator.")
    client_secret: str = Field(..., description="OAuth2 client secret for that client.")


class DisconnectIvaluaParams(ConnectionRefParams):
    connection_id: str = Field(..., description="Saved Ivalua tenant connection ID to remove from Imperal.")


class ListRequisitionsParams(ConnectionRefParams):
    status: str = Field("", description="Optional requisition status filter, e.g. approved, pending_approval.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetRequisitionParams(ConnectionRefParams):
    requisition_id: str = Field(..., description="Ivalua requisition unique identifier.")


class CreateRequisitionParams(ConnectionRefParams):
    justification: str = Field(..., description="Requisition justification/description.")
    requested_by_email: str = Field(..., description="Email of the Ivalua user this requisition is created for.")
    lines: list[dict] = Field(..., description="List of {description, quantity, price, need_by_date} line dicts.")


class ListPurchaseOrdersParams(ConnectionRefParams):
    supplier: str = Field("", description="Optional supplier name filter.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetPurchaseOrderParams(ConnectionRefParams):
    order_id: str = Field(..., description="Ivalua purchase order unique identifier.")


class CreatePurchaseOrderParams(ConnectionRefParams):
    supplier_id: str = Field(..., description="Ivalua supplier unique identifier this PO is issued to.")
    lines: list[dict] = Field(..., description="List of {description, quantity, price} line dicts.")


class ApprovePurchaseOrderParams(ConnectionRefParams):
    order_id: str = Field(..., description="Ivalua purchase order unique identifier to approve/release.")


class ListSuppliersParams(ConnectionRefParams):
    query: str = Field("", description="Optional supplier name search filter.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetSupplierParams(ConnectionRefParams):
    supplier_id: str = Field(..., description="Ivalua supplier unique identifier.")


class CreateSupplierParams(ConnectionRefParams):
    name: str = Field(..., description="Supplier legal name.")
    email: str = Field("", description="Supplier primary contact email.")
    fields: dict = Field(default_factory=dict, description="Additional tenant-specific supplier fields.")


class ListInvoicesParams(ConnectionRefParams):
    status: str = Field("", description="Optional invoice status filter, e.g. approved, disputed, matched, exception.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetInvoiceParams(ConnectionRefParams):
    invoice_id: str = Field(..., description="Ivalua invoice unique identifier.")


class ListSourcingEventsParams(ConnectionRefParams):
    status: str = Field("", description="Optional sourcing event status filter, e.g. open, closed, awarded.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetSourcingEventParams(ConnectionRefParams):
    event_id: str = Field(..., description="Ivalua sourcing/RFx event unique identifier.")


class ListContractsParams(ConnectionRefParams):
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetContractParams(ConnectionRefParams):
    contract_id: str = Field(..., description="Ivalua contract unique identifier.")


class ListCatalogItemsParams(ConnectionRefParams):
    query: str = Field("", description="Optional catalog item name/SKU search filter.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class AuditAccessParams(ConnectionRefParams):
    pass


class ListResourceParams(ConnectionRefParams):
    resource_name: str = Field(..., description="Tenant-configured Ivalua REST resource path, e.g. 'purchase-orders' or 'suppliers'. Use when a typed function (list_purchase_orders etc.) does not match this tenant's own Ivalua Studio object model.")
    top: int = Field(50, ge=1, le=200, description="Maximum records to return (1-200).")


class GetResourceParams(ConnectionRefParams):
    resource_name: str = Field(..., description="Tenant-configured Ivalua REST resource path.")
    record_id: str = Field(..., description="Record identifier within that resource.")


class CreateResourceParams(ConnectionRefParams):
    resource_name: str = Field(..., description="Tenant-configured Ivalua REST resource path.")
    values: dict = Field(..., description="Field values for the new record, in the tenant's own configured field names.")


class UpdateResourceParams(ConnectionRefParams):
    resource_name: str = Field(..., description="Tenant-configured Ivalua REST resource path.")
    record_id: str = Field(..., description="Record identifier within that resource.")
    values: dict = Field(..., description="Field values to change, in the tenant's own configured field names. Only given fields change.")


class DeleteResourceParams(ConnectionRefParams):
    resource_name: str = Field(..., description="Tenant-configured Ivalua REST resource path.")
    record_id: str = Field(..., description="Record identifier within that resource to delete.")


class IvaluaConnection(sdl.Entity):
    id: str
    title: str
    label: str
    tenant_url: str


class ConnectionList(sdl.Entity):
    items: list[IvaluaConnection] = Field(default_factory=list)
    total: int = 0


class IvaluaRecord(sdl.Entity):
    id: str
    title: str
    fields: dict = Field(default_factory=dict)


class IvaluaRecordList(sdl.Entity):
    items: list[IvaluaRecord] = Field(default_factory=list)
    total: int = 0


class Capability(sdl.Entity):
    name: str
    available: bool
    note: str


class AccessAudit(sdl.Entity):
    tenant_url: str
    capabilities: list[Capability] = Field(default_factory=list)
    available_count: int = 0
    unavailable_count: int = 0
    checks: list[Capability] = Field(default_factory=list)


class DeleteResult(sdl.Entity):
    deleted: bool
    id: str
