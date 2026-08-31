import asyncio
import json
import threading
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from DSE.agent import QUESTIONS, run_agent_stream

_STATIC = Path(__file__).parent.parent / "static" / "agent"

router = APIRouter(prefix="/agent", tags=["EHR Agent"])


@router.get("/", response_class=HTMLResponse)
async def agent_ui():
    return (_STATIC / "index.html").read_text()


@router.get("/questions")
async def get_questions():
    return QUESTIONS


@router.get("/run_agent")
async def run_agent_endpoint(
    patient_id: str = Query(default="3887"),
    question_id: Optional[int] = Query(default=None),
    prompt: Optional[str] = Query(default=None),
):
    if question_id is not None:
        entry = next((q for q in QUESTIONS if q["id"] == question_id), None)
        if entry is None:
            raise HTTPException(404, "Question not found")
        question = entry["question"]
    elif prompt:
        question = prompt
    else:
        raise HTTPException(400, "Provide question_id or prompt")

    return StreamingResponse(
        _sse_stream(question, patient_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _sse_stream(question: str, patient_id: str):
    queue: asyncio.Queue = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def sync_emit(event: dict) -> None:
        asyncio.run_coroutine_threadsafe(queue.put(event), loop)

    def run():
        try:
            run_agent_stream(question, patient_id, emit=sync_emit)
        except Exception as exc:
            sync_emit({"destination": None, "request": False,
                       "event": f"Agent error: {exc}", "data": str(exc), "final": True})
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop)

    threading.Thread(target=run, daemon=True).start()

    while True:
        event = await queue.get()
        if event is None:
            break
        yield f"data: {json.dumps(event)}\n\n"
