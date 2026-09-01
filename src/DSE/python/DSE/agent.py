"""
EHR Navigator Agent — DSE service.
Adapted from notebooks/ehr_navigator_agent_no_google.ipynb.
LLM: local MedGemma via LM Studio (OpenAI-compatible endpoint).
"""

import concurrent.futures
import json
import operator
import os
import re
from typing import Annotated, Callable, Optional, TypedDict
from urllib.parse import quote

import requests

# LangChain imports
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool        # @tool decorator
from openai import OpenAI                    # direct client avoids LangChain tool-call routing on 27b responses

# LangGraph imports
from langgraph.graph import END, StateGraph  # the pipeline wiring
from langgraph.prebuilt import ToolNode      # executes tools

# ── Configuration ─────────────────────────────────────────────────────────────

FHIR_STORE_URL = os.getenv("FHIR_STORE_URL", "http://4.210.90.115:8081/fhir/r4")
FHIR_USER = os.getenv("FHIR_USER", "SuperUser")
FHIR_PASSWORD = os.getenv("FHIR_PASSWORD", "SYS")
LM_STUDIO_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
LM_STUDIO_MODEL = os.getenv("LM_STUDIO_MODEL", "medgemma-27b-text-it-mlx")
LLM_CONTEXT_TOKENS = int(os.getenv("LLM_CONTEXT_TOKENS", "131072"))  # max tokens your model supports

FHIR_RESOURCE_TYPES = [
    "Encounter", "Practitioner",
    "Condition", "Observation", "AllergyIntolerance", "FamilyMemberHistory",
    "MedicationRequest", "MedicationStatement", "MedicationAdministration",
    "DiagnosticReport", "Procedure", "ServiceRequest",
]

QUESTIONS = [
    {"id": 1, "question": "What medications is this patient currently prescribed?"},
    {"id": 2, "question": "Does this patient have conditions or devices associated with pressure injury risk?"},
    {"id": 3, "question": "What are this patient's most recent laboratory results?"},
    {"id": 4, "question": "What procedures has this patient undergone?"},
    {"id": 5, "question": "Summarise this patient's active medical conditions."},
]

# tokens reserved for the question, prompt template, and answer — not available for FHIR data
_PROMPT_RESERVED_TOKENS = 4_000

# ── LLM ───────────────────────────────────────────────────────────────────────

