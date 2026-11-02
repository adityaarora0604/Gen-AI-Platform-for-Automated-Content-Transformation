"""Ingestion: validate and extract text from TXT / PDF / DOCX. (Owner: Aditya)

Uploaded files are only parsed as data, never executed.
"""
import io
import os
from typing import Tuple

from app.config import get_settings
from app.preprocessing.cleaner import clean_text, truncate_text
from app.schemas import AppError

ALLOWED_EXTENSIONS = {".txt", ".pdf", ".docx"}


def validate_file(filename: str, data: bytes) -> str:
    """Validate name, extension, size and content signature. Returns the extension."""
    if not filename:
        raise AppError("No file name provided.", 400)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(f"Unsupported file type '{ext or 'unknown'}'. Allowed: TXT, PDF, DOCX.", 415)
    if not data:
        raise AppError("The uploaded file is empty.", 400)
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise AppError(f"File is too large. Maximum size is {get_settings().max_upload_mb} MB.", 413)
    if ext == ".pdf" and not data.startswith(b"%PDF"):
        raise AppError("File content does not look like a valid PDF.", 400)
    if ext == ".docx" and not data.startswith(b"PK"):
        raise AppError("File content does not look like a valid DOCX.", 400)
    return ext


def extract_txt(data: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise AppError("Could not decode the text file.", 400)


def extract_pdf(data: bytes) -> str:
    try:
        import fitz  # PyMuPDF
    except ImportError as e:  # pragma: no cover
        raise AppError("PDF support is not installed (pip install pymupdf).", 500) from e
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        if doc.needs_pass:
            raise AppError("Password-protected PDFs are not supported.", 400)
        pages = [page.get_text() for page in doc]
        doc.close()
    except AppError:
        raise
    except Exception as e:
        raise AppError("Could not read the PDF. It may be corrupted.", 400) from e
    return "\n\n".join(pages)


def extract_docx(data: bytes) -> str:
    try:
        import docx  # python-docx
    except ImportError as e:  # pragma: no cover
        raise AppError("DOCX support is not installed (pip install python-docx).", 500) from e
    try:
        document = docx.Document(io.BytesIO(data))
    except Exception as e:
        raise AppError("Could not read the DOCX. It may be corrupted.", 400) from e
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return "\n".join(parts)


def extract_text(filename: str, data: bytes) -> Tuple[str, str, bool]:
    """Return (cleaned_text, file_type, truncated)."""
    ext = validate_file(filename, data)
    if ext == ".txt":
        raw = extract_txt(data)
    elif ext == ".pdf":
        raw = extract_pdf(data)
    else:
        raw = extract_docx(data)
    cleaned = clean_text(raw)
    if not cleaned:
        raise AppError(
            "No readable text was found in the file (scanned/image-only PDFs are not supported in this phase).",
            422,
        )
    cleaned, truncated = truncate_text(cleaned, get_settings().max_source_chars)
    return cleaned, ext.lstrip("."), truncated


def prepare_source_text(text: str) -> Tuple[str, bool]:
    """Validate and clean pasted text. Returns (cleaned_text, truncated)."""
    cleaned = clean_text(text or "")
    if not cleaned:
        raise AppError("Source content is empty. Paste text or upload a document.", 400)
    if len(cleaned) < 20:
        raise AppError("Source content is too short to transform (minimum 20 characters).", 400)
    return truncate_text(cleaned, get_settings().max_source_chars)
