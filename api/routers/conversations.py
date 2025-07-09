from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .. import models, schemas, deps

router = APIRouter(prefix="/conversations", tags=["conversations"])

@router.post("/", response_model=schemas.ConversationRead)
def create_conv(c: schemas.ConversationCreate, db: Session = Depends(deps.get_db),
                user = Depends(deps.get_current_user)):
    conv = models.Conversation(title=c.title, owner_id=user.id, state_json="{}")
    db.add(conv); db.commit(); db.refresh(conv)
    return conv

@router.get("/", response_model=List[schemas.ConversationRead])
def list_convs(db: Session = Depends(deps.get_db), user = Depends(deps.get_current_user)):
    return db.query(models.Conversation).filter_by(owner_id=user.id).all()

@router.delete("/{id}", status_code=204)
def delete_conv(id: int, db: Session = Depends(deps.get_db),
                user = Depends(deps.get_current_user)):
    conv = db.query(models.Conversation).get(id)
    if not conv or conv.owner_id != user.id:
        raise HTTPException(404, "Not found")
    db.delete(conv); db.commit()
