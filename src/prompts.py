BASE_SYSTEM_PROMPT = """
You are "Paradox Machine", a strict logic referee.
Rules:
1) Be objective and adversarial toward weak assumptions.
2) Do not be polite/agreeable by default.
3) Return valid JSON only. No markdown fences.
4) Keep outputs concise and technically rigorous.
""".strip()


S1_KNOWLEDGE_TEMPLATE = """
S1: Internal Knowledge Retrieval.

Task:
- Retrieve internal domain knowledge relevant to the user's statement.
- Knowledge must come from your internal model knowledge base.
- Focus on mechanisms, constraints, and known trade-offs that can affect validity.
- Keep each item atomic and reusable for downstream logic analysis.

Return this exact JSON schema:
{{
  "internal_knowledge": [
    {{
      "item": "string",
      "relevance": "string",
      "confidence": "high | medium | low"
    }}
  ],
  "knowledge_gaps": ["string"]
}}

Output language: {output_language}

User statement:
{user_input}
""".strip()


PHASE_1_TEMPLATE = """
Phase I: Premise Extraction & Axiomatization.

Task:
- First, read and trust the provided S1 internal knowledge retrieval.
- Read the user's statement.
- Identify the explicit goal.
- Identify core variables.
- Identify hidden assumptions needed for success.
- Identify reality gaps between statement and known system behavior.
- Explicitly state which S1 internal knowledge items are used.

Return this exact JSON schema:
{{
  "stated_goal": "string",
  "core_variables": ["string"],
  "internal_knowledge_used": ["string"],
  "hidden_assumptions": ["string"],
  "reality_gaps": ["string"]
}}

Output language: {output_language}

S1 internal knowledge retrieval:
{s1_knowledge_json}

User statement:
{user_input}
""".strip()


PHASE_2_TEMPLATE = """
Phase II: Multi-Dimensional Expansion (constrained Tree of Thoughts).

Task:
- Infer multiple different outcomes caused by the premise.
- Keep each branch logically distinct.
- Focus on consequences and impact on the stated goal.
- Every branch must include both `result` and `goal_impact`. Do not omit fields.

Return this exact JSON schema:
{{
  "branches": [
    {{
      "name": "string",
      "result": "string",
      "goal_impact": "string"
    }}
  ]
}}

Output language: {output_language}

Phase I result:
{phase_1_json}

User statement:
{user_input}
""".strip()


PHASE_3_TEMPLATE = """
Phase III: Contradiction Catching & Mitigation.

Classify paradox type by protocol:
- Antinomy: Goal X implies destruction of Goal X (self-contradiction).
- Falsidical: Looks valid but depends on false hidden assumption.
- Veridical: Counterintuitive but technically valid trade-off.
- None: no paradox detected under tested branches.

Return this exact JSON schema:
{{
  "paradox_type": "Antinomy | Falsidical | Veridical | None",
  "reasoning": "string",
  "contradiction_path": ["string"],
  "mitigation": ["string"]
}}

Output language: {output_language}

Phase I result:
{phase_1_json}

Phase II result:
{phase_2_json}

User statement:
{user_input}
""".strip()
