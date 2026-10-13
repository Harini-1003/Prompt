import sqlite3
import json
from datetime import datetime
from config import DB_PATH, DEFAULT_SUBJECTS

def get_db_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Subjects table (exactly 5 configurable subjects)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        code TEXT,
        syllabus_file TEXT,
        syllabus_raw_text TEXT,
        co_list TEXT, -- JSON array of {"co_id": "CO1", "description": "..."}
        chunk_count INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Question Papers table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS question_papers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject_id INTEGER NOT NULL,
        exam_name TEXT NOT NULL,
        college_name TEXT,
        subject_code TEXT,
        duration_minutes INTEGER DEFAULT 180,
        total_marks INTEGER NOT NULL,
        settings_json TEXT NOT NULL,
        blueprint_json TEXT,
        questions_json TEXT NOT NULL,
        answer_key_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (subject_id) REFERENCES subjects(id)
    )
    """)
    
    # Seed default 5 subjects if empty
    cursor.execute("SELECT COUNT(*) as count FROM subjects")
    count = cursor.fetchone()["count"]
    if count == 0:
        for subj in DEFAULT_SUBJECTS:
            cursor.execute("""
            INSERT INTO subjects (name, code, co_list)
            VALUES (?, ?, ?)
            """, (
                subj,
                "".join([w[0].upper() for w in subj.split() if w[0].isalpha()]),
                json.dumps([
                    {"co_id": "CO1", "description": f"Understand core foundations and theories of {subj}."},
                    {"co_id": "CO2", "description": f"Apply design concepts and algorithms in {subj}."},
                    {"co_id": "CO3", "description": f"Analyze methodologies and architectural paradigms of {subj}."},
                    {"co_id": "CO4", "description": f"Evaluate comparative approaches and solutions in {subj}."},
                    {"co_id": "CO5", "description": f"Design and synthesize comprehensive frameworks for {subj}."}
                ])
            ))
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
