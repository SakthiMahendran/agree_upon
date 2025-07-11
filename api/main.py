import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.database import Base, engine
from api.routers.auth import router as auth_router
from api.routers.conversation import router as conversation_router
from api.routers.agent import router as agent_router
from api.routers.document import router as document_router

# Initialize DB tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AgreeUpon API",
    version="1.0.0",
    description="Agentic AI-Powered Legal Document Drafter for Canadian Law"
)

# ─────────────────────────────
# 🔐 CORS Setup
# ─────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set allowed frontend URLs in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────
# 📁 Static File Mount
# ─────────────────────────────
# Workaround: locate static dir relative to this main.py file
import pathlib
BASE_DIR = pathlib.Path(__file__).parent.parent.resolve()
STATIC_DIR = str(BASE_DIR / "static")

if not os.path.isdir(STATIC_DIR):
    os.makedirs(STATIC_DIR)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ─────────────────────────────
# 🏠 Serve index.html at "/"
# ─────────────────────────────
@app.get("/", include_in_schema=False)
def serve_homepage():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.isfile(index_path):
        return {"error": "index.html not found"}
    return FileResponse(index_path)

# ─────────────────────────────
# 🚀 Include All Routers
# ─────────────────────────────
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(conversation_router, prefix="/conversations", tags=["conversations"])
app.include_router(agent_router, tags=["agent"])  # already has prefix="/agent"
app.include_router(document_router, tags=["documents"])
