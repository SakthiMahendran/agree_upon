# agent/prompts.py

from langchain_core.prompts import PromptTemplate

# 4️⃣ PLACEHOLDER CHECKER PROMPT
PLACEHOLDER_CHECKER_PROMPT = PromptTemplate.from_template("""
You're checking the draft below for any missing fields or placeholder values like [PLACEHOLDER], [Your Name], etc.

Draft:
{draft}

List all placeholders found in the draft. Return as a Python list. If none found, return an empty list.
""")
