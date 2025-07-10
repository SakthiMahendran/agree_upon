from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from api import models, schemas, deps

router = APIRouter(tags=["conversations"])  # 🔥 Removed prefix here

# -------------------------------
# Create a New Conversation
# -------------------------------
@router.post("/", response_model=schemas.ConversationRead)
def create_conversation(
    c: schemas.ConversationCreate,
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    conv = models.Conversation(user_id=user.id)
    db.add(conv); db.commit(); db.refresh(conv)
    return conv

# -------------------------------
# List User's Conversations
# -------------------------------
@router.get("/", response_model=List[schemas.ConversationRead])
def list_conversations(
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    return db.query(models.Conversation)\
             .filter(models.Conversation.user_id == user.id)\
             .order_by(models.Conversation.created_at.desc())\
             .all()

# -------------------------------
# Get a Conversation by ID
# -------------------------------
@router.get("/{id}", response_model=schemas.ConversationRead)
def get_conversation(
    id: int,
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    conv = db.query(models.Conversation).filter_by(id=id, user_id=user.id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    return conv

# -------------------------------
# Delete a Conversation
# -------------------------------
@router.delete("/{id}", status_code=204)
def delete_conversation(
    id: int,
    db: Session = Depends(deps.get_db),
    user: models.User = Depends(deps.get_current_user),
):
    conv = db.query(models.Conversation).filter_by(id=id, user_id=user.id).first()
    if not conv:
        raise HTTPException(404, "Conversation not found")
    db.delete(conv); db.commit()
