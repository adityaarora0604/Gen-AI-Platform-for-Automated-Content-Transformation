"""Tests 13-15: output validation, export/download, complete workflow (no HTTP layer)."""
import io
import json

import pytest

from app import jobs_store
from app.export.exporter import build_export
from app.generation.generator import run_transform
from app.schemas import ALL_OUTPUT_TYPES, AppError, GenerationSettings, TransformRequest
from app.validation.validator import validate_output

SOURCE = "AcmeCorp reported 3,500 organisations are affected. The cause is unconfirmed."


# ------------------------------------------------------------------ validation

def test_empty_output_flagged():
    assert "empty" in validate_output("linkedin", "   ", SOURCE)[0]


def test_unknown_type_rejected():
    with pytest.raises(AppError):
        validate_output("poem", "text", SOURCE)


def test_executive_summary_missing_sections_flagged():
    warnings = validate_output("executive_summary", "# T\n## Overview\nonly this", SOURCE)
    assert any("Key Findings" in w for w in warnings)
    assert any("Conclusion" in w for w in warnings)


def test_missing_title_flagged():
    text = "## Overview\na\n## Key Findings\nb\n## Important Facts\nc\n## Conclusion\nd"
    assert any("title" in w for w in validate_output("executive_summary", text, SOURCE))


def test_valid_executive_summary_passes():
    text = "# T\n## Overview\na\n## Key Findings\n- b\n## Important Facts\n- 3,500 organisations\n## Conclusion\nd"
    assert validate_output("executive_summary", text, SOURCE) == []


def test_linkedin_requires_hashtags():
    text = "## Hook\nh\n## Post\np\n## Key Takeaways\n- k\n## Hashtags\nnone here\n## Call to Action\nc"
    assert any("hashtag" in w.lower() for w in validate_output("linkedin", text, SOURCE))


def test_thread_length_limit_enforced():
    long_post = "1/1 " + "x" * 300
    assert any("280" in w for w in validate_output("x_thread", long_post, SOURCE))


def test_thread_numbering_checked():
    assert any("numbering" in w for w in validate_output("x_thread", "1/3 a\n\n3/3 b", SOURCE))
    assert validate_output("x_thread", "1/2 first post\n\n2/2 second post", SOURCE) == []


def test_thread_without_numbers_flagged():
    assert any("numbered" in w for w in validate_output("x_thread", "just a tweet", SOURCE))


def test_presentation_needs_slides_visuals_notes():
    warnings = validate_output("presentation", "# Deck\n## Slide 1: A\n- b", SOURCE)
    assert any("fewer than 3" in w for w in warnings)
    assert any("Suggested visual" in w for w in warnings)
    assert any("Speaker notes" in w for w in warnings)


def test_invented_figures_flagged():
    text = "# T\n## Overview\n9,999 organisations\n## Key Findings\nb\n## Important Facts\nc\n## Conclusion\nd"
    assert any("9999" in w for w in validate_output("executive_summary", text, SOURCE))


def test_figures_from_source_not_flagged():
    text = "# T\n## Overview\n3,500 organisations\n## Key Findings\nb\n## Important Facts\nc\n## Conclusion\nd"
    assert validate_output("executive_summary", text, SOURCE) == []


def test_uncertain_source_presented_as_confirmed_flagged():
    text = "# T\n## Overview\nThe cause is confirmed.\n## Key Findings\nb\n## Important Facts\nc\n## Conclusion\nd"
    assert any("certainty" in w for w in validate_output("executive_summary", text, SOURCE))


def test_negated_certainty_wording_is_not_flagged():
    text = "# T\n## Overview\nThis has not been verified and is yet to be confirmed.\n## Key Findings\nb\n## Important Facts\nc\n## Conclusion\nd"
    assert validate_output("executive_summary", text, SOURCE) == []


def test_invented_severity_flagged():
    text = (
        "# Adv\n## Severity / Priority\nCritical\n## Background\nb\n## Key Observations\n- o\n"
        "## Potential Impact\ni\n## Recommended Actions\n- a\n## Caveats\n- c"
    )
    assert any("severity" in w.lower() for w in validate_output("advisory", text, "A plain note with no rating."))


