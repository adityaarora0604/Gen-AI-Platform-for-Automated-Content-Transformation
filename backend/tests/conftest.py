"""Shared fixtures. Tests never call a real LLM: they use demo mode or monkeypatch the AI client."""
import io
from pathlib import Path

import pytest

SAMPLE = Path(__file__).resolve().parents[2] / "sample_data" / "sample_advisory_source.txt"


@pytest.fixture(autouse=True)
def isolated_env(monkeypatch, tmp_path):
    """Every test gets demo mode, its own SQLite file, and instant retries."""
    monkeypatch.setenv("LLM_PROVIDER", "demo")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "jobs.sqlite3"))
    monkeypatch.setenv("LLM_MAX_RETRIES", "2")
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    monkeypatch.setattr("app.ai_service.client.time.sleep", lambda s: None)


@pytest.fixture
def ai_mode(monkeypatch):
    """Switch to the 'anthropic' provider with a fake key (the network call is always mocked)."""
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")


@pytest.fixture
def sample_text() -> str:
    return SAMPLE.read_text(encoding="utf-8")


def make_pdf_bytes(text: str) -> bytes:
    """Build a tiny valid one-page PDF without needing any PDF library."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = b"%PDF-1.4\n"
    offsets = []
    for i, o in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def make_docx_bytes(paragraphs) -> bytes:
    import docx

    d = docx.Document()
    for p in paragraphs:
        d.add_paragraph(p)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
