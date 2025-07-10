from typing import Optional, List
from pydantic import BaseModel

class AgentState(BaseModel):
    stage: Optional[str] = "q_and_a"
    document_type: Optional[str] = None
    required_fields: Optional[List[str]] = []
    collected_info: dict = {}
    current_field: Optional[str] = ""
    draft: Optional[str] = ""
    placeholders_found: List[str] = []
    refine_request: Optional[str] = ""
    final_document: Optional[str] = ""
    user_input: Optional[str] = ""
    error_message: Optional[str] = ""
