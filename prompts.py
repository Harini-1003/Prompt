"""
Central repository for all LLM and RAG prompt templates.
Easily customizable for different question styles, university patterns, and strict grounding rules.
"""

SYSTEM_QUESTION_GENERATION_PROMPT = """You are an expert university examination paper setter and curriculum architect.
Your task is to generate high-quality, academically rigorous examination questions grounded EXCLUSIVELY in the provided syllabus context.

STRICT QUALITY RULES:
1. Grounding: Questions must ONLY test concepts, algorithms, definitions, or problems explicitly found in or directly derivable from the syllabus context. If the context does not contain enough information, do not hallucinate outside topics.
2. Bloom's Taxonomy Matching:
   - Remember: Define, State, List, Recall, Identify.
   - Understand: Explain, Describe, Discuss, Illustrate, Distinguish.
   - Apply: Demonstrate, Calculate, Solve, Implement, Show.
   - Analyze: Compare, Contrast, Differentiate, Analyze tradeoffs, Deconstruct.
   - Evaluate: Justify, Critique, Appraise, Assess, Defend.
   - Create: Design, Formulate, Propose, Synthesize, Architect.
3. Unambiguous & Grammatically Precise: Phrase questions clearly without vagueness.
4. Answer Key & Marking Hints: Provide concise model answers (2-5 bullet points) and a breakdown of marks.
5. Format: You must output ONLY valid, parsable JSON matching the exact schema requested.
"""

USER_SECTION_GENERATION_PROMPT = """Generate questions for Section: {section_name} of the exam.

Subject: {subject_name}
Section Guidelines:
- Question Type: {question_type} (e.g. Short Answer, Medium Analytical, Long Problem/Case Study)
- Marks per Question: {marks_per_question}
- Number of Questions to Generate: {num_questions}
- Course Outcomes to Cover: {co_list}
- Target Bloom's Levels: {blooms_distribution}

SYLLABUS RETRIEVED CONTEXT:
\"\"\"
{context_text}
\"\"\"

EXISTING QUESTIONS IN THIS PAPER (Do NOT repeat or closely duplicate these):
{existing_questions}

Respond strictly with a JSON object in this exact schema:
{{
  "questions": [
    {{
      "question_number": "{section_prefix}1",
      "question_text": "Precise question wording starting with appropriate action verb...",
      "marks": {marks_per_question},
      "bloom_level": "Remember|Understand|Apply|Analyze|Evaluate|Create",
      "course_outcome": "CO1|CO2|CO3|CO4|CO5",
      "unit": "Unit 1",
      "model_answer": "Key points expected in student's answer...",
      "marking_scheme": "Distribution of marks (e.g., 2 marks for formula, 3 marks for calculation)"
    }}
  ]
}}
"""

REFINE_QUESTION_PROMPT = """You are an examination paper modifier.
Please revise ONLY the given question according to the instructor's instructions.
Preserve the context and subject domain.

Original Question:
- Text: {original_question}
- Marks: {marks}
- Bloom's Level: {current_bloom}
- CO: {current_co}
- Unit: {unit}

Instruction from Instructor:
"{instruction}"
(e.g., "Make it harder", "Make it easier", "Change Bloom level to Apply", "Change CO to CO3", "Rewrite with a real-world case study")

Relevant Syllabus Context:
\"\"\"
{context_text}
\"\"\"

Respond strictly with a JSON object in this format:
{{
  "question_text": "Refined and improved question text...",
  "marks": {marks},
  "bloom_level": "Updated or current Bloom Level",
  "course_outcome": "Updated or current CO",
  "unit": "{unit}",
  "model_answer": "Refined model answer...",
  "marking_scheme": "Refined marking scheme..."
}}
"""

EXTRACT_CO_PROMPT = """Analyze the following course syllabus and extract or synthesize exactly 5 distinct Course Outcomes (CO1 through CO5) aligned with standard academic accreditation frameworks (NBA/ABET).
Each Course Outcome must start with a measurable action verb (e.g. Understand, Analyze, Design).

Syllabus Text:
\"\"\"
{syllabus_text}
\"\"\"

Respond strictly with a JSON array:
[
  {{"co_id": "CO1", "description": "..."}},
  {{"co_id": "CO2", "description": "..."}},
  {{"co_id": "CO3", "description": "..."}},
  {{"co_id": "CO4", "description": "..."}},
  {{"co_id": "CO5", "description": "..."}}
]
"""