def test_unspecified_severity_is_fine():
    text = (
        "# Adv\n## Severity / Priority\nNot specified in the source.\n## Background\nb\n## Key Observations\n- o\n"
        "## Potential Impact\ni\n## Recommended Actions\n- a\n## Caveats\n- c"
    )
    assert validate_output("advisory", text, "A plain note with no rating.") == []


def test_placeholder_text_flagged():
    text = "# T\n## Overview\n[insert details]\n## Key Findings\nb\n## Important Facts\nc\n## Conclusion\nd"
    assert any("placeholder" in w for w in validate_output("executive_summary", text, SOURCE))


# ------------------------------------------------------------------ export

OUTPUTS = [
    {"type": "executive_summary", "label": "Executive Summary", "content": "# Title\n## Overview\n- point **bold**"},
    {"type": "linkedin", "label": "LinkedIn Post", "content": "## Hook\nHello"},
]


@pytest.mark.parametrize("fmt", ["md", "txt", "json", "docx"])
def test_export_all_formats(fmt):
    data, filename, media = build_export("job1", OUTPUTS, "demo", fmt)
    assert data and filename == f"content_job1.{fmt}" and media


def test_export_markdown_contains_notice_and_demo_label():
    text = build_export("j", OUTPUTS, "demo", "md")[0].decode()
    assert "human must review" in text.lower() and "DEMO MODE" in text and "Executive Summary" in text


def test_export_json_roundtrip():
    payload = json.loads(build_export("j", OUTPUTS, "ai", "json")[0])
    assert payload["job_id"] == "j" and len(payload["outputs"]) == 2


def test_export_txt_has_no_markdown_markers():
    text = build_export("j", OUTPUTS, "ai", "txt")[0].decode()
    assert "**" not in text and "# " not in text


def test_export_docx_is_readable():
    import docx

    data = build_export("j", OUTPUTS, "ai", "docx")[0]
    paragraphs = [p.text for p in docx.Document(io.BytesIO(data)).paragraphs]
    assert any("point" in p for p in paragraphs)


def test_export_unsupported_format():
    with pytest.raises(AppError) as e:
        build_export("j", OUTPUTS, "ai", "exe")
    assert e.value.status_code == 400


def test_export_nothing():
    with pytest.raises(AppError):
        build_export("j", [], "ai", "md")


# ------------------------------------------------------------------ end to end

def test_complete_workflow(sample_text):
    """paste text -> settings -> generate all formats -> validate -> stored job -> export."""
    req = TransformRequest(
        source_text=sample_text,
        output_types=list(ALL_OUTPUT_TYPES),
        settings=GenerationSettings(audience="Executives / leadership", tone="Formal", objective="Alert",
                                    style="Analytical", detail_level="High", language="English"),
    )
    res = run_transform(req)
    assert res.status == "completed"
    assert {o.type for o in res.outputs} == set(ALL_OUTPUT_TYPES)
    assert all(o.validation_warnings == [] for o in res.outputs)
    assert "human must review" in res.human_review_notice.lower()

    job = jobs_store.get_job(res.job_id)
    assert job["status"] == "completed" and job["mode"] == "demo"
    assert job["settings"]["tone"] == "Formal"
    assert len(job["result"]["outputs"]) == 5
    assert "AcmeCorp" not in json.dumps({k: v for k, v in job.items() if k != "result"}), "raw source is not stored"

    data, _, _ = build_export(res.job_id, [o.model_dump() for o in res.outputs], res.mode, "md")
    assert b"Executive Summary" in data


def test_failed_job_is_recorded(monkeypatch, sample_text):
    from app.ai_service import client

    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(client, "_call_anthropic", lambda *a: (_ for _ in ()).throw(client.LLMError("down", 502, False)))
    with pytest.raises(AppError):
        run_transform(TransformRequest(source_text=sample_text, output_types=["linkedin"]))
    # the job row exists and is marked failed
    import sqlite3

    from app.config import get_settings

    row = sqlite3.connect(get_settings().database_path).execute("select status from jobs").fetchone()
    assert row[0] == "failed"
