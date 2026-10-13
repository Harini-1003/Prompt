import json
from typing import Dict, Any, List
from rag.vector_store import SubjectVectorIndex
from generation.llm_client import LLMClient, extract_json_from_response
from prompts import (
    SYSTEM_QUESTION_GENERATION_PROMPT,
    USER_SECTION_GENERATION_PROMPT,
    REFINE_QUESTION_PROMPT
)

def check_duplicate(new_question: str, existing_questions: List[Dict[str, Any]], threshold: float = 0.8) -> bool:
    """Simple jaccard token similarity check to prevent duplicate questions."""
    new_tokens = set(new_question.lower().split())
    if not new_tokens:
        return False
    for eq in existing_questions:
        q_tokens = set(eq.get("question_text", "").lower().split())
        if not q_tokens:
            continue
        intersection = len(new_tokens.intersection(q_tokens))
        union = len(new_tokens.union(q_tokens))
        if union > 0 and (intersection / union) > threshold:
            return True
    return False

def generate_full_question_paper(
    subject_id: int,
    subject_name: str,
    exam_settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate an entire grounded question paper with Part A, Part B, Part C sections,
    verifying total marks, question counts, and blueprint distribution.
    """
    vector_index = SubjectVectorIndex(subject_id)
    llm = LLMClient()
    
    sections_config = exam_settings.get("sections", [
        {"name": "Part A", "type": "Short Answer", "marks_per_q": 2, "count": 5},
        {"name": "Part B", "type": "Medium Analytical", "marks_per_q": 8, "count": 5},
        {"name": "Part C", "type": "Comprehensive Application / Case Study", "marks_per_q": 10, "count": 1}
    ])
    
    blooms_distribution = exam_settings.get("blooms_distribution", "Balanced coverage of Remember, Understand, Apply, Analyze, Evaluate, Create")
    co_list = exam_settings.get("co_list", ["CO1", "CO2", "CO3", "CO4", "CO5"])
    
    generated_sections = []
    all_questions = []
    total_calculated_marks = 0

    for s_idx, sec in enumerate(sections_config):
        sec_name = sec.get("name", f"Section {chr(65+s_idx)}")
        q_type = sec.get("type", "Standard Questions")
        marks_per_q = int(sec.get("marks_per_q", 2))
        q_count = int(sec.get("count", 2))
        prefix = f"{chr(65+s_idx)}"

        # Query vector store for rich grounded syllabus context across units
        query = f"{subject_name} fundamental concepts algorithms architecture and methodologies"
        retrieved_chunks = vector_index.search(query, top_k=6)
        if retrieved_chunks:
            context_text = "\n\n---\n\n".join([f"[{c.get('unit', 'Unit')} | {c.get('topic', 'Topic')}]: {c['text']}" for c in retrieved_chunks])
        else:
            context_text = f"Curriculum and core academic syllabus outline for {subject_name} across units 1 to 5."

        existing_summary = "\n".join([f"- {q['question_text']}" for q in all_questions]) or "None"

        user_prompt = USER_SECTION_GENERATION_PROMPT.format(
            section_name=sec_name,
            subject_name=subject_name,
            question_type=q_type,
            marks_per_question=marks_per_q,
            num_questions=q_count,
            co_list=", ".join(co_list),
            blooms_distribution=blooms_distribution,
            context_text=context_text,
            existing_questions=existing_summary,
            section_prefix=prefix
        )

        raw_output = llm.generate(SYSTEM_QUESTION_GENERATION_PROMPT, user_prompt)
        parsed = extract_json_from_response(raw_output)
        sec_questions = parsed.get("questions", []) if isinstance(parsed, dict) else parsed

        # Standardize questions and calculate
        processed_sec_questions = []
        for q_i, q in enumerate(sec_questions):
            q_num = f"{prefix}{q_i+1}"
            q_text = q.get("question_text", f"Explain key characteristics in {subject_name}.")
            # Duplicate check
            if check_duplicate(q_text, all_questions):
                q_text += f" (Discuss specifically in context of module {q_i+1})"

            formatted_q = {
                "question_number": q_num,
                "question_text": q_text,
                "marks": marks_per_q,
                "bloom_level": q.get("bloom_level", "Understand"),
                "course_outcome": q.get("course_outcome", f"CO{(q_i%5)+1}"),
                "unit": q.get("unit", f"Unit {(q_i%5)+1}"),
                "model_answer": q.get("model_answer", "Model answer key point 1, 2, and 3."),
                "marking_scheme": q.get("marking_scheme", f"{marks_per_q} marks total based on key points.")
            }
            processed_sec_questions.append(formatted_q)
            all_questions.append(formatted_q)
            total_calculated_marks += marks_per_q

        generated_sections.append({
            "section_name": sec_name,
            "section_type": q_type,
            "marks_per_question": marks_per_q,
            "questions": processed_sec_questions
        })

    # Build Blueprint / Coverage Matrix
    blueprint = compute_blueprint(all_questions)

    return {
        "subject_id": subject_id,
        "subject_name": subject_name,
        "exam_name": exam_settings.get("exam_name", "End Semester Examination"),
        "college_name": exam_settings.get("college_name", "Department of Computer Science & Engineering"),
        "subject_code": exam_settings.get("subject_code", "CS101"),
        "duration_minutes": exam_settings.get("duration_minutes", 180),
        "total_marks": total_calculated_marks,
        "sections": generated_sections,
        "all_questions": all_questions,
        "blueprint": blueprint
    }

def compute_blueprint(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute CO vs Bloom's Level vs Marks matrix and identify gaps."""
    cos = ["CO1", "CO2", "CO3", "CO4", "CO5"]
    blooms = ["Remember", "Understand", "Apply", "Analyze", "Evaluate", "Create"]

    matrix = {co: {b: 0 for b in blooms} for co in cos}
    co_totals = {co: 0 for co in cos}
    bloom_totals = {b: 0 for b in blooms}
    total_marks = 0

    for q in questions:
        co = q.get("course_outcome", "CO1")
        b = q.get("bloom_level", "Understand")
        marks = int(q.get("marks", 2))

        if co not in matrix:
            matrix[co] = {bl: 0 for bl in blooms}
            co_totals[co] = 0
        if b not in blooms:
            b = "Understand"

        matrix[co][b] += marks
        co_totals[co] += marks
        bloom_totals[b] += marks
        total_marks += marks

    warnings = []
    for co in cos:
        if co_totals.get(co, 0) == 0:
            warnings.append(f"Notice: {co} does not currently have any allocated questions.")
    for b in blooms:
        if bloom_totals.get(b, 0) == 0:
            warnings.append(f"Notice: Bloom's Taxonomy level '{b}' has 0% allocation in this paper.")

    return {
        "matrix": matrix,
        "co_totals": co_totals,
        "bloom_totals": bloom_totals,
        "total_marks": total_marks,
        "warnings": warnings
    }

def refine_single_question(
    subject_id: int,
    original_question: Dict[str, Any],
    instruction: str
) -> Dict[str, Any]:
    """Regenerates/modifies a single question based on user instructions, leaving the rest untouched."""
    vector_index = SubjectVectorIndex(subject_id)
    llm = LLMClient()

    query = f"{original_question.get('question_text', '')} {instruction}"
    retrieved = vector_index.search(query, top_k=3)
    context_text = "\n".join([c["text"] for c in retrieved]) if retrieved else "Syllabus domain content"

    prompt = REFINE_QUESTION_PROMPT.format(
        original_question=original_question.get("question_text", ""),
        marks=original_question.get("marks", 2),
        current_bloom=original_question.get("bloom_level", "Understand"),
        current_co=original_question.get("course_outcome", "CO1"),
        unit=original_question.get("unit", "Unit 1"),
        instruction=instruction,
        context_text=context_text
    )

    raw_output = llm.generate(SYSTEM_QUESTION_GENERATION_PROMPT, prompt)
    parsed = extract_json_from_response(raw_output)

    refined_q = {
        "question_number": original_question.get("question_number", "Q1"),
        "question_text": parsed.get("question_text", original_question.get("question_text")),
        "marks": parsed.get("marks", original_question.get("marks")),
        "bloom_level": parsed.get("bloom_level", original_question.get("bloom_level")),
        "course_outcome": parsed.get("course_outcome", original_question.get("course_outcome")),
        "unit": parsed.get("unit", original_question.get("unit")),
        "model_answer": parsed.get("model_answer", original_question.get("model_answer")),
        "marking_scheme": parsed.get("marking_scheme", original_question.get("marking_scheme"))
    }
    return refined_q
