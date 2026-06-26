
# iris-fhir-converter-demo

This project demonstrates an end-to-end HL7 v2 → FHIR pipeline using InterSystems IRIS for Health.
Incoming HL7 v2 messages (received over TCP or file) are converted into FHIR Bundles and stored in the embedded FHIR Server.

The conversion layer is built on top of — and extends — [chaseastewart/fhir-converter](https://github.com/chaseastewart/fhir-converter),
a Python port of [Microsoft's FHIR-Converter](https://github.com/microsoft/FHIR-Converter) (a C#/.NET utility that translates
legacy health formats — HL7v2, C-CDA, JSON — into FHIR R4 using Liquid templates).

## Table of Contents

- [iris-fhir-converter-demo](#iris-fhir-converter-demo)
  - [Table of Contents](#table-of-contents)
  - [Useful Links](#useful-links)
  - [Running the project](#running-the-project)
  - [FHIR Server](#fhir-server)
    - [How it is set up](#how-it-is-set-up)
  - [EAI Production](#eai-production)
    - [Architecture](#architecture)
      - [Conversion HL7 v2 → FHIR](#conversion-hl7-v2--fhir)
      - [FHIR storage](#fhir-storage)
      - [Key components](#key-components)
    - [Sending HL7 v2 messages](#sending-hl7-v2-messages)
      - [Via file drop](#via-file-drop)
      - [Via TCP](#via-tcp)
    - [Inspecting messages conversion in the Message Viewer](#inspecting-messages-conversion-in-the-message-viewer)
    - [Exploring the FHIR Server](#exploring-the-fhir-server)
      - [FHIR Dashboard](#fhir-dashboard)
      - [Querying the FHIR Server](#querying-the-fhir-server)
        - [curl](#curl)
        - [Bruno](#bruno)
  - [Environment variables principle and instructions](#environment-variables-principle-and-instructions)
    - [The three different mechanisms — easy to confuse](#the-three-different-mechanisms--easy-to-confuse)
    - [`env_file` vs `environment` precedence](#env_file-vs-environment-precedence)
    - [Why we don't use `env_file` in this project](#why-we-dont-use-env_file-in-this-project)
  - [The principle: validate at the boundary, trust within](#the-principle-validate-at-the-boundary-trust-within)
    - [What to do concretely](#what-to-do-concretely)
      - [Configuration: `.env` and `.env.example`](#configuration-env-and-envexample)
      - [docker-entrypoint.sh](#docker-entrypointsh)
      - [The exception: standalone scripts](#the-exception-standalone-scripts)
      - [Summary](#summary)
      - [APP\_HOME is special](#app_home-is-special)
  - [Python sys.path — how it all fits together](#python-syspath--how-it-all-fits-together)
    - [Source layout](#source-layout)
    - [1. PYTHONPATH — set in the Dockerfile](#1-pythonpath--set-in-the-dockerfile)
    - [2. IRIS WSGI (`WSGIAppLocation` + `iris_wsgi_interface.py`)](#2-iris-wsgi-wsgiapplocation--iris_wsgi_interfacepy)
    - [3. IRIS production worker (`iop --migrate` / `iop` interop)](#3-iris-production-worker-iop---migrate--iop-interop)
    - [Import rule summary](#import-rule-summary)
  - [License key file (if any)](#license-key-file-if-any)

## Useful Links

- [FHIR Dashboard](http://localhost:8081/csp/fhir-management/home)
- [EAI Production](http://localhost:8081/csp/healthshare/eai/EnsPortal.ProductionConfig.zen)

User name and password for both is `SuperUser` / `SYS`.

> **Note:** the management portal is served via the webgateway on port 8081, not the private web server on port 52773.
The latter is intentionally not published in this project since it's unused (community image has PWS but we don't use it, licensed image 2023.2+ has no PWS at all).

## Running the project

1. Make sure you have either [Docker Desktop](https://www.docker.com/products/docker-desktop/) or [Podman Desktop](https://podman-desktop.io/) installed and running.
2. Clone this repository.
3. Open a terminal and navigate to the root of the cloned repository.
4. Run the following command to build and start the Docker container:

    ```bash
    # Using Docker
    docker compose up --build
    # Or using Podman
    podman compose up --build
    ```

5. Wait for the container to start. This may take a few minutes as it needs to build the image and initialize the IRIS instance.
6. Once the container is running, you can access the FHIR Dashboard and EAI Production using the links provided above.
7. Copy HL7 v2 messages into the `input` folder. The EAI Production is configured to monitor this folder and will process any new files it finds, converting them to FHIR resources and storing them in the FHIR Server.

## FHIR Server

An FHIR R4 server is embedded directly in the IRIS for Health instance. It is provisioned at startup — no separate service is needed.

![FHIR Server Management](.github/images/screenshots/intersystems_iris_for_health_fhir_server_management.png)

### How it is set up

Provisioning runs inside [`initdb.d/iris.script`](initdb.d/iris.script) and is driven mostly by environment variables:

| Variable               | Purpose                                                          |
|------------------------|------------------------------------------------------------------|
| `FHIR_SERVER_ENABLE`   | Set to `1` to enable the server (skip if `0`)                    |
| `FHIR_SERVER_VERSION`  | FHIR version to install (e.g. `R4`)                              |
| `FHIR_SERVER_PATH`     | URL path under which the server is mounted (e.g. `/fhir/r4`)     |
| `FHIR_SERVER_STRATEGY` | Storage strategy class (e.g. `FHIR.Python.InteractionsStrategy`) |

The script:

1. Creates a dedicated `FHIRSERVER` namespace and installs the FHIR foundation packages into it.
2. Calls `HS.FHIRServer.Installer.InstallInstance` with the values above to mount the FHIR endpoint.
3. Registers a named HTTP service entry (`fhir`) in the IRIS service registry, pointing to the webgateway on port `8081` — this is the address the EAI production uses to POST converted resources.

See [Installing a New FHIR Server](https://docs.intersystems.com/irisforhealthlatest/csp/docbook/DocBook.UI.Page.cls?KEY=HXFHIRINS_server_install_new) for more details on the installation process and available configuration options.

The FHIR server is then reachable through the webgateway at:

```text
http://localhost:8081/fhir/r4
```

A management UI (FHIR Dashboard) is available at the link in [Useful Links](#useful-links).

## EAI Production

The EAI (Enterprise Application Integration) production is the orchestration layer that ties inbound HL7 v2 traffic to the FHIR server. It runs in its own `EAI` namespace and is started automatically at container initialisation.
> TODO: check that the production is set to auto-start.

### Architecture

> **Note:** Same architecture is shown in both standard and new UI screenshots.

#### Conversion HL7 v2 → FHIR

```text
┌─────────────────────────────────────────────────────────────────┐
│ EAI Production                                                  │
│                                                                 │
│  IRIS.HL7v2FileService   ─┐                                     │
│  (EnsLib.HL7.Service      ├──► Python.FhirConverterProcess      │
│   .FileService)           │    (bp.py)                          │
│                           │       │                             │
│  IRIS.HL7v2TCPService   ──┘       │ FhirConverterMessage        │
│  (EnsLib.HL7.Service              ▼                             │
│   .TCPService, :62115)     Python.FhirConverterOperation        │
│                            (bo.py — Hl7v2Renderer)              │
│                                   │                             │
│                                   │ FHIR Bundle (JSON)          │
│                                   ▼                             │
│                            FHIR_PYTHON_HTTP  ──► FHIR Server    │
│                            (FhirHttpOperation)   /fhir/r4       │
└─────────────────────────────────────────────────────────────────┘
```

![EAI Production standard UI](.github/images/screenshots/iris_fhir_converter_demo_eai_production_converter.gif)

#### FHIR storage

See [Accepting FHIR Requests](https://docs.intersystems.com/irisforhealth20261/csp/docbook/DocBook.UI.Page.cls?KEY=HXFHIRPROD_production#HXFHIRPROD_production_use).

```text
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  InteropService ──► FHIR_MAIN ──► FHIR_MAIN_HTTP                │
│  (FHIR proxy for       (FhirMainProcess)   (HS.FHIRServer       │
│   direct FHIR calls)                        .Interop            │
│                                             .HTTPOperation)     │
└─────────────────────────────────────────────────────────────────┘
```

![EAI Production standard UI](.github/images/screenshots/iris_fhir_converter_demo_eai_production_fhir_server.gif)

#### Key components

| Component                       | Class                                                     | Role                                                                                                                           |
|---------------------------------|-----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `IRIS.HL7v2FileService`         | `EnsLib.HL7.Service.FileService`                          | Watches `misc/data/input/` for `*.hl7` files; archives processed files to `misc/data/archive/`                                 |
| `IRIS.HL7v2TCPService`          | `EnsLib.HL7.Service.TCPService`                           | Listens on TCP port `62115` for inbound MLLP-framed HL7 v2 messages                                                            |
| `Python.FhirConverterProcess`   | `bp.FhirConverterProcess`                                 | Receives an HL7 message from either service, selects the right Liquid template, delegates conversion                           |
| `Python.FhirConverterOperation` | `bo.FhirConverterOperation`                               | Runs the `Hl7v2Renderer` from `fhir_converter` against the Liquid templates in `templates/`; returns a FHIR Bundle JSON string |
| `FHIR_PYTHON_HTTP`              | `bo.FhirHttpOperation`                                    | POSTs the resulting FHIR Bundle to `https://webgateway/fhir/r4`                                                                |
| `FHIR_MAIN` / `FHIR_MAIN_HTTP`  | `FhirMainProcess` / `HS.FHIRServer.Interop.HTTPOperation` | Handles direct FHIR requests arriving through the IRIS interop proxy                                                           |

The Liquid templates used for conversion live in the [`templates/`](templates/) directory and follow the same conventions as the Microsoft FHIR-Converter templates.

### Sending HL7 v2 messages

#### Via file drop

Place any `*.hl7` file in the `misc/data/input/` directory inside the container (or mount it as a volume). See samples in `misc/data/hl7v2`. The `IRIS.HL7v2FileService` polls that directory and picks up new files automatically.

Processed files are moved to `misc/data/archive/`.

#### Via TCP

Send an MLLP-framed HL7 v2 message to port `62115` using any MLLP-capable client. The `.vscode/extensions.json` actually includes an [HL7 extension](https://marketplace.visualstudio.com/items?itemName=pbrooks.hl7), which provides a convenient UI for sending test messages directly from VS Code:

![Send HL7 message over TCP right from VS Code](.github/images/screenshots/send_hl7_message_over_tcp_with_vs_code_extension.gif)

### Inspecting messages conversion in the Message Viewer

After sending both samples messages, open the [EAI Production](http://localhost:8081/csp/healthshare/eai/EnsPortal.ProductionConfig.zen) in your browser.

![Check TCP and file HL7 messages in Message Viewer](.github/images/screenshots/check_tcp_and_file_hl7_messages_in_viewer.gif)

Once a message has been processed, the resulting FHIR resources are stored in the embedded FHIR server and can be queried directly

### Exploring the FHIR Server

Sending the two sample HL7 v2 messages results in the creation of two Patient resources (amongst other related resources) in the FHIR server. You can query them using the FHIR API or explore them in the FHIR Dashboard.

#### FHIR Dashboard

![Check two patients in FHIR Server Management](.github/images/screenshots/check_two_patients_in_fhir_server_management.gif)

#### Querying the FHIR Server

##### curl

The FHIR server can also be queried directly using the API. For example, to count the patients, you can use `curl`:

```bash
➜  iris-fhir-converter-demo git:(main) ✗ curl --request GET \
  --url 'http://localhost:8081/fhir/r4/Patient?_summary=count' \
  --header 'authorization: Basic U3VwZXJVc2VyOlNZUw=='  | jq .
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100   223  100   223    0     0  14029      0 --:--:-- --:--:-- --:--:-- 14866
{
  "resourceType": "Bundle",
  "id": "b535281b-537b-11f1-9a0c-e2c9613486d7",
  "type": "searchset",
  "timestamp": "2026-05-19T12:10:21Z",
  "total": 2,
  "link": [
    {
      "relation": "self",
      "url": "http://localhost:8081/fhir/r4/Patient?_summary=count"
    }
  ]
}
```

##### Bruno

![Bruno collection](.github/images/screenshots/bruno_collection_get_patients_count.png)

## Environment variables principle and instructions

### The three different mechanisms — easy to confuse

| Mechanism                 | What it does                                                         |
|---------------------------|----------------------------------------------------------------------|
| .env at compose level     | Provides values for `${VAR}` substitution in docker-compose.yml only |
| `environment:` in compose | Explicitly injects specific vars into the container                  |
| `env_file:` in compose    | Injects **all** vars from a file directly into the container         |

### `env_file` vs `environment` precedence

**`environment` wins over `env_file`**, always — regardless of order in the file.

```yaml
env_file:
  - .env              # sets FHIR_SERVER_ENABLE=1

environment:
  - FHIR_SERVER_ENABLE=0   # this wins → container sees 0
```

Full precedence chain (highest to lowest):

1. `environment:` in docker-compose.yml
2. `env_file:` in docker-compose.yml
3. `ENV` in the Dockerfile

### Why we don't use `env_file` in this project

`env_file:` injects **all** vars from a file directly into the container, which looks convenient:

```yaml
services:
  iris:
    env_file:
      - .env   # would inject APP_HOME, FHIR_SERVER_*, etc. all at once
```

However, this project doesn't use it because `.env` contains `APP_HOME=/irisdev/app`, and injecting it via `env_file` would override the `ENV APP_HOME=...` baked into the image at build time — potentially pointing scripts at a path that doesn't exist in the container. The explicit `environment:` listing gives precise control over exactly which vars enter the container.

## The principle: validate at the boundary, trust within

`docker-entrypoint.sh` **is** the boundary — it's the first process that runs, it owns the environment, and everything else is downstream. The right approach:

```text
.env
  └─► docker-compose reads it to substitute ${VAR} placeholders in docker-compose.yml. Only vars explicitly listed under `environment:` are passed to the container.
        └─► docker-entrypoint.sh  ← validate EVERYTHING here, once
              ├─► init_iris.sh    ← trust the env, no re-checks
              └─► iris.script     ← trust the env, no re-checks
```

### What to do concretely

#### Configuration: `.env` and `.env.example`

`.env` is gitignored to prevent accidental credential leaks. A committed `.env.example` serves as the reference for what variables are required:

```bash
cp .env.example .env
# then edit .env if needed
```

Never commit `.env`. Never leave `.env.example` out of date.

#### docker-entrypoint.sh

Do all pre-flight in this script, before calling anything:

- **`_preflight_check()`** — validates that all required env vars (`APP_HOME`, `FHIR_SERVER_*`) are set and non-empty, and that `APP_HOME` points to an existing directory. Fails fast with a clear `[ FAIL ]` message.
- **`docker_setup_env()`** — calls `file_env` for IRIS credentials only (`IRIS_USERNAME`, `IRIS_PASSWORD`, `IRIS_NAMESPACE`, `IRIS_URI`). These use `file_env` because they support Docker secrets (value can come from a `_FILE` var pointing to a mounted secret file).

Note: `file_env` is **not** used for `FHIR_SERVER_*` vars — those are simple required strings with no secrets use case, so plain presence validation in `_preflight_check` is sufficient.

#### The exception: standalone scripts

Use guards in the scripts themselves only if they are intended to be run standalone, outside of the entrypoint context.
In that case, they should have a lightweight guard to ensure the necessary environment is set up, but they can skip the full pre-flight logic since it's only relevant for the entrypoint.

Example: `init_iris.sh` has a comment saying it can run standalone inside the container.

#### Summary

| Script               | Guards needed?                                                    |
|----------------------|-------------------------------------------------------------------|
| docker-entrypoint.sh | Yes — full pre-flight, single source of truth                     |
| init_iris.sh         | Optional minimal guard only if it needs to support standalone use |
| iris.script          | No — always called transitively from entrypoint                   |

#### APP_HOME is special

`APP_HOME` is set once in the Dockerfile via `ENV APP_HOME=/irisdev/app`. It controls **both** where files are placed during the image build (`COPY ... "${APP_HOME}/"`) and where runtime scripts look for those files.

Because the filesystem layout is physically baked into the image at build time, `APP_HOME` **cannot be changed at runtime** (e.g. via docker-compose or a Kubernetes pod spec) without rebuilding the image — doing so would cause all scripts to look for files at a path that does not exist in the container.

The only supported way to use a different path is to rebuild the image with a build argument:

```bash
docker build --build-arg APP_HOME=/your/custom/path .
```

The entrypoint will refuse to start if `APP_HOME` is unset or points to a non-existent directory.

Having the `ARG/ENV` combo in the Dockerfile allows building a differently-rooted image variant via `--build-arg APP_HOME=/custom/path`.
This is useful when a corporate policy mandates a specific directory structure, or when building a derivative image on top of this one.
But once built, the value is frozen — it cannot be changed without a rebuild.

> **Note:** A pre-commit hook (`scripts/check-app-home.sh`) enforces that `ARG APP_HOME=` in the Dockerfile and `APP_HOME=` in `.env.example` always match. Any commit touching either file will fail if the values differ.

| Condition                             | Before      | After      |
|---------------------------------------|-------------|------------|
| Dockerfile missing                    | skip (warn) | `[ FAIL ]` |
| .env.example missing                  | skip (warn) | `[ FAIL ]` |
| `ARG APP_HOME=` missing in Dockerfile | skip (warn) | `[ FAIL ]` |
| `APP_HOME=` missing in .env.example   | skip (warn) | `[ FAIL ]` |
| Values differ                         | `[ FAIL ]`  | `[ FAIL ]` |
| All good                              | `[  OK  ]`  | `[  OK  ]` |

## Python sys.path — how it all fits together

Understanding which directories end up on `sys.path` is critical for writing correct imports across three different Python contexts that IRIS creates: the WSGI worker, the production worker, and the `iop --migrate` command.

### Source layout

```text
src/
├── CDS
│   └── python
│       └── CDS                  ← the CDS Python package
│           ├── app.py           ← FastAPI entrypoint (loaded by IRIS WSGI)
│           ├── fhir_client/
│           ├── interop/
│           │   ├── bo/
│           │   ├── bp/
│           │   ├── bs/
│           │   └── msg/
│           └── routers/
└── EAI
    └── python
        └── EAI                  ← the EAI Python package
```

### 1. PYTHONPATH — set in the Dockerfile

```dockerfile
ENV PYTHONPATH="${APP_HOME}/src/CDS/python:${APP_HOME}/src/EAI/python"
```

This is the baseline that every Python process inside the container inherits.
It gives both the CDS and EAI packages the same root, so any import starting with `CDS.` or `EAI.` resolves correctly.

### 2. IRIS WSGI (`WSGIAppLocation` + `iris_wsgi_interface.py`)

The web application is declared in `initdb.d/merge.cpf`:

```text
CreateApplication:Name=/cds,
  WSGIAppLocation=/irisdev/app/src/CDS/python/CDS/,
  WSGIAppName=app,
  WSGICallable=app,
  ...
```

`iris_wsgi_interface.py` receives these three values as `app_path`, `module`, and `callable`:

```python
def get_from_module(module, app_path, callable, debug):
    # 1. Adds WSGIAppLocation to sys.path:
    sys.path.append(app_path)                                        # → .../CDS/
    sys.path.append(os.path.abspath(os.path.join(app_path, os.pardir)))  # → .../src/CDS/python/

    # 2. Imports WSGIAppName as a top-level module (not CDS.app):
    module_obj = importlib.import_module(module)                     # import_module('app')

    # 3. Returns WSGICallable from it (the FastAPI instance):
    return getattr(module_obj, callable)                             # app.app
```

Consequence for `sys.path` in the WSGI worker:

| Entry added by            | Path                                                 |
|---------------------------|------------------------------------------------------|
| `PYTHONPATH` (Dockerfile) | `/irisdev/app/src/CDS/python`                        |
| `PYTHONPATH` (Dockerfile) | `/irisdev/app/src/EAI/python`                        |
| WSGI (app_path)           | `/irisdev/app/src/CDS/python/CDS/`                   |
| WSGI (parent of app_path) | `/irisdev/app/src/CDS/python/` (duplicate, harmless) |

Both `CDS/` and `src/CDS/python/` are on `sys.path` before `app.py` is even imported.  This means **both** `from routers.X import` and `from CDS.routers.X import` would technically resolve.

**We always use `CDS.*`** — this is the canonical import path that is consistent with how the IRIS production worker resolves the same modules (see below).  Using bare `from routers.X import` in `app.py` would register the class under a different key in `sys.modules`, causing Pydantic class identity failures when the same class is compared across the WSGI and production contexts.

Note that `app.py` is imported as the module `app` (not `CDS.app`) — which means **relative imports** (`from . import`) do not work inside it.  Use `CDS.*` absolute imports instead.

### 3. IRIS production worker (`iop --migrate` / `iop` interop)

When an interop production starts, `iop` loads `settings.py` and registers the production classes.  `iop` adds a path entry of its own — the directory containing the settings file:

```text
/irisdev/app/src/CDS/python/CDS/interop/   ← added by iop when loading settings.py
```

Combined with the `PYTHONPATH` baseline, the production worker sys.path is:

| Entry              | Path                                       |
|--------------------|--------------------------------------------|
| `PYTHONPATH`       | `/irisdev/app/src/CDS/python`              |
| `PYTHONPATH`       | `/irisdev/app/src/EAI/python`              |
| iop (settings dir) | `/irisdev/app/src/CDS/python/CDS/interop/` |

Notice that `/irisdev/app/src/CDS/python/CDS/` (the bare `CDS/` directory) is **not** added by iop.  So bare imports like `from routers.X import` or `from models import` would fail with `ModuleNotFoundError`.  Only `CDS.*` imports work here.

`iop --migrate` operates in this same context — running it inside the container is mandatory:

```bash
docker-compose exec iris python3 -m iop --migrate /irisdev/app/src/CDS/python/CDS/interop/settings.py
```

Running it on the host Mac fails because the host environment does not have the IRIS Python runtime or the same `sys.path` setup.

### Import rule summary

| Module location        | Loaded by                     | Must use                                                 |
|------------------------|-------------------------------|----------------------------------------------------------|
| `CDS/app.py`           | WSGI (as `app`)               | `CDS.*` absolute imports                                 |
| `CDS/routers/*.py`     | WSGI (via `app`)              | relative `.` imports within routers, `CDS.*` for interop |
| `CDS/interop/bs/*.py`  | WSGI (via routers `get_bs()`) | `CDS.*`                                                  |
| `CDS/interop/msg/*.py` | both WSGI and production      | `CDS.*` (safe because `src/CDS/python` is on both paths) |
| `CDS/interop/bp/*.py`  | production only               | `CDS.*`                                                  |
| `CDS/interop/bo/*.py`  | production only               | `CDS.*`                                                  |

## License key file (if any)

Put your InterSystems IRIS license key file in the `key` folder with the name format `iris.<arch>.key` (e.g. `iris.x86_64.key` or `iris.aarch64.key`) before building the image.
The Dockerfile will copy it to the correct location in the image with the name `iris.key` so that IRIS can find it at runtime.

> **Note:** the community edition of IRIS for Health does not require a license key file, so this step is only necessary if you are using a licensed edition. Using a licensed key with a community image will show a similar message:
>
> ```bash
> [INFO] Starting InterSystems IRIS instance IRIS...
> [INFO] log: 05/18/26-12:36:40:499 (410) 2 [Generic.Event] This version of InterSystems IRIS will only accept a Community license key, iris.key will be ignored.
> ```

See [Managing InterSystems IRIS Licensing](https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GSA_LICENSE).

