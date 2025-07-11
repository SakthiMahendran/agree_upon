# AgreeUpon API v1 Schema

Base URL: `/api/v1`

## Authentication  `/auth`
| Method | Path | Body | Success 200 |
|--------|------|------|-------------|
| POST | /auth/register | UserCreate | UserRead |
| POST | /auth/login | UserLogin | Token |
| POST | /auth/refresh | — | Token |
| POST | /auth/logout | — | `{ok:true}` |

## Conversations  `/conversations`
| Method | Path | Description | Success |
|--------|------|-------------|---------|
| POST | /conversations | create new conversation | Conversation |
| GET  | /conversations | list conversations (`limit,offset`) | List[Conversation] |
| GET  | /conversations/{id} | fetch single conversation | Conversation |
| DELETE | /conversations/{id} | delete conversation | 204 |

## Agent interaction (nested)
| Method | Path | Body | Success |
|--------|------|------|---------|
| POST | /conversations/{id}/agent/message | MessageCreate | AgentReply |
| GET  | /conversations/{id}/agent/stream?prompt=… | SSE | events: reply, document, done |

## Documents (nested)
| Method | Path | Body | Success |
|--------|------|------|---------|
| GET | /conversations/{id}/document | — | Document |
| PUT | /conversations/{id}/document | DocumentUpdate | Document |

## Standard envelope
```json
{
  "data": { … },          // null on error
  "error": {
    "code": "not_found",
    "message": "Conversation not found"
  }
}
```

## Core Models (Python / Pydantic)
```python
class UserCreate(BaseModel):
    username: constr(min_length=3, max_length=30)
    password: constr(min_length=8)

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class Conversation(BaseModel):
    id: int
    created_at: datetime

class MessageCreate(BaseModel):
    content: constr(min_length=1, max_length=10_000)

class AgentReply(BaseModel):
    assistant_reply: str
    document: Optional[str]

class Document(BaseModel):
    id: int
    conversation_id: int
    doc_type: Literal["contract", "memo", "unknown"]
    content: str
    updated_at: datetime
```

---

This schema is versioned, REST-ful, strongly typed, self-documenting, and prepared for expansion.
