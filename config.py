import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

# Storage Paths
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
DATA_DIR.mkdir(exist_ok=True)
UPLOADS_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = DATA_DIR / "app.db"

# LLM Configuration (Free / Local first)
# Default is Ollama with local model llama3.2 or qwen2.5
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "llama3.2")
# Fallback provider: "ollama", "groq", "gemini"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Embeddings & Vector DB
# Free HuggingFace / sentence-transformers CPU model
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2")
CHROMA_PERSIST_DIR = DATA_DIR / "chroma_db"
CHROMA_PERSIST_DIR.mkdir(exist_ok=True)

# Chunking Config
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "600"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "100"))

# OCR Configuration
TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")

# Supported Subjects Limit
MAX_SUBJECTS = 5
DEFAULT_SUBJECTS = [
    "Data Structures & Algorithms",
    "Database Management Systems",
    "Operating Systems",
    "Computer Networks",
    "Machine Learning"
]

# Bloom's Taxonomy Levels
BLOOMS_LEVELS = [
    "Remember",
    "Understand",
    "Apply",
    "Analyze",
    "Evaluate",
    "Create"
]

BLOOM_ACTION_VERBS = {
    "Remember": ["Define", "List", "State", "Identify", "Recall", "Name"],
    "Understand": ["Explain", "Describe", "Discuss", "Distinguish", "Summarize", "Illustrate"],
    "Apply": ["Demonstrate", "Calculate", "Solve", "Implement", "Apply", "Construct"],
    "Analyze": ["Analyze", "Compare", "Contrast", "Differentiate", "Deconstruct", "Categorize"],
    "Evaluate": ["Evaluate", "Justify", "Assess", "Critique", "Defend", "Determine"],
    "Create": ["Design", "Formulate", "Develop", "Propose", "Synthesize", "Construct"]
}
