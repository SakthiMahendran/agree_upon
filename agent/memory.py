"""
agent/memory.py
─────────────────────────────────────────────────────────────────────────────
Production-grade ConversationBufferMemory backed by your SQL database.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Dict, List

from langchain.memory import ConversationBufferMemory
from sqlalchemy.orm import Session

from api.database import SessionLocal
from api.models import Conversation, Message  # ORM models

logger = logging.getLogger("agent.memory")
logger.setLevel(logging.DEBUG)

# ─────────────────────────────────────────────────────────────
#  Session helper
# ─────────────────────────────────────────────────────────────
@contextmanager
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────────
#  Ensure conversation row exists
# ─────────────────────────────────────────────────────────────
def _ensure_conversation(db: Session, conversation_id: int) -> None:
    if not db.query(Conversation).filter_by(id=conversation_id).first():
        db.add(Conversation(id=conversation_id, user_id=0))
        db.commit()
        logger.debug("➕ Created Conversation(id=%s)", conversation_id)

# ─────────────────────────────────────────────────────────────
#  SQL-backed memory class
# ─────────────────────────────────────────────────────────────
class SQLBufferMemory(ConversationBufferMemory):
    """
    LangChain ConversationBufferMemory that transparently syncs
    with the `messages` table.
    """

    class Config:
        arbitrary_types_allowed = True  # allow raw db/session attrs
        extra = "allow"                # ignore unknown attrs

    # ––– Init ––––––––––––––––––––––––––––––––––––––––––––
    def __init__(self, conversation_id: int, db: Session):
        super().__init__(
            memory_key="history",      # <<< aligns w/ agent_runner
            input_key="user_input",
            return_messages=True,
        )

        # attach non-pydantic fields
        object.__setattr__(self, "conversation_id", conversation_id)
        object.__setattr__(self, "db", db)

        self._bootstrap()

    # ––– Bootstrap history –––––––––––––––––––––––––––––––
    def _bootstrap(self) -> None:
        rows: List[Message] = (
            self.db.query(Message)
            .filter(Message.conversation_id == self.conversation_id)
            .order_by(Message.timestamp)
            .all()
        )
        logger.debug(
            "🧩 Bootstrapping %s msgs for conv_id=%s",
            len(rows), self.conversation_id
        )

        for row in rows:
            if row.sender == "user":
                self.chat_memory.add_user_message(row.content)
            else:
                self.chat_memory.add_ai_message(row.content)

    # ––– Persist new turn ––––––––––––––––––––––––––––––––
    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """Persist BOTH the in-memory buffer and DB rows."""
        super().save_context(inputs, outputs)  # update LC buffer

        user_msg       = str(inputs.get("user_input", ""))
        assistant_resp = str(outputs.get("output", ""))

        self.db.add_all(
            [
                Message(
                    conversation_id=self.conversation_id,
                    sender="user",
                    content=user_msg,
                ),
                Message(
                    conversation_id=self.conversation_id,
                    sender="assistant",
                    content=assistant_resp,
                ),
            ]
        )
        self.db.commit()
        logger.debug("💾 Saved turn to DB for conv_id=%s", self.conversation_id)

    # ––– Cleanup –––––––––––––––––––––––––––––––––––––––––
    def __del__(self):
        try:
            self.db.close()
        except Exception:  # pragma: no cover
            pass

# ─────────────────────────────────────────────────────────────
#  Factory for agent_runner
# ─────────────────────────────────────────────────────────────
def get_memory(conversation_id: str) -> SQLBufferMemory:
    """
    Return a SQL-backed ConversationBufferMemory for the given
    conversation_id (FastAPI passes it as a string).
    """
    conv_id_int = int(conversation_id)
    db = SessionLocal()
    _ensure_conversation(db, conv_id_int)
    return SQLBufferMemory(conversation_id=conv_id_int, db=db)
