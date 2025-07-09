# api/routers/agent.py

import os
import logging
import traceback
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from httpx import HTTPStatusError

from .. import models, schemas, deps
from agent.agent import get_agent_executor

router = APIRouter(prefix="/agent", tags=["agent"])
logger = logging.getLogger("api.routers.agent")
logger.setLevel(logging.DEBUG)

@router.post("/{conv_id}/message", response_model=schemas.MessageRead)
def send_message(
    conv_id: int,
    msg_in: schemas.MessageCreate,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    try:
        logger.info(f"Agent start: conv={conv_id}, input={msg_in.content!r}")

        # 1) Load + authorize
        conv = db.get(models.Conversation, conv_id)
        if not conv or conv.owner_id != current_user.id:
            raise HTTPException(404, "Conversation not found")

        # 2) Save user message
        user_msg = models.Message(
            conversation_id=conv_id,
            sender="user",
            content=msg_in.content
        )
        db.add(user_msg); db.commit(); db.refresh(user_msg)

        # 3) Pull API key
        api_key = os.getenv("HF_TOKEN") or os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise HTTPException(500, "Missing HF_TOKEN / OPENROUTER_API_KEY env var")

        # 4) Build the agent executor
        executor = get_agent_executor(api_key)

        # 5) Invoke agent with fixed-interval retries on 503
        inputs = {
            "input": msg_in.content,
            "history": [],              # replace with real history as needed
            "agent_scratchpad": []      # must be a list, not a string
        }

        last_error = None
        for attempt in range(1, 1001):
            try:
                result = executor.invoke(inputs)
                break
            except HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 503:
                    logger.warning(f"Attempt {attempt}/1000: received 503, retrying in 5s...")
                else:
                    logger.error(f"Attempt {attempt}/1000: HTTP {e.response.status_code}, aborting")
                    raise HTTPException(502, f"LLM HTTP error {e.response.status_code}")
            except Exception as e:
                last_error = e
                if "503" in str(e):
                    logger.warning(f"Attempt {attempt}/1000: encountered 503, retrying in 5s...")
                else:
                    logger.error(f"Attempt {attempt}/1000: non-retryable error: {e}")
                    raise HTTPException(500, "Unexpected error during LLM call")
            time.sleep(5)
        else:
            logger.error(f"All 1000 retries failed: {last_error}")
            raise HTTPException(502, "LLM service unavailable after multiple retries")

        # 6) Post-process: strip internal think blocks
        raw_reply = result.get("output", "").strip()
        if "</think>" in raw_reply:
            # drop everything up to and including the last </think>
            reply = raw_reply.split("</think>")[-1].strip()
        else:
            reply = raw_reply

        # 7) Save assistant message
        ai_msg = models.Message(
            conversation_id=conv_id,
            sender="assistant",
            content=reply
        )
        db.add(ai_msg); db.commit(); db.refresh(ai_msg)

        logger.info(f"Agent end: sent id={ai_msg.id}")
        return ai_msg

    except HTTPException:
        raise
    except Exception:
        tb = traceback.format_exc()
        logger.error(f"Unhandled error in send_message:\n{tb}")
        raise HTTPException(500, "Internal server error — see logs for details")
