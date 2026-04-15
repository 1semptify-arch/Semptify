# Module Compliance Realignment

## Purpose
This file documents the current module inventory, the compliance realignment performed, and the next actions needed to align the codebase with the latest compliance and privacy expectations.

## 1. Inventory of Actual App Modules
The current `app/modules/` directory contains the following production module files:

- `app/modules/tenant_defense.py`
- `app/modules/research_module.py`
- `app/modules/case_builder.py`
- `app/modules/complaint_wizard_module.py`
- `app/modules/document_converter.py`
- `app/modules/legal_filing_module.py`
- `app/modules/example_payment_tracking.py`

## 1.1 Router and Service Components Included
The compliance inventory now also includes routing and service components from:

- `app/routers/`
- `app/services/`

This means the inventory tracks both API-facing router modules and backend service components alongside the original `app/modules/` entries.

## 2. Documentation Reconciliation
The existing `CODEBASE_ASSESSMENT.md` section for modules was updated to reflect the actual module files and status.

## 3. Compliance Matrix Added
A compliance matrix was added to `CODEBASE_ASSESSMENT.md` documenting:

- privacy/compliance scope for each module
- evidence/integrity role for each module
- security controls and expectations
- next actions for review and alignment

## 4. Centralized Compliance Validation
A new shared compliance module was added at `app/core/compliance.py`.

### What it does
- records the current module compliance inventory
- validates production security settings when `SECURITY_MODE=enforced`
- warns if Semptify starts in `open` mode
- warns if a module inventory file is missing from disk

### Startup integration
`app/main.py` now calls `validate_app_compliance(app_settings)` during application creation.

## 5. Next Steps
- Review `app/core/compliance.py` and extend the inventory for additional modules as the module system grows.
- Add audit logging for all module_hub transitions and document handoff events.
- Confirm `legal_filing_module.py` and `complaint_wizard_module.py` do not persist sensitive data beyond session scope.
- Optionally add a dedicated `app/core/module_compliance.py` registry that can be referenced by runtime module loaders.
