import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config import (
    BASE_DIR, UPLOADS_DIR, DATA_DIR,
    DEFAULT_LLM_MODEL, EMBEDDING_MODEL_NAME
)
from db.database import init_db, get_db_connection
from ingestion.parser import parse_syllabus_file
from ingestion.structure_extractor import extract_units, extract_course_outcomes
from rag.vector_store import SubjectVectorIndex, chunk_text_with_metadata
from generation.generator import (
    generate_full_question_paper,
    refine_single_question,
    compute_blueprint
)
from export.document_exporter import export_to_pdf, export_to_docx

# Initialize FastAPI application
app = FastAPI(title="Automated Question Paper Generator")

# Initialize database safely
try:
    init_db()
except Exception as e:
    print(f"Database init warning: {e}")

# Mount static and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Pydantic Request Models
class UserAuthRequest(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = "Professor"

class ExamGenerateRequest(BaseModel):
    subject_id: int
    college_name: str
    exam_name: str
    subject_code: str
    duration_minutes: int
    blooms_distribution: str
    sections: List[Dict[str, Any]]

class RefineQuestionRequest(BaseModel):
    subject_id: int
    question: Dict[str, Any]
    instruction: str

class RecomputeBlueprintRequest(BaseModel):
    questions: List[Dict[str, Any]]

# ROUTES
@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))

# AUTHENTICATION (Accepts any credentials and logs in/creates record)
@app.post("/api/auth/login")
async def auth_login(req: UserAuthRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (req.username,))
    row = cursor.fetchone()

    if not row:
        # Auto-register user
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name) VALUES (?, ?, ?)",
            (req.username, "plain_demo_hash", req.full_name or req.username)
        )
        conn.commit()
        user_id = cursor.lastrowid
        user_data = {"id": user_id, "username": req.username, "full_name": req.full_name or req.username}
    else:
        user_data = {"id": row["id"], "username": row["username"], "full_name": row["full_name"]}

    conn.close()
    return {"status": "success", "user": user_data}

# 1. SUBJECTS MANAGEMENT
@app.get("/api/subjects")
async def list_subjects():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, code, syllabus_file, co_list, chunk_count, updated_at FROM subjects ORDER BY id ASC")
    rows = cursor.fetchall()
    subjects = []
    for r in rows:
        subjects.append({
            "id": r["id"],
            "name": r["name"],
            "code": r["code"],
            "syllabus_file": r["syllabus_file"],
            "co_list": json.loads(r["co_list"]) if r["co_list"] else [],
            "chunk_count": r["chunk_count"],
            "updated_at": r["updated_at"]
        })
    conn.close()
    return {"subjects": subjects}

# 2. SYLLABUS UPLOAD & INGESTION
@app.post("/api/syllabus/upload")
async def upload_syllabus(file: UploadFile = File(...), subject_id: int = Form(...)):
    # Check subject exists
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE id = ?", (subject_id,))
    subj = cursor.fetchone()
    if not subj:
        conn.close()
        raise HTTPException(status_code=404, detail="Target subject not found")

    # Save uploaded file
    file_ext = Path(file.filename).suffix.lower()
    saved_filename = f"subject_{subject_id}_{file.filename}"
    saved_path = UPLOADS_DIR / saved_filename

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Parse content from file (supports PDF, DOCX, PPTX, XLSX, TXT, OCR)
        extracted_text, pages_data = parse_syllabus_file(saved_path)
        if not extracted_text.strip():
            raise ValueError("No text could be extracted from the file.")

        # Extract Course Outcomes (CO1..CO5)
        cos = extract_course_outcomes(extracted_text)

        # Chunk text and build isolated subject vector index
        chunks = chunk_text_with_metadata(
            full_text=extracted_text,
            subject_id=subject_id,
            subject_name=subj["name"]
        )

        vector_index = SubjectVectorIndex(subject_id)
        vector_index.build_index(chunks)

        # Update database with syllabus info
        cursor.execute("""
            UPDATE subjects
            SET syllabus_file = ?,
                syllabus_raw_text = ?,
                co_list = ?,
                chunk_count = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (
            file.filename,
            extracted_text[:10000], # Preview storage
            json.dumps(cos),
            len(chunks),
            subject_id
        ))
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "message": f"Successfully ingested and indexed {len(chunks)} chunks for {subj['name']}",
            "chunk_count": len(chunks),
            "extracted_preview": extracted_text[:2000],
            "course_outcomes": cos
        }

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=400, detail=f"Syllabus extraction failed: {str(e)}")

# 3. QUESTION PAPER GENERATION
@app.post("/api/paper/generate")
async def generate_paper_api(req: ExamGenerateRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM subjects WHERE id = ?", (req.subject_id,))
    subj = cursor.fetchone()
    if not subj:
        conn.close()
        raise HTTPException(status_code=404, detail="Subject not found")

    co_data = json.loads(subj["co_list"]) if subj["co_list"] else []
    co_keys = [c.get("co_id", f"CO{i+1}") for i, c in enumerate(co_data)] or ["CO1", "CO2", "CO3", "CO4", "CO5"]

    exam_settings = {
        "college_name": req.college_name,
        "exam_name": req.exam_name,
        "subject_code": req.subject_code,
        "duration_minutes": req.duration_minutes,
        "blooms_distribution": req.blooms_distribution,
        "sections": req.sections,
        "co_list": co_keys
    }

    try:
        paper_result = generate_full_question_paper(
            subject_id=req.subject_id,
            subject_name=subj["name"],
            exam_settings=exam_settings
        )

        # Save generated paper to SQLite history
        cursor.execute("""
            INSERT INTO question_papers (
                subject_id, exam_name, college_name, subject_code,
                duration_minutes, total_marks, settings_json, blueprint_json,
                questions_json, answer_key_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            req.subject_id,
            req.exam_name,
            req.college_name,
            req.subject_code,
            req.duration_minutes,
            paper_result["total_marks"],
            json.dumps(exam_settings),
            json.dumps(paper_result["blueprint"]),
            json.dumps(paper_result["sections"]),
            json.dumps(paper_result["all_questions"])
        ))
        conn.commit()
        paper_id = cursor.lastrowid
        conn.close()

        paper_result["paper_id"] = paper_id
        return paper_result

    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

