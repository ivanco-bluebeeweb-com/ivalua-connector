# Ivalua Connector — идеальный первый запуск

Источник: `ONBOARDING_FIRST_LAUNCH_STANDARD.md`. Целевой пользователь: закупочный
аналитик, buyer, AP-клерк или category manager, впервые открывающий приложение.

## 1. Credential type
OAuth2 Client Credentials, tenant-scoped: базовый URL тенанта (например,
`https://acme.ivalua.app`) + client_id/client_secret, полученные у администратора
Ivalua тенанта. Дополнительно — редактируемый `api_path_prefix` (по умолчанию
`/api/v1`), так как Ivalua не публикует единый универсальный путь API (см.
`CONNECTOR_DISCOVERY.md` §1 — honesty gate).

## 2. Идеальный флоу (без ограничений SDK)
1. **Первое открытие** — простыми словами объяснить: "URL вашего Ivalua-тенанта,
   например https://acme.ivalua.app — так же, как вы заходите в Ivalua в браузере".
2. **Форма подключения** — base URL + OAuth client_id/client_secret + необязательный
   api_path_prefix (с подсказкой "оставьте по умолчанию, если не уверены — можно
   изменить позже, если запросы не находят нужные записи").
3. **После успеха** — сразу пробный вызов к каждому из семи модулей
   (Requisitions/POs/Suppliers/Invoices/Sourcing/Contracts/Catalogs) через
   `audit_ivalua_access` и явная карта "что отвечает для этого тенанта" — раз нет
   публичной спецификации API, никогда не предполагать, что путь угадан верно
   с первого раза.
4. **Живая сводка** — открытые requisitions на approval, PO pending approval,
   suppliers с неполным onboarding — сразу actionable, не пустой экран.
5. **Ошибка "path not found" (404/501)** — отдельное явное сообщение: "этот
   тенант, похоже, использует другой путь API — проверьте api_path_prefix в
   настройках", а не общая ошибка подключения.
6. **Multi-tenant** — если у консультанта несколько Ivalua-тенантов клиентов,
   явный переключатель между сохранёнными подключениями.
7. **Sourcing/onboarding предупреждение** — явно объяснить в help-диалоге, что
   полный bid-scoring workflow и supplier onboarding questionnaires не входят
   в это приложение (см. `CONNECTOR_DISCOVERY.md` §4).

## 3. Разница с реализацией сейчас
См. `UI_COMPONENT_PLAN.md` §0 — реализация показывает карту доступности модулей
как обычный список (DataTable/Badge), без специализированного визуального
виджета — такого примитива в SDK нет.
