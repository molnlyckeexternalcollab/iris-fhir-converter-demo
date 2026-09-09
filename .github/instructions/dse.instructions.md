---
description: "Use when working on the DSE namespace: the EHR Navigator Agent (agent.py LangGraph pipeline, FastAPI routers, SSE streaming, static React/GSAP frontend), the HAPI risk calculator (interop production, hapi_calculator.py), Synthea synthetic test data under src/DSE/synthea, or DSE deployment/env vars."
applyTo: "src/DSE/**"
---

# DSE — Decision Support Engine

## What it is

DSE (Decision Support Engine) is the namespace where clinical decision-support
logic apps live, alongside the EAI HL7v2→FHIR pipeline and the CDS Hooks
backend. Just like CDS, it is built on top of an IRIS for Health
interoperability production (`interop/production.py`), with one or more
FastAPI sub-backends fronting parts of that production. Not every sub-backend
has a browser frontend — the EHR Navigator Agent does, the HAPI risk
calculator doesn't (it's a pure JSON API, consumed by the CDS production over
HTTP — see `cds.instructions.md` → `HapiRiskOperation`).

Two independent capabilities currently live under DSE:

1. **EHR Navigator Agent** — a LangGraph AI agent with a browser UI, heavily
   inspired by Google's MedGemma reference demo, that lets a clinician ask
   natural-language questions about a patient and navigates the FHIR store to
   answer them.
2. **HAPI risk calculator** — a stateless logistic-regression scoring endpoint
   for Hospital-Acquired Pressure Injury (HAC PI) risk, fronted by the IRIS
   production (`BS.Hapi → BP.Hapi`) and (optionally) a FastAPI router.

## Package layout

```text
src/DSE/python/DSE/
├── agent.py            # Core LangGraph agent — adapted from the MedGemma notebook
├── hapi_calculator.py  # Reese et al. (2024) logistic regression HAC PI risk model
├── models.py           # RiskAssessmentInput / RiskCalculationResult Pydantic models
├── app.py              # FastAPI application entry point (IRIS WSGI + uvicorn dev)
├── routers/
│   ├── agent.py        # /agent/* endpoints: SSE stream, questions list, index HTML
│   └── hapi.py         # /hapi endpoint — thin wrapper calling BS.Hapi
├── interop/            # IoP production for the HAPI calculator
│   ├── production.py   # BS.Hapi → BP.Hapi topology
│   ├── settings.py     # migration entrypoint
│   ├── bs/hapi.py      # Business Service — wraps input, calls BP.Hapi
│   ├── bp/hapi.py      # Business Process — calls hapi_calculator.calculate_risk()
│   └── msg/            # RiskAssessmentInputRequest / RiskAssessmentResultResponse
└── static/agent/       # Frontend static files (React + GSAP, no build step)
    ├── index.html      # Entry point — loads React/Babel/GSAP/markdown-it from CDN
    ├── script.js       # Main React app + SSE event queue + animation state
    ├── arrow.js        # GSAP animated arrow component
    ├── dialog.js       # "Details about this Demo" modal
    └── style.css
```

Note: `app.py` currently has `DSE.routers.hapi` (and its `app.include_router`
call) commented out — only the agent router is mounted. Uncomment both lines
if you need to exercise `/hapi` directly through FastAPI/uvicorn; the IRIS
production path (`BS.Hapi` called directly via `Director`, e.g. from CDS's
`HapiRiskOperation`) is unaffected by that FastAPI router being disabled.

## HAPI risk calculator

`hapi_calculator.py` implements the Reese et al. (2024) validated logistic
regression model for HAC PI (Hospital-Acquired Pressure Injury) risk — a
stateless scoring function taking demographics, clinical measurements, Braden
Scale sub-scores, devices, and conditions as input. Only `age` is required;
every other field has a documented model default.

For the model math (coefficients, Z-score formula), the full input field
reference, and links to the clinical/LOINC/SNOMED reference docs, see
[src/DSE/python/DSE/README.md](../../src/DSE/python/DSE/README.md).

### Request flow

FastAPI router (or any other HTTP caller) → Business Service → Business
Process → scoring function, using the IRIS production message graph (see
`interop/production.py`):

