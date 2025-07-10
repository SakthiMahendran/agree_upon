# api/routers/agent.py

import logging
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from api import models, schemas, deps
from agent.agent_runner import run_agent_step
from agent.state import AgentState

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger("api.routers.agent")


# ──────────────────────────────────────────────
# POST /agent/{conversation_id}/message
# Handles normal (non-streaming) agent replies
# ──────────────────────────────────────────────
@router.post("/{conversation_id}/message", response_model=schemas.MessageRead)
def send_message(
    conversation_id: str,
    msg_in: schemas.MessageCreate,
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    # 1. Load conversation
    conv = (
        db.query(models.Conversation)
        .filter_by(id=conversation_id, user_id=user.id)
        .first()
    )
    if not conv:
        raise HTTPException(404, "Conversation not found.")

    # 2. Safely load or initialize AgentState
    raw_state = getattr(conv, "state", None)
    state = AgentState(**raw_state) if raw_state else AgentState()

    # 3. Run agent logic
    result = run_agent_step(state, msg_in.content, conversation_id)
    reply, updated_state = result["reply"], result["updated_state"]

    # 4. Persist messages (use `sender`, matching your ORM model)
    user_msg = models.Message(
        conversation_id=conv.id,
        sender="user",
        content=msg_in.content
    )
    ai_msg = models.Message(
        conversation_id=conv.id,
        sender="assistant",
        content=reply
    )
    db.add_all([user_msg, ai_msg])

    # 5. Persist updated state if supported
    if hasattr(conv, "state"):
        conv.state = updated_state.dict()
    else:
        logger.debug("Conversation model has no 'state' attribute—skipping state persistence.")

    db.commit()
    db.refresh(ai_msg)

    return schemas.MessageRead(
        id=ai_msg.id,
        sender=ai_msg.sender,
        content=ai_msg.content,
        timestamp=ai_msg.timestamp  # adjust field if your model uses a different name
    )


# ──────────────────────────────────────────────
# POST /agent/{conversation_id}/stream
# Streams the assistant's reply via SSE (EventSource)
# ──────────────────────────────────────────────
@router.post("/{conversation_id}/stream")
async def stream_reply(
    conversation_id: str,
    msg_in: schemas.MessageCreate,
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    conv = (
        db.query(models.Conversation)
        .filter_by(id=conversation_id, user_id=user.id)
        .first()
    )
    if not conv:
        raise HTTPException(404, "Conversation not found.")

    raw_state = getattr(conv, "state", None)
    state = AgentState(**raw_state) if raw_state else AgentState()

    def token_stream():
        # Run agent step (non-streaming)
        result = run_agent_step(state, msg_in.content, conversation_id)
        full_reply = result["reply"]
        updated_state = result["updated_state"]

        # Persist messages and state
        user_msg = models.Message(
            conversation_id=conv.id,
            sender="user",
            content=msg_in.content
        )
        ai_msg = models.Message(
            conversation_id=conv.id,
            sender="assistant",
            content=full_reply
        )
        db.add_all([user_msg, ai_msg])
        if hasattr(conv, "state"):
            conv.state = updated_state.dict()
        db.commit()

        # Stream character by character
        for char in full_reply:
            yield f"data: {char}\n\n"
            time.sleep(0.015)

        yield "event: done\ndata: END\n\n"

    return StreamingResponse(token_stream(), media_type="text/event-stream")
