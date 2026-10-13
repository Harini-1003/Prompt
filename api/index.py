import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app import app

# Also mount root handler directly inside api/index.py for direct routing
@app.get("/api/index")
async def api_index():
    from fastapi.responses import HTMLResponse
    index_path = BASE_DIR / "templates" / "index.html"
    return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
