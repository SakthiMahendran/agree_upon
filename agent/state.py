"""
agent/state.py
━━━━━━━━━━━━━━━━━━━━━━━━━━
Canonical state shared by all chains & the runner.
"""

import json
from typing import Dict, Any
from pydantic import BaseModel, field_validator
from pydantic import BaseModel


class AgentState(BaseModel):
    # ──────────────────────────────
    # User–visible state
    # ──────────────────────────────
    document_type: str = ""                   # e.g. “NDA”, “Lease Agreement”
    needed_fields: Dict[str, str] = {}        # { "Party A Name": "Alice LLC", … }
    draft: str = ""                           # Full draft (multiline)
    is_drafted: bool = False                  # True ⇢ draft has been generated
    missing_prompt_count: int = 0             # Times user has been asked for missing details

    # ──────────────────────────────
    # Validation – ensure string values
    # ──────────────────────────────
    @field_validator('needed_fields', mode='before')
    @classmethod
    def _coerce_needed_fields(cls, v: Any):
        """Ensure needed_fields is Dict[str, str] regardless of input shapes."""
        if v is None:
            return {}
        if isinstance(v, dict):
            str_dict: Dict[str, str] = {}
            for k, val in v.items():
                if isinstance(val, str):
                    str_dict[str(k)] = val
                else:
                    try:
                        str_dict[str(k)] = json.dumps(val, ensure_ascii=False)
                    except TypeError:
                        str_dict[str(k)] = str(val)
            return str_dict
        # Accept list of pairs etc.
        try:
            as_dict = dict(v)
            return cls._coerce_needed_fields(as_dict)
        except Exception:
            # Fallback: ignore invalid format
            return {}


    # ──────────────────────────────
    # Internal helpers (not exposed)
    # ──────────────────────────────
    def summary(self) -> str:
        """Compact one-liner for LLM context injection."""
        typed = self.document_type or "—"
        drafted = "yes" if self.is_drafted else "no"
        return (f"type={typed}, drafted={drafted}, "
                f"fields={list(self.needed_fields.keys())}")
