# Ivalua Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `ivalua-connector`.

## 0. Разница с IDEAL_ONBOARDING.md
Идеал предполагает живую "карту доступности модулей" сразу при подключении.
Текущая реализация показывает это через `audit_ivalua_access` как обычный список
(`ui.DataTable`/Badge), без специализированного виджета — такого примитива в SDK нет
(тот же компромисс, что в Coupa/SAP Ariba/Oracle Procurement Cloud Connector).

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(direction="v", align="stretch") + `ui.Text`(tenant label) + `ui.Divider` + navigation `ui.ListItem`(Requisitions/Purchase Orders/Suppliers/Invoices/Sourcing/Contracts/Catalogs) + `ui.Button`("App settings") | Без карточек по стандарту, без дублирования инструкций из help-диалога. |
| Connect form (sidebar, not connected) | `ui.Form`(action="connect_ivalua", submit_label="Verify and connect") + labelled `ui.Input`(label="Tenant URL", placeholder="Например: https://acme.ivalua.app") + `ui.Input`(label="API path prefix (необязательно)", placeholder="/api/v1 — оставьте по умолчанию, если не уверены") + `ui.Input`(label="Client ID", placeholder="OAuth Client ID из настроек Ivalua") + `ui.Password`(label="Client Secret", placeholder="OAuth Client Secret") + `ui.Button`("Как получить эти данные?" → Dialog) | Форма растянута на всю ширину сайдбара, каждое поле — на всю ширину формы, у каждого поля лейбл и контекстный плейсхолдер — по UI_INTERFACE_STANDARD. |
| Requisition List (center, `center_overlay=True`) | `ui.Stats`(Total requisitions) + `ui.Input`(label="Фильтр по статусу", param_name="status", placeholder="Например: Approved, Pending Approval...") + `ui.DataTable`(id, title, status Badge, requester, total) | `DataTable` — основной обзор; `Input` для фильтра по статусу. |
| Purchase Order List | `ui.DataTable`(PO number, supplier, status Badge, total, currency) | Тот же паттерн, что requisitions — единообразие. |
| Supplier List | `ui.DataTable`(name, id, onboarding status Badge) | Быстрый обзор по поставщикам и статусу онбординга. |
| Invoice List | `ui.DataTable`(invoice number, supplier, match status Badge, amount, due date) | AP-клерку нужен match-статус и сумма на одном экране. |
| Sourcing Event List | `ui.DataTable`(title, status Badge, deadline, bid count) | Category manager видит активные RFx события. |
| Contract List | `ui.DataTable`(title, supplier, status Badge, end date) | Сроки контрактов сразу видны. |
| Catalog Item List | `ui.DataTable`(name, sku, supplier, price) | Обзор каталожных позиций. |
| Access audit (center overview) | `ui.Stats`(Available/Unavailable) + список Badge по модулям | Прозрачная карта доступности модулей для этого тенанта — без публичной спецификации API это единственный надёжный способ показать, что реально работает. |
| App settings (center) | `ui.Header` + список подключений + `ui.Button`("Disconnect", variant="danger") | Единственное место для disconnect — не дублируется в сайдбаре. |

## 2. Что НЕ строим (SDK-ограничения)
Нет отдельного примитива "module availability map" — заменяется DataTable/Badge
комбинацией, как в Coupa/SAP Ariba/Oracle Procurement Cloud Connector.

## 3. UI_INTERFACE_STANDARD — применено
- Все инпуты имеют `label`; плейсхолдеры контекстно соответствуют содержимому поля
  (не generic "Enter value").
- Контейнер формы подключения принудительно растянут на всю ширину левого
  сайдбара; поля внутри неё растянуты на всю ширину формы.
- Инструкция по кнопке "Как получить эти данные?" живёт только в модалке
  (Dialog) — в сайдбаре она не дублируется.
