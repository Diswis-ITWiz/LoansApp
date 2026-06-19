# Handover Change List

This file lists the changes made to the application in a recommended application order, from easiest and lowest risk to hardest and highest risk. It is meant for another developer who may choose which changes to keep, skip, or reapply separately.

## Recommended Application Order

1. Very Easy: Documentation And Setup
2. Easy: Readability-Only Changes
3. Easy To Medium: Query Improvements
4. Medium: Pagination
5. Medium: Test Suite
6. Medium To Hard: Constants And Choices Centralization
7. Hard: Service Layer Extraction
8. Hardest: Database-State Safety

Tests are listed in the middle because they take some domain understanding to write correctly. In practice, apply or create tests before taking the harder service-layer and transaction-safety changes.

## 1. Very Easy: Documentation And Setup

These changes are low risk because they mostly affect setup instructions, local environment documentation, and project orientation.

- Added/updated `requirements.txt` with pinned direct dependencies.
- Added `.env.example` documenting required environment variables.
- Updated `startup.bat` to run from the project directory and use `.venv`.
- Added/updated `README.md` with setup, migration, run, and email-command instructions.
- Added `loans/test_settings.py` for SQLite-based test runs without local MySQL or `.env`.

Suggested verification:

- Confirm a new developer can identify required environment variables.
- Confirm setup commands in `README.md` match the intended deployment environment.
- Confirm `startup.bat` points to the correct project folder and virtual environment.

## 2. Easy: Readability-Only Changes

These changes improve code readability and admin usability without intentionally changing business behavior.

### Import Cleanup

- Removed wildcard imports under `base/`.
- Replaced them with explicit imports in views and management commands.
- Removed `base/helpers.py` after confirming production Python code no longer imports it.
- Removed service-level camelCase compatibility aliases after updating tests to use snake_case service functions.

### Type Hints

- Added type hints to the higher-value boundaries:
  - Service-layer functions.
  - View-service functions.
  - Django view function signatures.
  - Management command `handle` methods.
  - Model `__str__` methods.
- Form constructors and test method signatures were intentionally left mostly untouched to avoid low-value noise.

### Model Readability

- Added `__str__` methods to the core models:
  - `LoanItem`
  - `Client`
  - `Transaction`
  - `BlockOutDate`
  - `BlockOutTime`

### Django Admin

- Added `ModelAdmin` configurations in `base/admin.py`.
- Added list displays, filters, search fields, ordering, readonly fields, and transaction autocompletes.

Suggested verification:

- Run a syntax check.
- Open Django admin and confirm model lists still load.
- Confirm object labels are readable in dropdowns and list pages.

## 3. Easy To Medium: Query Improvements

These changes should preserve behavior while reducing avoidable database queries.

- Added `select_related` where templates or commands access related objects:
  - Client last borrowed item.
  - Transaction client.
  - Transaction item.
- Applied this in:
  - Views.
  - Client lookup services.
  - Return services.
  - Email management commands.
- Added stable ordering to querysets that are paginated or displayed in repeated lists.

Suggested verification:

- Open pages that list clients, items, transactions, overdue transactions, and penalized clients.
- Run the email management command tests if dependencies are available.
- Watch for any broken related-object access in templates.

## 4. Medium: Pagination

These changes are technically straightforward, but they change the user-facing behavior of long tables.

- Added shared pagination helper: `base/view_services/pagination.py`.
- Added shared pagination partial: `base/templates/base/_pagination.html`.
- Added pagination to:
  - Item panel.
  - Item detail transaction history.
  - Client panel.
  - Client detail transaction history.
  - Overdue transactions.
  - Penalized clients.
- Pagination preserves existing search/filter query parameters.
- Added pagination includes to list/history templates.

Suggested verification:

- Confirm page navigation appears when there is more than one page.
- Confirm search and filter parameters survive when moving to the next or previous page.
- Confirm short lists still display normally without unnecessary pagination controls.

## 5. Medium: Test Suite (OPTIONAL BUT RECOMMENDED FOR THE FUTURE) 

These changes do not change production behavior, but they require understanding the current business rules well enough to lock them down.

- Added `base/tests/__init__.py`.
- Added `base/tests/test_helpers.py` covering helper/domain behavior:
  - Calendar/no-class rules.
  - Closing time logic.
  - Item type classification.
  - Type A/Type B overdue calculations.
  - Penalty thresholds/application.
  - Email helper dispatch.
- Added `base/tests/test_management_commands.py` for the Type B overdue email command path.
- Added `base/tests/test_workflows.py` for loan, return, and report workflow state transitions.
- Added `loans/test_settings.py` for SQLite-based test runs without local MySQL or `.env`.

