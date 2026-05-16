"""POST /chat/stream — Server-Sent Events endpoint driving the orchestrator."""
from __future__ import annotations

import json
import time

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.orchestrator import Orchestrator
from backend.db.repos import AthleteRepo, ChatRepo

router = APIRouter()


class ChatRequest(BaseModel):
    athlete_id: str
    message: str
    language: str = "tr"


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False, default=str)}\n\n"


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    profile = AthleteRepo().get(req.athlete_id)
    if not profile:
        raise HTTPException(
            status_code=404,
            detail=f"Athlete '{req.athlete_id}' not found. Run /onboarding first or call /profile to create one.",
        )

    # Per-request language override (the user may toggle in the UI)
    profile["language"] = req.language

    history = ChatRepo().last(req.athlete_id, n=6)

    def event_stream():
        t0 = time.time()
        final_answer = ""
        final_metadata: dict = {}
        try:
            for event in Orchestrator().run(
                user_message=req.message,
                athlete_id=req.athlete_id,
                profile=profile,
                history=history,
            ):
                if event.get("type") == "done":
                    event["latency_ms"] = int((time.time() - t0) * 1000)
                    final_answer = event.get("answer", "")
                    final_metadata = {
                        "trace": event.get("trace", []),
                        "verification_score": event.get("verification_score", 1.0),
                        "removed_claims": event.get("removed_claims", []),
                        "latency_ms": event["latency_ms"],
                    }
                yield _sse(event)
        except Exception as e:
            yield _sse({"type": "error", "message": f"{type(e).__name__}: {e}"})
            return

        # Persist the conversation outside the stream loop
        if final_answer:
            try:
                ChatRepo().append(req.athlete_id, "user", req.message)
                ChatRepo().append(
                    req.athlete_id, "assistant", final_answer, metadata=final_metadata
                )
            except Exception:
                pass  # don't fail the response if logging fails

    return StreamingResponse(event_stream(), media_type="text/event-stream")