class _StringLLM:
    """Calls the LLM directly, bypassing LangChain response routing."""

    def __init__(self):
        self._client = OpenAI(base_url=LM_STUDIO_BASE_URL, api_key="lm-studio")

    def invoke(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1) -> str:
        response = self._client.chat.completions.create(
            model=LM_STUDIO_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""


_llm: Optional[_StringLLM] = None


def _get_llm() -> _StringLLM:
    global _llm
    if _llm is None:
        _llm = _StringLLM()
    return _llm


# ── Helpers ───────────────────────────────────────────────────────────────────

def _strip_thinking(text: str) -> str:
    return re.sub(r"<unused94>.*?<unused95>", "", text, flags=re.DOTALL).strip()


def _strip_json_fences(text: str) -> str:
    s = text.strip()
    if s.startswith("```json") and s.endswith("```"):
        return s[7:-3].strip()
    if s.startswith("```") and s.endswith("```"):
        return s[3:-3].strip()
    return s


def _get_fhir(resource_path: str) -> dict:
    """Paginated FHIR GET helper — no side-effects."""
    try:
        all_entries = []
        url = f"{FHIR_STORE_URL}/{resource_path}"
        while url:
            resp = requests.get(url, auth=(FHIR_USER, FHIR_PASSWORD), timeout=30)
            resp.raise_for_status()
            page = resp.json()
            all_entries.extend(page.get("entry", []))
            url = next((l["url"] for l in page.get("link", []) if l.get("relation") == "next"), None)

        def clean(obj):
            if isinstance(obj, list):
                return [clean(i) for i in obj]
            if isinstance(obj, dict):
                return {k: clean(v) for k, v in obj.items() if k != "meta"}
            return obj.split("/fhir/")[-1] if isinstance(obj, str) and "/fhir/" in obj else obj

        for e in all_entries:
            e.pop("fullUrl", None)
            e.pop("search", None)
            if "resource" in e:
                e["resource"] = clean(e["resource"])

        return {"resourceType": "Bundle", "type": "searchset", "total": len(all_entries), "entry": all_entries}
    except Exception as exc:
        return {"error": str(exc), "total": 0}


# ── Agent state ───────────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[list, operator.add]
    patient_id: str
    patient_fhir_manifest: dict
    tool_output_summary: Annotated[list, operator.add]
    tool_calls_to_execute: list
    relevant_resource_types: list


# ── Agent builder ─────────────────────────────────────────────────────────────

def _build_agent(emit: Callable[[dict], None]):
    """
    Compile a LangGraph agent wired to the given emit callback.
    Built per-request so each SSE stream gets its own closure.
    """
    llm = _get_llm()

    # ── Tools (closures over emit) ────────────────────────────────────────────

    @tool
    def get_patient_data_manifest(patient_id: str) -> str:
        """Discovers all available FHIR resource types for a patient."""
        manifest = {}

        def _scan(rt):
            emit({"destination": "FHIR", "request": True, "event": f"Discovering {rt}…", "data": None, "final": False})
            result = _get_fhir(f"{rt}?patient=Patient/{patient_id}")
            if result.get("total", 0) > 0:
                codes = []
                for entry in result.get("entry", []):
                    resource = entry.get("resource", {})
                    if "code" in resource and "coding" in resource["code"]:
                        for code in resource["code"]["coding"]:
                            codes.append(f'{code.get("display", "")}={code.get("code", "")}')
                emit({"destination": "FHIR", "request": False, "event": f"{rt}: {result['total']} records", "data": None, "final": False})
                return rt, codes
            emit({"destination": "FHIR", "request": False, "event": f"{rt}: none", "data": None, "final": False})
            return rt, None

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(FHIR_RESOURCE_TYPES)) as pool:
            for rt, codes in pool.map(_scan, FHIR_RESOURCE_TYPES):
                if codes is not None:
                    manifest[rt] = codes

        return json.dumps(manifest)

    @tool
    def get_patient_fhir_resource(patient_id: str, fhir_resource: str, filter_code: Optional[str] = None) -> str:
        """Fetches a specific FHIR resource type for a patient, optionally filtered by code."""
        path = f"{fhir_resource}?patient=Patient/{patient_id}"
        if filter_code:
            path += f"&code={quote(filter_code.replace(' ', ''))}"
        if "Medication" in fhir_resource:
            path += f"&_include={fhir_resource}:medication"
        result = _get_fhir(path)
        if result.get("total", 0) == 0 and filter_code:
            path = f"{fhir_resource}?patient=Patient/{patient_id}&category={quote(filter_code)}"
            result = _get_fhir(path)
        return json.dumps(result)

    manifest_tool_node = ToolNode([get_patient_data_manifest])

    # ── Nodes ─────────────────────────────────────────────────────────────────

    def call_manifest_tool(state: AgentState) -> dict:
        patient_id = state["patient_id"]
        emit({"destination": "FHIR", "request": True, "event": f"Scanning records for patient {patient_id}…", "data": None, "final": False})
        try:
            msg = AIMessage(content="", tool_calls=[{
                "name": "get_patient_data_manifest",
                "args": {"patient_id": patient_id},
                "id": "manifest_call",
            }])
            output = manifest_tool_node.invoke([msg])[0]
            manifest = json.loads(output.content)
            # Always fetch Patient demographics — a direct read returns the resource, not a Bundle
            emit({"destination": "FHIR", "request": True, "event": "Fetching Patient demographics\u2026", "data": None, "final": False})
            pt_resp = requests.get(f"{FHIR_STORE_URL}/Patient/{patient_id}",
                                   auth=(FHIR_USER, FHIR_PASSWORD), timeout=30)
            pt_resp.raise_for_status()
            pt = pt_resp.json()
            if pt.get("resourceType") == "Patient":
                manifest["Patient"] = {
                    "gender":    pt.get("gender", "unknown"),
                    "birthDate": pt.get("birthDate", "unknown"),
                    "name":      next((f"{n.get('family','')} {' '.join(n.get('given',[]))}"
                                       for n in pt.get("name", []) if n.get("use") == "official"), "unknown"),
                }
            emit({"destination": "FHIR", "request": False, "event": "Patient demographics loaded", "data": None, "final": False})
            return {"patient_fhir_manifest": manifest}
        except Exception as exc:
            emit({"destination": None, "request": False, "event": f"Manifest error: {exc}", "data": None, "final": False})
            return {"patient_fhir_manifest": {}}

    def identify_relevant_resource_types(state: AgentState) -> dict:
        manifest = state.get("patient_fhir_manifest", {})
        question = state["messages"][1].content
        manifest_text = "\n".join(
            f"{rt}: {', '.join(v.values()) if isinstance(v, dict) else (', '.join(v) if v else 'present')}"
            for rt, v in manifest.items()
        )
        emit({"destination": "LLM", "request": True,  "event": "Identifying relevant resource types\u2026", "data": None, "final": False})
        prompt = (
            f"USER QUESTION: {question}\n\nPATIENT DATA MANIFEST:\n{manifest_text}\n\n"
            "Output a JSON list of FHIR resource types needed to answer the question.\n"
            "RULES:\n"
            "- For purely demographic questions (age, sex, gender, name, date of birth) return ONLY [\"Patient\"].\n"
            "- Include clinical resource types only when the question explicitly asks about clinical data.\n"
            "- No other text.\n"
            'Example: ["Condition", "Observation"]'
        )
        raw = llm.invoke(prompt, max_tokens=200, temperature=0.0)
        try:
            relevant = json.loads(_strip_json_fences(raw))
        except json.JSONDecodeError:
            relevant = []
        emit({"destination": "LLM", "request": False, "event": f"Relevant: {', '.join(relevant)}", "data": None, "final": False})
        return {"relevant_resource_types": relevant}

    def select_data_to_retrieve(state: AgentState) -> dict:
        manifest = state.get("patient_fhir_manifest", {})
        relevant = state.get("relevant_resource_types", [])
        patient_id = state["patient_id"]
        # Build tool calls directly — no LLM needed, the resource type is already known
        # Patient is served from the manifest dict; Patient?patient=... is not a valid FHIR query
        calls = [
            {"name": "get_patient_fhir_resource",
             "args": {"patient_id": patient_id, "fhir_resource": rt},
             "id": rt}
            for rt in relevant if rt in manifest and rt != "Patient"
        ]
        return {"tool_calls_to_execute": calls}

    def execute_data_retrieval(state: AgentState) -> dict:
        facts = []
        manifest = state.get("patient_fhir_manifest", {})
        relevant = state.get("relevant_resource_types", [])
        question = state["messages"][1].content

        # Patient demographics are already in the manifest — no FHIR call needed
        if "Patient" in relevant and "Patient" in manifest:
            pt = manifest["Patient"]
            facts.append(f"Patient demographics: gender={pt.get('gender')}, birthDate={pt.get('birthDate')}, name={pt.get('name')}")
            emit({"destination": "FHIR", "request": False, "event": "Patient demographics from manifest", "data": None, "final": False})

        calls = state.get("tool_calls_to_execute", [])
        if not calls:
            return {"tool_output_summary": facts}

        def _fetch(call):
            rt = call.get("id", "resource")
            emit({"destination": "FHIR", "request": True, "event": f"Fetching {rt}…", "data": None, "final": False})
            raw = get_patient_fhir_resource.invoke(call["args"])
            emit({"destination": "FHIR", "request": False, "event": f"{rt} received", "data": None, "final": False})
            return rt, raw

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(calls)) as pool:
            fetched = dict(pool.map(_fetch, calls))

        data_budget_chars = (LLM_CONTEXT_TOKENS - _PROMPT_RESERVED_TOKENS) * 4
        total_chars = sum(len(raw) for raw in fetched.values())

        if total_chars <= data_budget_chars:
            emit({"destination": None, "request": False, "event": f"Data fits in context ({total_chars // 1024} KB) — no summarization needed", "data": None, "final": False})
            for rt, raw in fetched.items():
                facts.append(f"=== {rt} ===\n{raw}")
            return {"tool_output_summary": facts}

        # Summarize the largest resources first until the total fits in the context budget
        emit({"destination": None, "request": False, "event": f"Data too large ({total_chars // 1024} KB) — summarizing largest resources", "data": None, "final": False})
        result = dict(fetched)
        for rt in sorted(fetched, key=lambda r: len(fetched[r]), reverse=True):
            if total_chars <= data_budget_chars:
                break
            raw = result[rt]
            emit({"destination": "LLM", "request": True, "event": f"Summarizing {rt} ({len(raw) // 1024} KB)…", "data": None, "final": False})
            summary_prompt = (
                f"USER QUESTION: {question}\n\n"
                f"FHIR DATA ({rt}):\n{raw}\n\n"
                "Summarise only facts relevant to the question. Be concise. No JSON."
            )
            summary = _strip_thinking(llm.invoke(summary_prompt, max_tokens=2000, temperature=0.6))
            total_chars -= len(raw) - len(summary)
            result[rt] = summary
            emit({"destination": "LLM", "request": False, "event": f"{rt} summarized", "data": None, "final": False})

        for rt in fetched:  # preserve original resource type order
            facts.append(f"=== {rt} ===\n{result[rt]}")
        return {"tool_output_summary": facts}

    def get_final_answer(state: AgentState) -> dict:
        emit({"destination": "LLM", "request": True, "event": "Synthesising final answer…", "data": None, "final": False})
        prompt = (
            f"USER QUESTION: {state['messages'][1].content}\n\n"
            f"PATIENT DATA:\n{chr(10).join(state['tool_output_summary'])}\n\n"
            "Provide a comprehensive answer in markdown:"
        )
        answer = _strip_thinking(llm.invoke(prompt, max_tokens=2000, temperature=0.1))
        emit({"destination": "LLM", "request": False, "event": "Answer ready", "data": answer, "final": True})
        return {"messages": [AIMessage(content=answer)]}

    # ── Graph ─────────────────────────────────────────────────────────────────

    wf = StateGraph(AgentState)
    wf.add_node("call_manifest_tool",              call_manifest_tool)
    wf.add_node("identify_relevant_resource_types", identify_relevant_resource_types)
    wf.add_node("select_data_to_retrieve",          select_data_to_retrieve)
    wf.add_node("execute_data_retrieval",           execute_data_retrieval)
    wf.add_node("final_answer",                     get_final_answer)
    wf.set_entry_point("call_manifest_tool")
    wf.add_edge("call_manifest_tool",              "identify_relevant_resource_types")
    wf.add_edge("identify_relevant_resource_types", "select_data_to_retrieve")
    wf.add_edge("select_data_to_retrieve",          "execute_data_retrieval")
    wf.add_edge("execute_data_retrieval",           "final_answer")
    wf.add_edge("final_answer",                     END)
    return wf.compile()


# ── Public entry point ────────────────────────────────────────────────────────

def run_agent_stream(question: str, patient_id: str, emit: Callable[[dict], None]) -> None:
    """Run the agent synchronously, calling emit for every SSE event."""
    agent = _build_agent(emit)
    agent.invoke({
        "messages": [
            SystemMessage(content="You are MedGemma, a helpful medical assistant."),
            HumanMessage(content=question),
        ],
        "patient_id": patient_id,
        "patient_fhir_manifest": {},
        "tool_output_summary": [],
    })
