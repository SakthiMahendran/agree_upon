from pydantic import BaseModel, Field
from typing import Dict, Any, List

class AgentState(BaseModel):
    session_id: str
    user_input: str = ""
    document_type: str = ""
    required_fields: List[str] = Field(default_factory=list)
    current_field: str = ""
    collected_info: Dict[str, Any] = Field(default_factory=dict)
    draft: str = ""
    placeholders_found: List[str] = Field(default_factory=list)
    refine_request: str = ""
    final_document: str = ""
    error_message: str = ""
    has_drafted_once: bool = False
