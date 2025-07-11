"""
agent/state.py
━━━━━━━━━━━━━━━━━━━━━━━━━━
Canonical state shared by all chains & the runner.
"""

from typing import Dict
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
    # Internal helpers (not exposed)
    # ──────────────────────────────
    def summary(self) -> str:
        """Compact one-liner for LLM context injection."""
        typed = self.document_type or "—"
        drafted = "yes" if self.is_drafted else "no"
        return (f"type={typed}, drafted={drafted}, "
                f"fields={list(self.needed_fields.keys())}")
