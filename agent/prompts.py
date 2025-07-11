# agent/prompts.py

from langchain_core.prompts import PromptTemplate

# 1️⃣ DOC TYPE CLASSIFICATION PROMPT
DOC_TYPE_PROMPT = PromptTemplate.from_template("""
You are a legal document assistant. Based on the user's message, identify the type of legal document they want to create.

Examples:
- "I need a contract for renting my apartment." → Rental Agreement
- "Write a Non-Disclosure Agreement for my startup." → NDA
- "I want a legal agreement to hire a software developer." → Employment Contract

User message:
{input}

Your answer (document type only):
""")

# 2️⃣ FIELD COLLECTOR PROMPT
FIELD_COLLECTOR_PROMPT = PromptTemplate.from_template("""
You are a helpful assistant tasked with extracting required fields from a user message to create a {doc_type}.

Collected fields so far:
{fields}

User message:
{input}

Return a JSON dictionary of extracted field names and values (no explanations).
""")

# 3️⃣ DRAFT GENERATOR PROMPT
DRAFT_GENERATOR_PROMPT = PromptTemplate.from_template("""
You are a legal drafting assistant. Based on the following information, generate a professional {doc_type}.

Required Fields:
{fields}

User Input:
{input}

Respond with a complete and clean legal draft, ready for client use. Do not include placeholder text like "[Your Company]".
""")

# 4️⃣ PLACEHOLDER CHECKER PROMPT
PLACEHOLDER_CHECKER_PROMPT = PromptTemplate.from_template("""
You're checking the draft below for any missing fields or placeholder values like [PLACEHOLDER], [Your Name], etc.

Draft:
{draft}

List all placeholders found in the draft. Return as a Python list. If none found, return an empty list.
""")

# 5️⃣ REFINER PROMPT
REFINER_PROMPT = PromptTemplate.from_template("""
You are a legal assistant. Refine the document below based on the given user instruction.

Instruction:
{instruction}

Original Draft:
{draft}

Return the revised draft only. No commentary or intro.
""")

# 6️⃣ Q&A FALLBACK PROMPT
QNA_PROMPT = PromptTemplate.from_template("""
You are a helpful legal assistant. Respond conversationally to the user's message below.

User:
{input}

Keep the response clear and supportive.
""")
