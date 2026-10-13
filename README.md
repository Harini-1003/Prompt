# AutoExam RAG: Automated Question Paper Generator

A production-grade, 100% free and open-source web application for university examination paper generation using **Retrieval-Augmented Generation (RAG)**, **Course Outcomes (CO)**, and **Bloom's Taxonomy**.

---

## 🌟 Key Features

1. **5 Isolated Subjects**: Data Structures & Algorithms, DBMS, Operating Systems, Computer Networks, and Machine Learning. Each subject maintains an independent vector store.
2. **Universal Ingestion & OCR**: Supports **PDF, DOCX, PPTX, TXT, MD, XLSX, CSV, JPG, PNG** with automatic Tesseract OCR for scanned documents.
3. **Strict Syllabus Grounding**: Questions are generated strictly from the uploaded curriculum without hallucination.
4. **Bloom's Taxonomy & NBA Mapping**: Distribute weightages across *Remember, Understand, Apply, Analyze, Evaluate, and Create* with automatic Course Outcome (CO1–CO5) mapping.
5. **Blueprint / Matrix View**: Instant visual verification table showing CO vs Bloom's Level vs Marks with automated gap warnings.
6. **Refinement & Regeneration**: Pick any single question and command the model to make it harder, easier, change Bloom's level, or transform into an industry case study.
7. **University Export (PDF & DOCX)**: Download exam papers formatted with university headers, marks breakdown, instructions, and confidential answer keys.
8. **Authentication & Landing Page**: Modern landing page with sign-in and sign-up modal (accepts any credentials and logs in immediately).
9. **SQLite History**: All generated question papers are stored in a local SQLite database for revisiting anytime.

---

## 🛠️ Tech Stack (100% Free & Open-Source)

- **Backend**: FastAPI with Python 3.10+
- **Frontend**: Responsive modern UI (HTML5, Vanilla JavaScript, CSS3, FontAwesome)
- **Local LLM**: [Ollama](https://ollama.com/) running `llama3.2` or `qwen2.5` (zero cost, no API keys needed). Includes a robust offline fallback rules engine.
- **Embeddings**: `sentence-transformers` with model `all-MiniLM-L6-v2` (runs entirely on CPU).
- **Vector DB**: Isolated cosine vector indexing with metadata tagging.
- **Document Parsing**: `pypdf`, `pdfplumber`, `python-docx`, `python-pptx`, `pandas`, `openpyxl`.
- **OCR Engine**: `pytesseract` with Google Tesseract-OCR.
- **Export**: `reportlab`, `python-docx`.
- **Database**: SQLite.

---

## 🚀 Step-by-Step Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/Harini-1003/Prompt.git
cd Prompt
```

### 2. Install Python Dependencies
```bash
python -m pip install -r requirements.txt
```

### 3. (Optional) Install Tesseract OCR for Image/Scanned PDF Ingestion
- **Windows**: Download the installer from [UB-Mannheim Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) and install to `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- **Linux/Ubuntu**:
  ```bash
  sudo apt-get update && sudo apt-get install -y tesseract-ocr
  ```
- **macOS**:
  ```bash
  brew install tesseract
  ```

### 4. Install Ollama and Pull the Free Model
1. Download Ollama from [https://ollama.com/download](https://ollama.com/download)
2. Open your terminal and pull the local open-source model:
   ```bash
   ollama pull llama3.2
   ```
   *(Or alternatively: `ollama pull qwen2.5`)*
3. Make sure Ollama is running (`ollama serve`).

*(Note: If you run without Ollama started, the application's built-in intelligent syllabus extractor and fallback engine will still generate grounded questions!)*

### 5. Launch the Web Application
```bash
python app.py
```
Open your web browser at:
```
http://localhost:8000
```

---

## 🧪 Short Demo Flow

1. **Sign In**: Click **Quick Login** or **Sign In** on the landing page. Enter any username and password to enter the dashboard.
2. **Select Subject**: View the 5 default subjects (*Data Structures, DBMS, OS, Networks, ML*).
3. **Upload Syllabus**:
   - Go to **2. Upload Syllabus**.
   - Select a subject (e.g., *Data Structures & Algorithms*).
   - Drag and drop any syllabus file (e.g., PDF, DOCX, or text outline).
   - Click **Parse, Chunk & Embed Syllabus**. The app extracts text, splits into chunks with metadata, generates local CPU embeddings, and extracts CO1–CO5.
4. **Generate Paper**:
   - Navigate to **3. Generate Paper**.
   - Customize question counts and marks for **Part A (Short Answer)**, **Part B (Medium Analytical)**, and **Part C (Case Study)**.
   - Select desired Bloom's taxonomy cognitive levels.
   - Click **Generate Grounded Question Paper**.
5. **Review Blueprint & Refine**:
   - Check the **CO vs Bloom's Matrix** for syllabus coverage.
   - Pick any question and click **Refine**. Request *"Make this question harder and frame as an industrial case study"*. Only that question is replaced!
6. **Export**:
   - Click **Download PDF** or **Download DOCX** to download the official university-formatted question paper with confidential answer key.
7. **History**:
   - Visit the **History** tab to see previously generated examination papers saved in SQLite.