# 4. QUESTION REFINEMENT
@app.post("/api/paper/refine-question")
async def refine_question_api(req: RefineQuestionRequest):
    try:
        refined = refine_single_question(
            subject_id=req.subject_id,
            original_question=req.question,
            instruction=req.instruction
        )
        return refined
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Refinement failed: {str(e)}")

@app.post("/api/paper/recompute-blueprint")
async def recompute_blueprint_api(req: RecomputeBlueprintRequest):
    return compute_blueprint(req.questions)

# 5. EXPORT
@app.post("/api/paper/export")
async def export_paper_api(paper_data: Dict[str, Any], format: str = Query("pdf")):
    exports_dir = DATA_DIR / "exports"
    exports_dir.mkdir(exist_ok=True)

    subj_code = paper_data.get("subject_code", "EXAM")
    
    if format.lower() == "pdf":
        out_file = exports_dir / f"Question_Paper_{subj_code}.pdf"
        export_to_pdf(paper_data, out_file, include_answers=True)
        return FileResponse(
            path=str(out_file),
            filename=f"Question_Paper_{subj_code}.pdf",
            media_type="application/pdf"
        )
    elif format.lower() == "docx":
        out_file = exports_dir / f"Question_Paper_{subj_code}.docx"
        export_to_docx(paper_data, out_file, include_answers=True)
        return FileResponse(
            path=str(out_file),
            filename=f"Question_Paper_{subj_code}.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'pdf' or 'docx'.")

# 6. HISTORY
@app.get("/api/papers/history")
async def get_history():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT qp.id, qp.exam_name, qp.subject_code, qp.total_marks, qp.created_at, s.name as subject_name
        FROM question_papers qp
        JOIN subjects s ON qp.subject_id = s.id
        ORDER BY qp.id DESC
    """)
    rows = cursor.fetchall()
    papers = [dict(r) for r in rows]
    conn.close()
    return {"papers": papers}

@app.get("/api/papers/{paper_id}")
async def get_paper_by_id(paper_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT qp.*, s.name as subject_name
        FROM question_papers qp
        JOIN subjects s ON qp.subject_id = s.id
        WHERE qp.id = ?
    """, (paper_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Paper not found")

    return {
        "id": row["id"],
        "subject_id": row["subject_id"],
        "subject_name": row["subject_name"],
        "exam_name": row["exam_name"],
        "college_name": row["college_name"],
        "subject_code": row["subject_code"],
        "duration_minutes": row["duration_minutes"],
        "total_marks": row["total_marks"],
        "sections": json.loads(row["questions_json"]),
        "all_questions": json.loads(row["answer_key_json"]),
        "blueprint": json.loads(row["blueprint_json"]) if row["blueprint_json"] else {},
        "created_at": row["created_at"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
