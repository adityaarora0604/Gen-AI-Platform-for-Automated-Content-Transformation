"""Export: build downloadable files from generated outputs. (Owner: Rishabh)"""
import io
import json
import re
from typing import Dict, List, Tuple

from app.prompt_templates.templates import HUMAN_REVIEW_NOTICE
from app.schemas import AppError

FORMATS = {
    "md": "text/markdown; charset=utf-8",
    "txt": "text/plain; charset=utf-8",
    "json": "application/json",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _footer(mode: str) -> str:
    extra = " This content was produced in DEMO MODE (rule-based, not AI-generated)." if mode == "demo" else ""
    return f"{HUMAN_REVIEW_NOTICE}{extra}"


def _markdown(job_id: str, outputs: List[Dict], mode: str) -> str:
    parts = [f"# Generated content (job {job_id})", "", f"_{_footer(mode)}_", ""]
    for o in outputs:
        parts += [f"---\n\n# {o.get('label') or o['type']}\n", o.get("content", "").strip(), ""]
    return "\n".join(parts).strip() + "\n"


def _plain(job_id: str, outputs: List[Dict], mode: str) -> str:
    text = _markdown(job_id, outputs, mode)
    return re.sub(r"(?m)^#+\s*", "", text).replace("**", "")


def _docx(job_id: str, outputs: List[Dict], mode: str) -> bytes:
    import docx

    doc = docx.Document()
    doc.add_heading(f"Generated content (job {job_id})", 0)
    note = doc.add_paragraph()
    note.add_run(_footer(mode)).italic = True
    for o in outputs:
        doc.add_heading(o.get("label") or o["type"], 1)
        for line in o.get("content", "").splitlines():
            line = line.strip().replace("**", "")
            if not line:
                continue
            m = re.match(r"^(#{1,6})\s+(.*)", line)
            if m:
                doc.add_heading(m.group(2), min(len(m.group(1)) + 1, 4))
            elif line.startswith(("- ", "* ")):
                doc.add_paragraph(line[2:], style="List Bullet")
            else:
                doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_export(job_id: str, outputs: List[Dict], mode: str, fmt: str) -> Tuple[bytes, str, str]:
    """Return (file_bytes, filename, media_type)."""
    fmt = (fmt or "md").lower()
    if fmt not in FORMATS:
        raise AppError(f"Unsupported export format '{fmt}'. Use one of: {', '.join(FORMATS)}.", 400)
    if not outputs:
        raise AppError("There are no outputs to export.", 404)
    if fmt == "md":
        data = _markdown(job_id, outputs, mode).encode("utf-8")
    elif fmt == "txt":
        data = _plain(job_id, outputs, mode).encode("utf-8")
    elif fmt == "json":
        data = json.dumps(
            {"job_id": job_id, "mode": mode, "notice": _footer(mode), "outputs": outputs},
            ensure_ascii=False,
            indent=2,
        ).encode("utf-8")
    else:
        data = _docx(job_id, outputs, mode)
    return data, f"content_{job_id}.{fmt}", FORMATS[fmt]
