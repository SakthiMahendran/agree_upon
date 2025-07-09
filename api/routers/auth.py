from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
import os

from .. import models, schemas, deps

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("JWT_SECRET", "change-this")
ALGORITHM = "HS256"

def verify_password(plain, hashed): return pwd_ctx.verify(plain, hashed)
def hash_password(p): return pwd_ctx.hash(p)

@router.post("/register", response_model=schemas.UserRead)
def register(u: schemas.UserCreate, db: Session = Depends(deps.get_db)):
    user = models.User(
        username=u.username, email=u.email, hashed_password=hash_password(u.password)
    )
    db.add(user); db.commit(); db.refresh(user)
    return user

@router.post("/token", response_model=schemas.Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(deps.get_db)):
    user = db.query(models.User).filter(models.User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(400, "Incorrect username or password")
    token = jwt.encode({"sub": user.username}, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}