Suggested verification:

```powershell
python manage.py test --settings=loans.test_settings
```

## 6. Medium To Hard: Constants And Choices Centralization

This is conceptually simple but touches many files. The main risk is accidentally changing a persisted status/choice value used by the database.
- Added `base/constants.py`.
- Centralized:
  - Loan item statuses.
  - Transaction statuses.
  - Report choices.
  - Item prefixes/type names.
  - Office opening/closing times.
  - Blockout time bounds.
  - Penalty thresholds/fines/descriptions.
  - Penalty-lift choices.
- Updated models, forms, services, views, and some templates to use these constants instead of repeated literals.
- Updated templates to use centralized choices/context values:
  - Report item choices.
  - Penalty lift choices.
  - Blockout time values.

Suggested verification:

- Confirm database values such as `IS`, `LO`, `OG`, `C`, `DM`, and `L` did not change.
- Confirm forms still render the expected choices.
- Confirm report-item, penalty-lift, and blockout pages still submit expected values.

## 7. Hard: Service Layer And View-Service Extraction

This is high-value, but it touches the core workflows. It should be applied with tests around loaning, returning, reporting, overdue behavior, emails, and key admin list pages.

- Added `base/services/` modules:
  - `calendar_rules.py`: no-class day and closing-time rules.
  - `item_types.py`: item type classification/name lookup.
  - `overdue.py`: Type A and Type B overdue calculations.
  - `penalties.py`: penalty calculation/application/lifting.
  - `emailing.py`: transaction, deadline, overdue email helpers.
  - `loaning.py`: due-date calculation and loan creation.
  - `returns.py`: return assessment, overdue override, return completion.
  - `reporting.py`: damaged/lost item reporting.
  - `blockouts.py`: blockout date/time and finals-week helpers.
  - `clients.py`: loan/return client lookup context helpers.
- Added `base/view_services/` modules:
  - `pagination.py`: shared pagination helper.
  - `loan_transaction_views.py`: loan-item GET/POST request, form, context, transaction, and email orchestration.
  - `return_views.py`: return-item form selection, override authentication, submission, and context orchestration.
  - `item_panel.py`: item panel form creation and search/filter queryset handling.
  - `client_panel.py`: client panel search/filter queryset handling.
- Removed `base/helpers.py` after moving code to explicit service/view-service imports.
- Updated `base/views.py` to delegate business logic into services and page orchestration into view services.
- Cleaned management command imports.
- Preserved the existing Type B overdue email patch path for tests by keeping the alias import.

Suggested verification:

- Test the loan item workflow end to end.
- Test the return item workflow end to end for Type A and Type B items.
- Test reporting an item as damaged or lost.
- Test late transaction detail calculations.
- Test client lookup behavior for eligible, borrowing, blacklisted, temporarily blacklisted, and graduating-waiting clients.
- Test item panel create/search/filter behavior.
- Test client panel search/filter behavior.
- Test blockout date/time creation.
- Test reminder email commands in a safe environment.

## 8. Hardest: Database-State Safety

These changes have the highest correctness value, but they affect multi-model state transitions and concurrency behavior.

- Wrapped multi-model state updates in database transactions for:
  - Loan creation.
  - Return completion.
  - Damaged/lost item reporting.
- Fixed loan creation so `Client.lastBorrowedDate` records the actual submitted loan date instead of a stale/empty local value.
- Added row locking during return completion to avoid updating stale transaction/client/item state.

Suggested verification:

- Confirm loan creation updates `Transaction`, `Client`, and `LoanItem` together.
- Confirm return completion updates `Transaction`, `Client`, and `LoanItem` together.
- Confirm damaged/lost reporting updates `Client`, `LoanItem`, and active `Transaction` together.
- Check behavior when a transaction is submitted twice or when two users attempt related actions close together.

## Notes For Picking Changes

- Documentation/setup changes can be adopted independently.
- Readability-only changes are low risk and useful even if larger refactors are skipped.
- Query improvements can be adopted independently, but should be manually checked in templates.
- Pagination is user-facing and should be reviewed by the staff who use the app.
- Tests should ideally be added before applying service-layer and transaction-safety changes.
- Constants centralization should preserve existing database values exactly.
- Service extraction should be treated as a workflow refactor, not a cosmetic cleanup.
- `base/services/` should stay focused on business/domain rules.
- `base/view_services/` should hold Django request, form, context, pagination, and page orchestration helpers.
- Transaction-safety changes should be applied only after the core workflow tests are in place.

```powershell
python -m py_compile base\views.py base\view_services\client_panel.py base\view_services\item_panel.py base\view_services\loan_transaction_views.py base\view_services\return_views.py base\view_services\pagination.py
```
