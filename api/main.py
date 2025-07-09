# api/main.py

import logging
from dotenv import load_dotenv

# 1) Load environment variables before anything else
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Configure root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

from .database import Base, engine
from .routers import auth, conversations, agent

# Create all tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="LegalBot API")
app.include_router(auth.router)
app.include_router(conversations.router)
app.include_router(agent.router)
app.mount("/static", StaticFiles(directory="api/static"), name="static")
