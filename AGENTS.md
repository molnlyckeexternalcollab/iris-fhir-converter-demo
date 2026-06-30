# Agent Guide

This project is an IoP application. IoP means Interoperability On Python: a
Python-first way to build InterSystems IRIS and Health Connect interoperability
productions.

## Project Status

✅ **Refactored to IoP 4.0 best practices** (see [REFACTORING.md](REFACTORING.md))

Key improvements:
- Python `Production` object in `src/EAI/python/EAI/production.py`
- Typed message handlers with full docstrings
- Type annotations across all components
- Enhanced error handling and logging
- Proper package-qualified imports

### IoP 4.0 Breaking Changes (vs 3.x)

- **`grongier.pex` removed** — use `iop` package only. IRIS proxy classes are now `IOP.*`, not `Grongier.PEX.*`.
- **Lifecycle hooks renamed to snake_case**: `on_init`, `on_tear_down`, `on_message`, `on_process_input`, `on_poll`. CamelCase versions no longer exist.
- **Implementation modules moved**: private `iop._*` files are gone; use `iop.components`, `iop.messages`, `iop.migration`, `iop.production`, `iop.runtime`.
- **`Director` and `Utils` facades deprecated** (still work, scheduled for removal in v5): prefer `iop.runtime.director` functions.
- **`PollingBusinessService`** is now a first-class export from `iop`; use `on_poll()` instead of overriding `on_process_input()`.
- **`@handler(MessageType)`** is the explicit dispatch decorator for operations and processes.
- **`iop --migrate --dry-run`** / `--explain` now supported.

## Dev Environment

- The application runs inside a Docker container named `iris` (defined in `docker-compose.yml`).
- The source tree on the host is bind-mounted into the container at `/irisdev/app/`.
- The host path `/Users/8826/Developer/misc/iris-fhir-converter-demo/` maps to `/irisdev/app/` inside the container.
- **`iop --migrate` requires the IRIS Embedded Python runtime and must NOT be run on the host Mac.** Always run it via `docker-compose exec iris`.

### Workflow: after changing Python interop files (settings.py, bs/, bp/, bo/, msg/)

1. **Clear pycache inside the container** — stale `.pyc` files cause workers to load old bytecode:
   ```sh
   docker-compose -f docker-compose.yml exec iris find /irisdev/app/src/CDS/python -type d -name __pycache__ -exec rm -rf {} +
   ```

2. **Run `iop --migrate` inside the container:**

   For the CDS interop package (`src/CDS/python/CDS/interop`):
   ```sh
   docker-compose -f docker-compose.yml exec iris python3 -m iop --migrate /irisdev/app/src/CDS/python/CDS/interop/settings.py
   ```

   For the EAI interop package (`src/EAI/python/EAI/interop`):
   ```sh
   docker-compose -f docker-compose.yml exec iris python3 -m iop --migrate /irisdev/app/src/EAI/python/EAI/interop/settings.py
   ```

Run both steps together whenever `settings.py` or any interop package file changes.

## First Prompt Contract

Before major implementation, make sure the project goal is explicit. If any of
these details are missing, ask for them or infer only when the repository makes
the answer clear:

- Business goal:
- Inbound systems:
- Outbound systems:
- Data standards or protocols:
- Required routing or transformation behavior:
- Runtime constraints:
- Acceptance criteria:

## Read First

Before changing code, read:

- `README.md` for setup and project-specific workflow.
- `settings.py`, `production.py`, or `prod.py` for the IoP `Production` graph.
- the relevant IoP cookbook, if present in this repository.
- message definitions such as `messages.py` or `msg.py`.
- components such as `bs.py`, `bp.py`, `bo.py`, `services.py`, `processes.py`,
  or `operations.py`.
- existing tests, fixtures, and sample payloads.

If this project does not include local cookbooks, use the public IoP cookbooks:
<https://grongierisc.github.io/interoperability-embedded-python/cookbooks/>

## Project Map

Update this list for the local project:

**EAI package** (`src/EAI/python/EAI/`):
- `settings.py`: Migration entrypoint with `PRODUCTIONS = [prod]`.
- `production.py`: IoP 4.0 Python Production object with component topology.
- `msg.py`: Message dataclasses for the pipeline.
- `bp.py`: Business Processes (FhirConverterProcess, FhirMainProcess).
- `bo.py`: Business Operations (FhirConverterOperation, FhirHttpOperation, RandomRestOperation).
- `obj.py`: Data objects (PermissionObj).
- `utils.py`: Utility functions for filtering.

**CDS package** (`src/CDS/python/CDS/`):
- `app.py`: FastAPI entry point, loaded by IRIS WSGI.
- `routers/contexts.py`: Hook context/input models shared between routers and interop.
- `interop/settings.py`: `CLASSES` dict + `PRODUCTIONS` config for the CDS production.
- `interop/bs/`: Business Services (one module per hook: `patient_view.py`, `order_select.py`, `order_sign.py`, plus `hapi.py`).
- `interop/bp/`: Business Processes (one module per hook plus `hapi.py`).
- `interop/bo/`: Business Operations (`hapi.py`, `fhir.py`).
- `interop/msg/`: IOP PydanticMessage classes (`__init__.py` for HAPI, `cds_hooks.py` for CDS hooks).

## settings.py Import Rules

