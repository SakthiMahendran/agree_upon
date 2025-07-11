"""
Typed Pydantic models returned by each LangChain chain.
All chains use `llm.with_structured_output(<Model>)`, so the JSON
the LLM emits is auto-parsed into these classes.
"""

from typing import Dict, List
from pydantic import BaseModel, Field


# ────────────────────────────────────────────
# 📄 1. Document-type identification
# ────────────────────────────────────────────
class DocumentTypeOut(BaseModel):
    """Output schema for doc_type_chain."""
    document_type: str = Field(..., description="Exact legal document type requested")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="LLM confidence score (0 – 1)",
    )


# ────────────────────────────────────────────
# 📝 2. Field collection
# ────────────────────────────────────────────
class FieldsOut(BaseModel):
    """Output schema for field_collector_chain."""
    fields: Dict[str, str] = Field(
        ...,
        description="Key-value pairs the user has already supplied",
    )
    missing: List[str] = Field(
        [],
        description="Field names still required before drafting can proceed",
    )


# ────────────────────────────────────────────
# 🖋️ 3. Draft generation
# ────────────────────────────────────────────
class DraftOut(BaseModel):
    """Output schema for draft_generator_chain."""
    draft: str = Field(..., description="Full legal draft (no fluff, no placeholders)")


# ────────────────────────────────────────────
# 🔍 4. Placeholder check
# ────────────────────────────────────────────
class PlaceholderCheckOut(BaseModel):
    """Output schema for placeholder_checker_chain."""
    placeholders: List[str] = Field(
        [],
        description="Unresolved tokens like [DATE], [NAME] found in draft",
    )


# ────────────────────────────────────────────
# ✏️ 5. Refinement
# ────────────────────────────────────────────
class RefineOut(BaseModel):
    """Output schema for refiner_chain."""
    refined_draft: str = Field(..., description="Draft after applying user instructions")
