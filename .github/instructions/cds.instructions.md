---
description: "Use when working on the CDS Hooks backend: FastAPI app, CDS interop settings, per-hook Business Services/Processes/Operations, or CDS message classes under src/CDS."
applyTo: "src/CDS/**"
---

# CDS — CDS Hooks Backend

## What it is

The CDS backend implements the official [HL7 CDS Hooks specification](https://cds-hooks.hl7.org/)
on top of an IRIS for Health interoperability production, fronted by a FastAPI
app. It layers Epic-specific nuances/extensions (e.g. the `com.epic.cdshooks.*`
request extensions) on top of the vendor-neutral spec, so the same hook
endpoint works for Epic and any other CDS Hooks-compliant client.

Only these hooks are implemented so far:
- `/cds-services` — discovery endpoint (hardcoded `_SERVICES` list of available services).
- `/cds-services/patient-view` (+ `/feedback`)
- `/cds-services/order-select` (+ `/feedback`)
- `/cds-services/order-sign` (+ `/feedback`)

### Request flow

FastAPI router → Business Service → Business Process → Business Operation(s),
using the IRIS production message graph (see `interop/production.py`):

```text
BS.PatientView  → BP.PatientView  → BO.Fhir (prefetch fallback)
                                   → HapiRiskOperation (HTTP call to DSE namespace)
BS.OrderSelect  → BP.OrderSelect
BS.OrderSign    → BP.OrderSign
```

1. A router in `routers/` (e.g. `patient_view.py`) receives the CDS Hooks
   request body, typed via Pydantic models in `routers/contexts.py` and
   `routers/cds_hooks_models.py`.
2. It optionally parses Epic vendor extensions via `routers/epic_extensions.py`
   (`get_epic_extensions(body)` returns `None` for non-Epic callers — the
   endpoint stays vendor-neutral).
3. The router calls the corresponding Business Service (`get_bs()` in
   `interop/bs/*.py`), which wraps the hook input in an IOP message and calls
   `send_request_sync` into the production.
4. The Business Process (`interop/bp/*.py`) contains the hook-specific
   orchestration logic: resolving prefetch data, falling back to `BO.Fhir` for
   a live FHIR read when prefetch is missing, calling out to other Business
   Operations (e.g. `HapiRiskOperation` for HAC PI risk scoring — implemented
   by posting to the DSE namespace's HAPI endpoint over HTTP), and building the
   `CdsHookResponse` cards.
5. The response flows back up: BP → BS → router → FastAPI JSON response.

Decision-support computation (risk scoring, DMN rules) intentionally lives
outside CDS (e.g. in the DSE namespace) and is invoked over HTTP from the
Business Process — CDS stays focused on the CDS Hooks protocol and card
building, not the scoring logic itself.

## Project Map

`src/CDS/python/CDS/`:
- `app.py`: FastAPI entry point, loaded by IRIS WSGI.
- `routers/`: one router module per hook (`patient_view.py`, `order_select.py`,
  `order_sign.py`) plus `cds_services.py` (discovery), `cds_hooks_models.py`
  (spec-generic card/response models), `contexts.py` (hook context/input
  models shared with interop), `epic_extensions.py` (typed Epic vendor
  extensions, `get_epic_extensions()`).
- `fhir_client/`: pluggable FHIR HTTP client used by `BO.Fhir`
  (`base.py` interface, `requests_client.py` implementation).
- `interop/production.py`: IoP 4.0 Python `Production` object — the production topology (services → processes → operations).
- `interop/settings.py`: migration entrypoint, imports `prod` from `production.py`.
- `interop/bs/`: Business Services (one module per hook: `patient_view.py`, `order_select.py`, `order_sign.py`).
- `interop/bp/`: Business Processes (one module per hook: `patient_view.py`, `order_select.py`, `order_sign.py`).
- `interop/bo/`: Business Operations — `fhir.py` (`BO.Fhir`, live FHIR reads when prefetch is missing) and `hapi.py` (`HapiRiskOperation`, HTTP call to the DSE HAPI risk endpoint).
- `interop/msg/`: IOP PydanticMessage classes (`cds_hooks.py` for CDS hooks request/response messages).


## Migrate after changes

Whenever `interop/settings.py` or any file under `interop/bs/`, `interop/bp/`,
`interop/bo/`, `interop/msg/` changes, clear pycache and re-run migrate inside
the container (never on the host Mac — see root `AGENTS.md` for the general
IoP/Dev Environment rules):

```sh
docker-compose -f docker-compose.yml exec iris find /irisdev/app/src/CDS/python -type d -name __pycache__ -exec rm -rf {} +
docker-compose -f docker-compose.yml exec iris python3 -m iop --migrate /irisdev/app/src/CDS/python/CDS/interop/settings.py
```

## Verify production behavior

- production starts and reports running status
- logs show service/process/operation execution with no blocking errors
- Message Viewer shows expected CDS Hooks request/response flow