```text
routers/hapi.py  → BS.Hapi → BP.Hapi → hapi_calculator.calculate_risk()
```

Any other caller (e.g. CDS's `HapiRiskOperation`) hits the same `/hapi`
endpoint over HTTP — see `cds.instructions.md` → Request flow.

1. `routers/hapi.py` receives `RiskAssessmentInput` and calls `BS.Hapi` via
   `get_bs().on_process_input(body)`.
2. `BS.Hapi` (`interop/bs/hapi.py`) wraps it in a `RiskAssessmentInputRequest`
   IOP message and calls `send_request_sync` into the production.
3. `BP.Hapi` (`interop/bp/hapi.py`) is a thin adapter — it just calls
   `hapi_calculator.calculate_risk()`. All scoring logic lives in
   `hapi_calculator.py`, not in the production component.
4. The response flows back up: BP → BS → router → FastAPI JSON response.

### Synthetic test data for the HAPI calculator

`src/DSE/synthea/` contains custom Synthea modules (lab observations, Braden
Scale-relevant conditions, devices) that generate patients exercising the HAPI
model's inputs. These modules are authored and maintained using the
[synthea-module-author](../../skills/synthea-module-author/synthea-module-author.md)
skill — use that skill (not ad-hoc JSON edits) whenever a module needs to be
created or extended, since it grounds every SNOMED/LOINC/RxNorm code against a
real terminology server instead of relying on training-data recall.

## Agent pipeline

`agent.py` implements a five-node LangGraph graph (2 sequential LLM calls total):

```text
call_manifest_tool
      │   Parallel-scans all 12 FHIR resource types (ThreadPoolExecutor).
      │   Also fetches Patient demographics directly.
      │   Emits task_id/status events for each parallel scan so the UI
      │   can show per-resource elapsed timers.
      ▼
identify_relevant_resource_types   ← LLM call 1
      │   LLM picks which resource types answer the question (max_tokens=200).
      ▼
select_data_to_retrieve
      │   Builds FHIR API call list without LLM — resource types already known.
      ▼
execute_data_retrieval
      │   Parallel-fetches selected resource types (ThreadPoolExecutor).
      │   Emits task_id/status events for each parallel fetch.
      │   If total data exceeds LLM_CONTEXT_TOKENS budget, summarizes the
      │   largest resources first with extra LLM calls (rare).
      ▼
get_final_answer                   ← LLM call 2
          LLM synthesises all facts into the final markdown answer (max_tokens=2000).
```

The two sequential LLM calls never overlap. Seeing two active counters in LM
Studio simultaneously indicates a second concurrent browser request.

**Key difference vs the notebook:**
In the notebook, step 3 uses the LLM to generate tool calls with specific
`filter_code` values selected from the manifest. In `agent.py` step 3 is
deterministic: it builds calls for all relevant resource types without filter
codes. This trades recall precision for reliability and removes a 3rd LLM call.

## How `emit` works (SSE bridge)

`agent.py` takes a `Callable[[dict], None]` argument called `emit` at build
time. Every node calls `emit({"destination": "FHIR"|"LLM"|None, "request":
bool, "event": str, "data": ..., "final": bool})` to signal progress.

`routers/agent.py` creates an `asyncio.Queue`, runs the synchronous agent in a
`threading.Thread`, and bridges events via `asyncio.run_coroutine_threadsafe`.
`StreamingResponse` with `media_type="text/event-stream"` turns these into SSE.

## Frontend

The frontend is vanilla React loaded from CDN (no build step, no npm).
`script.js` uses `EventSource` to consume the SSE stream and drives an
animated diagram — arrows from the clinician icon to FHIR store and to MedGemma
icon, with GSAP-powered motion path animations.

An event queue with configurable delays (`SPEED = 0.33`) decouples visual
animation timing from network arrival so the diagram animates smoothly even if
the backend sends bursts.

Predefined questions come from `GET /agent/questions` (served from `QUESTIONS`
in `agent.py`). A free-text textarea lets the clinician ask custom questions.
Patient ID is an editable field; default is `3887` (Beer512).

## Production deployment (Docker)

```text
Browser
  │
  └── Apache + InterSystems Web Gateway (port 8081)
        │
        ├── /dse/agent/static/*  ── served directly by Apache
        │   (Alias in CSP.conf → /var/www/dse-agent-static, CSP Off)
        │   (docker-compose volume: ./src/DSE/python/DSE/static/agent → /var/www/dse-agent-static)
        │
        └── /dse/agent/*  ── CSP On → IRIS WSGI → a2wsgi → FastAPI
              /agent/           (FastAPI router prefix)
              /agent/questions
              /agent/run_agent  ← SSE stream
```

`index.html` contains `<base href="/dse/agent/">` so relative URLs in the
React app (`fetch('questions')`, `new URL(url, document.baseURI)`) resolve
correctly under this path prefix.

## SSE + WSGI known issue

IRIS WSGI wraps the ASGI FastAPI app via `a2wsgi`. Streaming responses (SSE)
over WSGI require chunked transfer support from the gateway. Apache / the Web
Gateway may buffer chunks, causing the frontend to receive all events at once
at the end instead of incrementally. Mitigation headers are already set:

```text
Cache-Control: no-cache
X-Accel-Buffering: no
```

If events arrive batched, the frontend handles this gracefully: it detects a
`final` event already queued and drains remaining events with a 50 ms delay
instead of the normal animation delay.

## Local development (without Docker)

**Backend** — run uvicorn directly (already wired at the bottom of `app.py`):

```bash
cd src/DSE/python
pip install fastapi uvicorn langchain langchain-openai langgraph requests
PYTHONPATH=. python -m DSE.app
# FastAPI available at http://localhost:8002
```

Routes served by uvicorn:

- `http://localhost:8002/agent/`          → index.html
- `http://localhost:8002/agent/questions` → question list
- `http://localhost:8002/agent/run_agent` → SSE stream

**Static files — base href mismatch:**
`index.html` has `<base href="/dse/agent/">` which matches the production
Apache path. When running under uvicorn alone, the router serves the app at
`/agent/` so the base href causes relative requests (`questions`, `run_agent`)
to resolve to `/dse/agent/questions` — a path uvicorn doesn't know.

For local debugging, either:

1. Temporarily change `<base href="/dse/agent/">` to `<base href="/agent/">`
   in `index.html` (revert before committing), **or**
2. Serve via a simple reverse proxy (e.g. caddy) that rewrites `/dse/` → `/`.

**Frontend only** (if you only need to iterate on HTML/CSS/JS without the agent):

```bash
cd src/DSE/python/DSE/static/agent
python3 -m http.server 8080
# Open http://localhost:8080/index.html
# API calls will fail (no backend) but layout/animation can be checked
```

## Environment variables

| Variable             | Default                            | Purpose                          |
|----------------------|------------------------------------|----------------------------------|
| `FHIR_STORE_URL`     | `http://4.210.90.115:8081/fhir/r4` | FHIR R4 endpoint                 |
| `FHIR_USER`          | `SuperUser`                        | FHIR basic-auth username         |
| `FHIR_PASSWORD`      | `SYS`                              | FHIR basic-auth password         |
| `LM_STUDIO_BASE_URL` | `http://localhost:1234/v1`         | LM Studio OpenAI-compatible URL  |
| `LM_STUDIO_MODEL`    | `medgemma-27b-text-it-mlx`         | Model name as shown in LM Studio |

## Editing the agent

- `agent.py` is standalone Python — edit on the host, no `iop --migrate` needed.
- Changes take effect on the next HTTP request (uvicorn) or next WSGI spawn
  (IRIS). Restart uvicorn or the IRIS WSGI worker to reload.
- The LLM singleton (`_llm`) is module-level; restart the process to pick up
  new `LM_STUDIO_*` env vars.
- Adding a new predefined question: add an entry to `QUESTIONS` in `agent.py`.

## Reference notebook

`notebooks/ehr_navigator_agent_no_google.ipynb` (in the `medgemma` repo,
also attached to this workspace) is the canonical reference for the agent logic.
It includes verbose `display(Markdown(...))` output at each step and a
`PrintPromptHandler` callback that logs every LLM prompt and response — useful
for debugging prompt quality without running the full FastAPI stack.
