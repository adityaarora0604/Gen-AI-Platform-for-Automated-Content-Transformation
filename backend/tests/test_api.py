"""HTTP-level tests (needs fastapi + httpx; skipped automatically if they are not installed)."""
import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("httpx", reason="httpx not installed")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from tests.conftest import make_docx_bytes, make_pdf_bytes  # noqa: E402

client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok" and r.json()["mode"] == "demo"


def test_options():
    body = client.get("/api/options").json()
    assert len(body["output_types"]) == 5 and "Professional" in body["tones"]


def test_upload_txt(sample_text):
    r = client.post("/api/upload", files={"file": ("s.txt", sample_text.encode(), "text/plain")})
    assert r.status_code == 200 and r.json()["file_type"] == "txt" and "AcmeCorp" in r.json()["text"]


def test_upload_docx():
    r = client.post("/api/upload", files={"file": ("s.docx", make_docx_bytes(["Hello from Word."]), "application/octet-stream")})
    assert r.status_code == 200 and "Hello from Word." in r.json()["text"]


def test_upload_pdf():
    pytest.importorskip("fitz")
    r = client.post("/api/upload", files={"file": ("s.pdf", make_pdf_bytes("PDF body text"), "application/pdf")})
    assert r.status_code == 200 and "PDF body text" in r.json()["text"]


def test_upload_invalid_type():
    r = client.post("/api/upload", files={"file": ("x.exe", b"MZ", "application/octet-stream")})
    assert r.status_code == 415 and "Unsupported" in r.json()["detail"]


def test_upload_empty_file():
    r = client.post("/api/upload", files={"file": ("e.txt", b"", "text/plain")})
    assert r.status_code == 400


def test_upload_too_large():
    r = client.post("/api/upload", files={"file": ("big.txt", b"a" * (2 * 1024 * 1024), "text/plain")})
    assert r.status_code == 413


def test_transform_empty_input():
    r = client.post("/api/transform", json={"source_text": "  ", "output_types": ["linkedin"]})
    assert r.status_code == 400


def test_transform_invalid_output_type():
    r = client.post("/api/transform", json={"source_text": "x" * 50, "output_types": ["poem"]})
    assert r.status_code == 422


def test_transform_invalid_settings(sample_text):
    r = client.post("/api/transform", json={"source_text": sample_text, "output_types": ["linkedin"], "settings": {"tone": "Rude"}})
    assert r.status_code == 422


def test_full_workflow_over_http(sample_text):
    # 1 upload -> 2 transform -> 3 job status -> 4 outputs -> 5 export (job + edited)
    up = client.post("/api/upload", files={"file": ("s.txt", sample_text.encode(), "text/plain")}).json()
    r = client.post("/api/transform", json={"source_text": up["text"], "output_types": ["executive_summary", "x_thread", "presentation"]})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed" and len(body["outputs"]) == 3
    job_id = body["job_id"]

    status = client.get(f"/api/jobs/{job_id}").json()
    assert status["status"] == "completed" and status["mode"] == "demo"
    assert len(client.get(f"/api/jobs/{job_id}/outputs").json()["outputs"]) == 3

    for fmt in ("md", "txt", "json", "docx"):
        e = client.get(f"/api/jobs/{job_id}/export", params={"format": fmt})
        assert e.status_code == 200 and "attachment" in e.headers["content-disposition"]

    edited = client.post("/api/export", json={"job_id": job_id, "mode": "demo", "format": "md",
                                               "outputs": [{"type": "linkedin", "label": "LinkedIn Post", "content": "My edited text"}]})
    assert edited.status_code == 200 and b"My edited text" in edited.content


def test_unknown_job_404():
    assert client.get("/api/jobs/doesnotexist").status_code == 404
    assert client.get("/api/jobs/doesnotexist/outputs").status_code == 404
    assert client.get("/api/jobs/doesnotexist/export").status_code == 404


def test_export_bad_format(sample_text):
    job = client.post("/api/transform", json={"source_text": sample_text, "output_types": ["linkedin"]}).json()
    assert client.get(f"/api/jobs/{job['job_id']}/export", params={"format": "exe"}).status_code == 400
