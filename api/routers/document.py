"""api/routers/document.py
Provides endpoints to fetch / update drafted documents associated with a conversation.
Currently only GET is required for the frontend to display the latest draft.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api import models, deps
from agent.state import AgentState

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{conversation_id}")
def get_document(conversation_id: int, db: Session = Depends(deps.get_db), user: models.User = Depends(deps.get_current_user)):
    """Return the drafted document for a conversation, or 404."""
    doc = (
        db.query(models.Document)
        .filter_by(conversation_id=conversation_id, user_id=user.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "conversation_id": doc.conversation_id,
        "doc_type": doc.doc_type,
        "content": doc.content,
        "updated_at": str(doc.updated_at),
    }
