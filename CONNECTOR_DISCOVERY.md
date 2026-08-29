# Ivalua — Connector Discovery

**Discovery date:** 2026-08-29
**Release scope:** Tier 1 + Tier 2 (maximum coverage across licensed modules), per
standing instruction ("максимальный функционал, полный максимум" applied to every
new app).
**Decision owner:** Vlad — Procurement category build-out (5th and final app,
closing the category alongside SAP Ariba, Coupa, Oracle Procurement Cloud, Jaggaer).

## 1. Target service and official sources

Ivalua is a cloud (and on-premise-deployable) Source-to-Pay platform, deployed per
customer as an isolated tenant instance (customer-specific subdomain/base URL).
Ivalua describes its own integration surface as: "a REST API built on open
standards, supporting JSON and XML data formats via secure web services... The
Integration Hub supports 60+ ERP and enterprise system connectors" (source:
ivalua.com/technology/ivalua-open-ecosystem/, api-evangelist.com/ivalua index).

### Honesty gate — documentation availability (important difference vs. Coupa/Ariba)

Unlike Coupa (public Compass developer portal) or SAP Ariba (public developer
portal with OpenAPI specs), **Ivalua does not publish a public REST API reference
with concrete endpoint paths/schemas**. Its API surface, exact resource paths, and
authentication configuration screens are documented inside the customer's own
tenant admin console and partner-only integration documentation (gated behind an
active Ivalua contract) — confirmed by web research turning up marketing/ecosystem
pages and whitepapers, but no public Swagger/OpenAPI spec or endpoint list.

**Consequence for this connector:** exact resource paths (`/api/v6/purchase-orders`
vs `/rest/PurchaseOrder` etc.) are NOT hard-coded from a verified public spec.
Instead, following the same "configurable base + probe before assuming" pattern
already used for other self-hosted/enterprise-gated connectors in this portfolio
(Documentum, OpenText Content Server, Infor), the connector:
- Takes a fully configurable `base_url` (the tenant's own Ivalua instance URL) and
  a configurable `api_path_prefix` (default `/api/v1`, user-editable in Settings
  — since Ivalua's own docs describe versioned REST endpoints without a single
  universally-fixed public version number).
- Every resource call is wrapped so a 404/501 is treated as "endpoint not present
  on this tenant's configuration" (not a hard connector failure) — the same
  resilience pattern as `audit_ariba_access` / `audit_procurement_access`.
- `audit_ivalua_access` probes every configured resource path up front and reports
  exactly what responded, so a real customer's admin can correct `api_path_prefix`
  in Settings if their tenant uses a different convention.

This is the same honest, non-fabricating posture already applied to Infor ION
(tenant-routed paths) and Oracle HCM/SuccessFactors (tenant-approved resource
paths) elsewhere in this portfolio — no invented certainty where the public record
doesn't support it.

## 2. Auth model — OAuth2 client credentials, tenant-scoped

Ivalua's own security materials (Ivalua Data Security & Privacy whitepaper) and its
positioning as an enterprise SaaS platform confirm OAuth2-based API access is the
standard integration credential type for its REST web services, configured by the
tenant's Ivalua administrator. Required fields to connect:
- `base_url` — the customer's Ivalua tenant base URL (e.g. `https://acme.ivalua.app`).
- `client_id` / `client_secret` — OAuth2 client credentials issued by the tenant's
  Ivalua administrator for API integration.
- `token_url` — configurable, defaulting to `{base_url}/oauth2/token` (the common
  OAuth2 client-credentials convention used across this portfolio's other
  enterprise SaaS connectors — SAP Ariba, Coupa — pending confirmation against
  the customer's actual tenant configuration screen).

Every connection is verified live at `connect_ivalua` time (a real token exchange
attempt), never assumed to work from configuration alone.

## 3. Module/resource scope decision (Tier 1 — this release)

Matches the task's named scope, each resource independently probed by
`audit_ivalua_access` before being assumed present:
- **Purchase Requisitions** — list/get/create
- **Purchase Orders** — list/get/create/approve
- **Suppliers** — list/get/create/update
- **Invoices** — list/get (3-way match status where exposed)
- **Sourcing/RFx events** — list/get
- **Contracts** — list/get
- **Catalogs** — list catalog items

## 4. Explicitly deferred (out of Tier 1 scope)

- Full Sourcing event bid-collection lifecycle (creating/scoring bids) — read-only
  in v1, matching how Sourcing is treated as a separate deeper module in Coupa/Ariba.
- Supplier onboarding questionnaire workflows — basic supplier read/write covered,
  full workflow orchestration deferred.
- EAI/ETL batch integration surface (Ivalua's own ETL tooling) — out of scope,
  this connector targets the REST web-services surface only.

## 5. Pagination and rate limits

Not publicly documented with a fixed number (consistent with the overall lack of a
public API reference). The connector treats HTTP 429 as retryable and paginates
defensively with a configurable page size, consistent with the portfolio-wide
retryable-429 fix (task #2359).

## 6. Reused portfolio pattern

Client-credentials OAuth2 + tenant base_url + per-resource capability probing is
the same architecture already proven in SAP Ariba Connector, Coupa Connector, and
Oracle Procurement Cloud Connector — Ivalua reuses this exact shape rather than
inventing a new one.
