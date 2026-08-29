# Ivalua Connector — Preparation

**Version:** 0.1.0 (planning)
**Date:** 2026-08-29
**Product owner:** Vlad / Bluebeeweb
**Related delivery task:** BBW Imperal Apps #2818 — `[App Development] Ivalua Connector`
**Scope decision:** maximum feasible capability through the tenant's configured
REST web-services surface (per standing "максимальный функционал" instruction).

## 1. App passport

**Name:** Ivalua Connector
**One-line purpose:** Connect an organization's own Ivalua Source-to-Pay tenant to
read and safely manage Purchase Requisitions, Purchase Orders, Suppliers,
Invoices, Sourcing/RFx events, Contracts, and Catalogs through Ivalua's REST web
services.

**Why now:** Ivalua is a Gartner Leader in the 2024/2025 Magic Quadrant for
Source-to-Pay Suites — a flexible, highly-configurable no-code platform favored
by large manufacturers for deep process customization. It is the 5th and final
app closing the Procurement/Source-to-Pay category alongside SAP Ariba, Coupa,
Oracle Procurement Cloud, and Jaggaer.

**What it is not:**
- Not a replacement for Ivalua's own approval workflow/BPM engine.
- Does not implement full Sourcing bid-collection/scoring lifecycle (read-only
  in v1 — see `CONNECTOR_DISCOVERY.md` §4).
- Does not assume any resource path is correct for a given tenant until a real
  response confirms it — Ivalua publishes no public API reference, so every
  endpoint is treated as tenant-configurable and probed, not hard-assumed.

## 2. Human problem

> A procurement analyst, buyer, or AP clerk needs to check a requisition's
> status, look up a purchase order or supplier record, review an invoice's match
> status, or see open sourcing events — without opening Ivalua's own multi-tab
> configurable UI.

### Personas and high-value moments
| Persona | Trigger | Value |
|---|---|---|
| Procurement analyst | Needs requisition/PO status | Track approvals in plain language |
| Buyer | Needs to raise a new PO/requisition | Create without switching to Ivalua's UI |
| AP clerk | Needs invoice match status | See match exceptions without hunting tabs |
| Category manager | Needs supplier/contract lookup | See who's contracted and on what terms |
| Sourcing manager | Needs open RFx/sourcing event status | Quick visibility into active events |

## 3. Scope (Tier 1 + Tier 2)

- `connect_ivalua` / `disconnect_ivalua` / `list_connections` — OAuth2 client
  credentials, tenant-scoped (configurable `base_url` + `api_path_prefix`),
  multi-tenant support.
- `list_requisitions` / `get_requisition` / `create_requisition`
- `list_purchase_orders` / `get_purchase_order` / `create_purchase_order` / `approve_purchase_order`
- `list_suppliers` / `get_supplier` / `create_supplier` / `update_supplier`
- `list_invoices` / `get_invoice`
- `list_sourcing_events` / `get_sourcing_event`
- `list_contracts` / `get_contract`
- `list_catalog_items`
- `audit_ivalua_access` — capability probe across every configured resource path.

## 4. Non-goals (this release)

- Sourcing bid collection/scoring workflow (read-only event/bid visibility only).
- Supplier onboarding questionnaire orchestration (basic supplier CRUD only).
- Ivalua's own EAI/ETL batch tooling (REST web services surface only).

## 5. Security

- `client_id`/`client_secret` stored via `ext.secret(...)`, `write_mode="both"`,
  rotation hint 90 days — same pattern as every other OAuth2 client-credentials
  connector in this portfolio.
- `base_url`/`api_path_prefix` stored alongside connection metadata (not secret),
  editable per-tenant in Settings, since Ivalua exposes no fixed universal path.
- No secret values ever echoed back in list/get responses.

## 6. Process gates (mandatory before code)

1. ✅ CONNECTOR_DISCOVERY.md — done.
2. ✅ PREPARATION.md — this file.
3. ⬜ IDEAL_ONBOARDING.md + UI_COMPONENT_PLAN.md (per ONBOARDING_FIRST_LAUNCH_STANDARD.md) — next, before panels.py.
4. ⬜ schemas.py / ivalua_client.py / handlers_*.py / panels.py / panels_settings.py / main.py.
5. ⬜ Pricing (mandatory before submit_for_review, per standing rule).
6. ⬜ validate / build / deploy / submit_for_review.
