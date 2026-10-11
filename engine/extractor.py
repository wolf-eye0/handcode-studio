"""
Multi-format text extraction module.
Supports: Images (OCR via Tesseract), PDFs (pdftotext + OCR fallback), Word DOCX, and Text files.
"""

import os
import subprocess
import tempfile

TESSERACT_PATH = "/home/paradoxpete/.local/bin/tesseract"
if not os.path.exists(TESSERACT_PATH):
    import shutil
    TESSERACT_PATH = shutil.which("tesseract") or "tesseract"

PDFTOTEXT_PATH = "/usr/bin/pdftotext"
if not os.path.exists(PDFTOTEXT_PATH):
    import shutil
    PDFTOTEXT_PATH = shutil.which("pdftotext") or "pdftotext"


def extract_from_image(file_path: str) -> str:
    """Extract text from an image using Tesseract OCR."""
    cmd = [TESSERACT_PATH, file_path, "stdout", "--oem", "1", "-l", "eng"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError as e:
        # Fallback to basic tesseract without flags
        cmd_fallback = [TESSERACT_PATH, file_path, "stdout"]
        res = subprocess.run(cmd_fallback, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return res.stdout.strip()


def extract_from_pdf(file_path: str) -> str:
    """Extract text from PDF using pdftotext; fallback to OCR if scanned/empty."""
    cmd = [PDFTOTEXT_PATH, "-layout", file_path, "-"]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        text = res.stdout.strip()
        if len(text) > 20:
            return text
    except Exception:
        pass

    # If pdftotext returned little or no text, it might be a scanned PDF
    return _ocr_pdf_pages(file_path)


def _ocr_pdf_pages(file_path: str) -> str:
    """Render PDF pages as images and run OCR."""
    pdftoppm = "/usr/bin/pdftoppm"
    with tempfile.TemporaryDirectory() as tmpdir:
        prefix = os.path.join(tmpdir, "page")
        cmd = [pdftoppm, "-png", "-r", "150", file_path, prefix]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        
        pages = sorted([os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.endswith(".png")])
        extracted = []
        for p in pages:
            txt = extract_from_image(p)
            if txt:
                extracted.append(txt)
        return "\n\n--- Page Break ---\n\n".join(extracted)


def extract_from_docx(file_path: str) -> str:
    """Extract text from Microsoft Word .docx file."""
    import docx
    doc = docx.Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs)


def extract_text(file_path: str) -> str:
    """Auto-detect format and extract text."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".tif"]:
        return extract_from_image(file_path)
    elif ext == ".pdf":
        return extract_from_pdf(file_path)
    elif ext == ".docx":
        return extract_from_docx(file_path)
    elif ext in [".txt", ".md", ".csv", ".json"]:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read().strip()
    else:
        raise ValueError(f"Unsupported file type: {ext}")
