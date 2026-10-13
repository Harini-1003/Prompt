import os
import re
from pathlib import Path
from typing import Tuple, List, Dict, Any

# Optional OCR
try:
    import pytesseract
    from PIL import Image
    from config import TESSERACT_CMD
    if os.path.exists(TESSERACT_CMD):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

def clean_extracted_text(text: str) -> str:
    """
    Clean extracted text: remove redundant header/footers, page markers, excessive newlines.
    """
    if not text:
        return ""
    # Normalize line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Remove repetitive page markers e.g. "Page 1 of 5", "- 2 -", "Page 3"
    text = re.sub(r'(?i)\bpage\s+\d+(\s+of\s+\d+)?\b', '', text)
    text = re.sub(r'^\s*-\s*\d+\s*-\s*$', '', text, flags=re.MULTILINE)
    # Remove recurring header/footer border lines
    text = re.sub(r'_{3,}', '', text)
    text = re.sub(r'-{4,}', '', text)
    text = re.sub(r'={4,}', '', text)
    # Reduce consecutive whitespaces and newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def extract_from_pdf(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text from PDF via pdfplumber/pypdf with OCR fallback if scanned."""
    pages_data = []
    full_text = []
    
    # Try pdfplumber first
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for idx, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if not text.strip() and OCR_AVAILABLE:
                    # Attempt OCR on scanned page image
                    try:
                        img = page.to_image(resolution=200).original
                        text = pytesseract.image_to_string(img)
                    except Exception:
                        pass
                cleaned = clean_extracted_text(text)
                pages_data.append({"page": idx + 1, "text": cleaned})
                full_text.append(cleaned)
    except Exception as e:
        # Fallback to pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(str(file_path))
            for idx, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                cleaned = clean_extracted_text(text)
                pages_data.append({"page": idx + 1, "text": cleaned})
                full_text.append(cleaned)
        except Exception as e2:
            raise ValueError(f"Failed to read PDF file: {e2}")

    return "\n\n".join(full_text), pages_data

def extract_from_docx(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text from Word DOCX file."""
    try:
        import docx
        doc = docx.Document(str(file_path))
        paragraphs = []
        for p in doc.paragraphs:
            if p.text.strip():
                paragraphs.append(p.text.strip())
        
        # Also extract table cells
        for table in doc.tables:
            for row in table.rows:
                row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                if row_text:
                    paragraphs.append(row_text)
                    
        text = "\n\n".join(paragraphs)
        cleaned = clean_extracted_text(text)
        return cleaned, [{"page": 1, "text": cleaned}]
    except Exception as e:
        raise ValueError(f"Failed to read DOCX file: {e}")

def extract_from_pptx(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text from PowerPoint PPTX file."""
    try:
        from pptx import Presentation
        prs = Presentation(str(file_path))
        pages_data = []
        full_text = []
        for idx, slide in enumerate(prs.slides):
            slide_texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    slide_texts.append(shape.text.strip())
            joined = "\n".join(slide_texts)
            cleaned = clean_extracted_text(joined)
            pages_data.append({"page": idx + 1, "text": cleaned})
            full_text.append(cleaned)
        return "\n\n".join(full_text), pages_data
    except Exception as e:
        raise ValueError(f"Failed to read PPTX file: {e}")

def extract_from_spreadsheet(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text from CSV or Excel file."""
    try:
        import pandas as pd
        if file_path.suffix.lower() == ".csv":
            df = pd.read_csv(str(file_path))
        else:
            df = pd.read_excel(str(file_path))
        text = df.to_string(index=False)
        cleaned = clean_extracted_text(text)
        return cleaned, [{"page": 1, "text": cleaned}]
    except Exception as e:
        raise ValueError(f"Failed to read spreadsheet file: {e}")

def extract_from_image(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text from image using OCR (Tesseract)."""
    if not OCR_AVAILABLE:
        raise ValueError("Tesseract OCR is not installed or configured on the system.")
    try:
        img = Image.open(str(file_path))
        text = pytesseract.image_to_string(img)
        cleaned = clean_extracted_text(text)
        return cleaned, [{"page": 1, "text": cleaned}]
    except Exception as e:
        raise ValueError(f"Failed to OCR image file: {e}")

def extract_from_plain_text(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """Extract text from plain text or Markdown."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        cleaned = clean_extracted_text(text)
        return cleaned, [{"page": 1, "text": cleaned}]
    except Exception as e:
        raise ValueError(f"Failed to read text file: {e}")

def parse_syllabus_file(file_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Main parser supporting PDF, DOCX, PPTX, XLSX, CSV, TXT, MD, JPG, PNG.
    Returns (full_cleaned_text, pages_list)
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return extract_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        return extract_from_docx(file_path)
    elif ext in [".pptx", ".ppt"]:
        return extract_from_pptx(file_path)
    elif ext in [".xlsx", ".xls", ".csv"]:
        return extract_from_spreadsheet(file_path)
    elif ext in [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"]:
        return extract_from_image(file_path)
    elif ext in [".txt", ".md", ".json"]:
        return extract_from_plain_text(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")