- Treat the directory containing `settings.py` as the project import root for
  migration.
- Import production graph, message, and component modules from paths reachable
  relative to `settings.py`.
- If `production.py` is next to `settings.py`, use
  `from production import prod`.
- If the application is packaged under a directory next to `settings.py`, use
  package imports such as `from myapp.production import prod`.
- Do not ask users to set `PYTHONPATH` to make migration imports work.
- Do not patch `os.environ["PYTHONPATH"]` or global `sys.path` in application
  code to hide import problems.
- Fix import errors by changing the project layout or import statements.

## IoP Rules

- Import from `iop`, not from `grongier.pex` — that package is removed in 4.0.
- IRIS proxy classes are `IOP.*`; do not reference `Grongier.PEX.*` in any ObjectScript or config.
- Prefer a Python `Production` object exported through `PRODUCTIONS`.
- Use `prod.service(...)`, `prod.process(...)`, `prod.operation(...)`, and
  `prod.connect(...)` to declare topology.
- Use `target()` on component classes for configurable outbound targets.
- Do not put component startup logic in `__init__()`. Use `on_init()`.
- Use `on_tear_down()` for cleanup when a component becomes inactive.
- Use `@dataclass` on regular `Message` classes. Do not decorate
  `PydanticMessage` classes with `@dataclass` — IOP raises `SerializationError`
  if combined.
- Use `PersistentMessage` only when IRIS needs a native persistent message body.
- Put new graph components in `PRODUCTIONS`; avoid raw `CLASSES` entries for
  components already declared in the production graph.
- Keep executable sample code behind `if __name__ == "__main__":` when it lives
  in a migration file.
- IOP message field naming convention: use `input` (not `request`) to match the
  `RiskAssessmentInputRequest.input` pattern.
- `Director.create_python_business_service(...)` must be called lazily (inside a
  `get_bs()` function), never at module import time — the IRIS portal imports all
  settings modules before any production starts.

## Dispatch Rules

- Use `on_message(self, request)` as a simple fallback handler.
- Use typed one-argument methods to route by message type, for example
  `submit_order(self, request: OrderRequest)`.
- Use `@handler(MessageType)` when the handler should be explicit or the type
  annotation is not enough.
- Duplicate `@handler` mappings for the same type emit a warning; the second
  handler is discarded.
- Avoid explicit `DISPATCH` entries in new code; treat them as legacy or
  advanced compatibility hooks.
- Avoid duplicate handlers for the same message type unless the intended
  precedence is clear.

## Production Design Rules

- A production is a message graph.
- Business Services are inbound entry points or triggers. They may be Python IoP
  services or native IRIS services.
- Business Processes orchestrate routing, decisions, transformations, and calls
  to downstream components.
- Business Operations isolate outbound side effects such as external APIs,
  database writes, files, TCP, HTTP, or FHIR endpoints.
- Components communicate through production messages and targets. Do not
  instantiate another production component or call its methods directly.

## Add-ons

Use add-ons only when the project needs them:

- Healthcare standards such as HL7v2 or FHIR:
  <https://grongierisc.github.io/interoperability-embedded-python/healthcare-ai-coding/>
- HL7v2 native input:
  <https://grongierisc.github.io/interoperability-embedded-python/cookbooks/hl7v2-native-input/>
- HL7v2 to FHIR with fhir-converter:
  <https://grongierisc.github.io/interoperability-embedded-python/cookbooks/hl7v2-to-fhir-with-fhir-converter/>
- FHIR submission with a Python client:
  <https://grongierisc.github.io/interoperability-embedded-python/cookbooks/fhir-submission-python-client/>

## Definition Of Done

A change is done when the fastest relevant checks pass and the expected
production behavior is observable. Adapt this list to the local project:

```bash
# Syntax check on the host
python -m py_compile src/EAI/python/EAI/*.py
python -m py_compile src/CDS/python/CDS/**/*.py

# Clear pycache and migrate inside the container (iop --migrate must NOT run on the host)
docker-compose -f docker-compose.yml exec iris find /irisdev/app/src/CDS/python -type d -name __pycache__ -exec rm -rf {} +
docker-compose -f docker-compose.yml exec iris python3 -m iop --migrate /irisdev/app/src/CDS/python/CDS/interop/settings.py
docker-compose -f docker-compose.yml exec iris python3 -m iop --migrate /irisdev/app/src/EAI/python/EAI/interop/settings.py

# Rebuild if Dockerfile or dependencies changed
docker compose up --build
```

Do not use `iop --test` as the normal way to test Business Services. Test
services through the runtime director or production runtime API so the deployed
production context, component settings, and configured targets are used.

For production behavior, verify at least one of:

- production starts and reports running status
- HL7 files in `misc/data/input/` are processed and converted to FHIR
- FHIR resources are viewable in the embedded FHIR Server
- logs show service/process/operation execution with no blocking errors
- Message Viewer shows expected conversion flow

## Troubleshooting Prompts

When diagnosing a failure, report:

- exact command that failed
- traceback or IRIS error
- files read before changing code
- smallest suspected failure boundary: Python, migration, IRIS runtime,
  external dependency, or test data

## Expected AI Output

For every non-trivial change, include:

- updated files list
- short rationale for behavior change
- exact commands used to verify
- test results summary
- residual risk or follow-up items

