# Agree Upon – LangChain + FastAPI Agentic AI Legal Drafter

A production-grade, LangChain-native conversational legal document drafting assistant using FastAPI, JWT authentication, SQLAlchemy, and a Hugging Face-hosted OpenAI-compatible LLM.

## Features
- Conversational agent for legal document drafting (NDA, Lease, Partnership, Shareholder, etc.)
- Gathers required fields, generates clean drafts, and allows iterative refinement
- No LLM fluff or placeholders in final drafts
- JWT-based authentication (python-jose)
- SQLAlchemy ORM for User, Conversation, Message, Document
- Conversation memory with LangChain `ConversationBufferMemory`
- Hugging Face OpenAI-compatible LLM with 503 cold-start retry
- FastAPI endpoints for auth, agent chat, conversations, documents
- CLI runner for terminal chat
- Ready for future RAG, web search, doc upload/parse

## Folder Structure
```
agree_upon/
├── api/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── database.py
│   └── routers/
│       ├── auth.py
│       ├── agent.py
│       ├── conversation.py
│       └── document.py
├── agent/
│   ├── prompts.py
│   ├── memory.py
│   ├── utils.py
│   ├── agent_runner.py
│   └── chains/
│       ├── doc_type_chain.py
│       ├── field_collector_chain.py
│       ├── draft_generator_chain.py
│       ├── placeholder_checker.py
│       └── refiner_chain.py
├── static/
│   └── index.html
├── .env
├── requirements.txt
└── README.md
```

## Quickstart
1. Install dependencies: `pip install -r requirements.txt`
2. Set your Hugging Face API key in `.env` as `HF_TOKEN=...`
3. Run FastAPI: `uvicorn api.main:app --reload`
4. (Optional) Run CLI: `python agent/agent_runner.py`

---

See code comments and docstrings for further details.
