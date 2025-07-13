"""
FastAPI router that exposes:
  • POST /agent/{conversation_id}/message
  • POST /agent/{conversation_id}/stream
Now also returns the drafted document (if any).
"""

import logging
import time
import json
from fastapi import APIRouter, Depends, HTTPException, status, Body, Request
from sqlalchemy.orm import Session
from typing import Optional
from fastapi.responses import StreamingResponse

from api import models, schemas, deps
from agent.agent_runner import run_agent_step
from agent.state import AgentState

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger("api.routers.agent")

# ──────────────────────────────────────────────
# POST /agent/{conversation_id}/message
# ──────────────────────────────────────────────
@router.post("/{conversation_id}/message")
def send_message(
    conversation_id: str,
    msg_in: schemas.MessageCreate,
    db: Session = Depends(deps.get_db),
):
    # 1. Load conversation
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found.")

    # 2. Hydrate AgentState
    raw_state = getattr(conv, "state", None)
    if isinstance(raw_state, str):
        try:
            raw_state = json.loads(raw_state)
        except Exception:
            raw_state = None
    state = AgentState(**raw_state) if raw_state else AgentState()

    # 3. Run agent step
    result          = run_agent_step(state, msg_in.content, conversation_id)
    reply           = result["reply"]
    updated_state   = result["updated_state"]
    draft_document  = result["draft_document"]  # could be None

    # ── Persist / upsert Document ──
    if draft_document:

        doc = (
            db.query(models.Document)
            .filter_by(conversation_id=conv.id)
            .first()
        )
        if doc:
            doc.content   = draft_document
            doc.doc_type  = state.document_type or doc.doc_type
        else:
            doc = models.Document(
                conversation_id=conv.id,

                doc_type=state.document_type or "unknown",
                content=draft_document,
            )
            db.add(doc)
        db.commit()

    # 4. Persist messages
    db.add_all([
        models.Message(conversation_id=conv.id, sender="user",      content=msg_in.content),
        models.Message(conversation_id=conv.id, sender="assistant", content=reply),
    ])

    # 5. Persist updated state
    if hasattr(conv, "state"):
        conv.state = json.dumps(updated_state.dict())

    db.commit()

    # 6. Return JSON payload (doc may be null)
    print("Agent replay: ", reply)
    return {
        "assistant_reply": reply,
        "document": draft_document,   # null if no draft yet
    }

# ──────────────────────────────────────────────
# POST /agent/{conversation_id}/stream
# ──────────────────────────────────────────────
@router.post("/{conversation_id}/stream")
async def stream_reply(
    conversation_id: str,
    msg_in: schemas.MessageCreate,
    db: Session = Depends(deps.get_db),
):
    conv = db.query(models.Conversation).filter_by(id=conversation_id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found.")

    raw_state = getattr(conv, "state", None)
    if isinstance(raw_state, str):
        try:
            raw_state = json.loads(raw_state)
        except Exception:
            raw_state = None
    state = AgentState(**raw_state) if raw_state else AgentState()

    # ——— Streaming generator ——————————————————
    def token_stream():
        # Run agent logic
        result         = run_agent_step(state, msg_in.content, conversation_id)
        full_reply     = result["reply"]
        updated_state  = result["updated_state"]
        draft_document = result["draft_document"]

        # Persist DB
        db.add_all([
            models.Message(conversation_id=conv.id, sender="user",      content=msg_in.content),
            models.Message(conversation_id=conv.id, sender="assistant", content=full_reply),
        ])
        if hasattr(conv, "state"):
            conv.state = json.dumps(updated_state.dict())
        db.commit()

        # Stream reply char-by-char
        for ch in full_reply:
            yield f"data: {ch}\n\n"
            time.sleep(0.015)

        # Push the document (if any) as a separate SSE event
        yield "event: document\ndata: " + (draft_document or "") + "\n\n"
        yield "event: done\ndata: END\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream")
