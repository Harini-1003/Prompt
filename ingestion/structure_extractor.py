import re
from typing import List, Dict, Any

UNIT_PATTERNS = [
    r'(?i)(?:unit|module|chapter|part)\s*[-:]?\s*([0-9ivxlcdm]+)\s*[:\-\.]?\s*(.*?)(?=(?:unit|module|chapter|part)\s*[-:]?\s*[0-9ivxlcdm]+|\Z)',
    r'(?i)(?:section)\s*[-:]?\s*([0-9ivxlcdm]+)\s*[:\-\.]?\s*(.*?)(?=(?:section)\s*[-:]?\s*[0-9ivxlcdm]+|\Z)'
]

CO_PATTERNS = [
    r'(?i)(?:course\s*outcome\s*[-:]?\s*|co\s*[-:]?\s*)([0-9]+)\s*[:\-\.]?\s*(.*?)(?=(?:course\s*outcome|co\s*[-:]?\s*[0-9]+)|\n\n|\Z)'
]

def extract_units(text: str) -> List[Dict[str, Any]]:
    """
    Detect Units / Modules from text.
    If no standard units pattern is found, falls back to splitting into synthetic equal units.
    """
    units = []
    for pattern in UNIT_PATTERNS:
        matches = list(re.finditer(pattern, text, re.DOTALL))
        if matches:
            for m in matches:
                unit_num = m.group(1).strip()
                unit_content = m.group(2).strip()
                # Find topic title if present on first line
                lines = unit_content.split('\n')
                title = lines[0].strip() if lines else f"Unit {unit_num}"
                units.append({
                    "unit": f"Unit {unit_num}",
                    "title": title[:100],
                    "content": unit_content
                })
            break
            
    if not units:
        # Fallback: create 5 balanced units if text is substantial
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if len(paragraphs) >= 5:
            k = len(paragraphs) // 5
            for i in range(5):
                chunk = "\n\n".join(paragraphs[i*k : (i+1)*k if i < 4 else len(paragraphs)])
                first_line = chunk.split('\n')[0][:80]
                units.append({
                    "unit": f"Unit {i+1}",
                    "title": first_line or f"Module {i+1}",
                    "content": chunk
                })
        else:
            units.append({
                "unit": "Unit 1",
                "title": "General Syllabus Content",
                "content": text
            })
            
    return units

def extract_course_outcomes(text: str) -> List[Dict[str, str]]:
    """
    Extract CO1 - CO5 descriptions if available in text.
    """
    cos = []
    matches = list(re.finditer(CO_PATTERNS[0], text, re.DOTALL))
    if matches:
        for m in matches:
            co_num = m.group(1).strip()
            co_text = m.group(2).strip().split('\n')[0] # First sentence or line
            cos.append({
                "co_id": f"CO{co_num}",
                "description": co_text.strip()
            })
            
    # Normalize to at least CO1..CO5 if none or fewer found
    if len(cos) < 5:
        defaults = [
            ("CO1", "Understand and recall fundamental concepts and principles."),
            ("CO2", "Explain and interpret core architectures and theoretical models."),
            ("CO3", "Apply methodologies and algorithms to solve practical problems."),
            ("CO4", "Analyze performance, design tradeoffs, and complex structures."),
            ("CO5", "Design and evaluate robust systems, frameworks, or solutions.")
        ]
        existing_ids = {c["co_id"] for c in cos}
        for def_id, def_desc in defaults:
            if def_id not in existing_ids:
                cos.append({"co_id": def_id, "description": def_desc})
                
    # Sort by CO index
    cos = sorted(cos, key=lambda x: x["co_id"])
    return cos[:5]
