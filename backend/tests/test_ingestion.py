"""Tests 1-5: TXT / PDF / DOCX extraction, invalid upload, empty input."""
import pytest

from app.ingestion.extractors import extract_text, prepare_source_text, validate_file
from app.schemas import AppError
from tests.conftest import make_docx_bytes, make_pdf_bytes


def test_txt_extraction():
    text, ftype, truncated = extract_text("note.txt", b"Hello world.\n\nThis is a test document for extraction.")
    assert ftype == "txt" and not truncated
    assert "Hello world." in text


def test_txt_extraction_utf8_bom():
    text, _, _ = extract_text("a.txt", "﻿Café report with enough characters".encode("utf-8"))
    assert text.startswith("Café")


def test_pdf_extraction():
    pytest.importorskip("fitz", reason="PyMuPDF not installed")
    text, ftype, _ = extract_text("report.pdf", make_pdf_bytes("Quarterly threat report"))
    assert ftype == "pdf"
    assert "Quarterly threat report" in text


def test_docx_extraction():
    data = make_docx_bytes(["First paragraph here.", "Second paragraph with 42 items."])
    text, ftype, _ = extract_text("brief.docx", data)
    assert ftype == "docx"
    assert "First paragraph here." in text and "42 items" in text


def test_invalid_extension_rejected():
    with pytest.raises(AppError) as e:
        extract_text("malware.exe", b"MZ....")
    assert e.value.status_code == 415


def test_fake_pdf_content_rejected():
    with pytest.raises(AppError) as e:
        validate_file("fake.pdf", b"this is not a pdf")
    assert e.value.status_code == 400


def test_fake_docx_content_rejected():
    with pytest.raises(AppError):
        validate_file("fake.docx", b"plain text pretending to be docx")


def test_empty_file_rejected():
    with pytest.raises(AppError) as e:
        extract_text("empty.txt", b"")
    assert "empty" in e.value.message.lower()


def test_oversized_file_rejected():
    with pytest.raises(AppError) as e:
        extract_text("big.txt", b"a" * (2 * 1024 * 1024))  # limit is 1 MB in tests
    assert e.value.status_code == 413


def test_whitespace_only_file_rejected():
    with pytest.raises(AppError):
        extract_text("blank.txt", b"   \n\n  \t ")


@pytest.mark.parametrize("bad", ["", "   ", "\n\n\t", None])
def test_empty_pasted_input_rejected(bad):
    with pytest.raises(AppError) as e:
        prepare_source_text(bad)
    assert e.value.status_code == 400


def test_too_short_input_rejected():
    with pytest.raises(AppError):
        prepare_source_text("hi")


def test_long_input_is_truncated(monkeypatch):
    monkeypatch.setenv("MAX_SOURCE_CHARS", "200")
    text, truncated = prepare_source_text("This is a sentence. " * 50)
    assert truncated and len(text) <= 200
