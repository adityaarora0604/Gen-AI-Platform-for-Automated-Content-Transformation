"""Tests 8-12: each output format, multiple selection, invalid settings, LLM failures, empty AI output."""
import json

import pytest

from app.ai_service import client
from app.generation.generator import run_transform
from app.prompt_templates.templates import OUTPUT_SPECS, build_generation_prompt
from app.schemas import ALL_OUTPUT_TYPES, AppError, GenerationSettings, TransformRequest


def make_req(text, types=None, **settings):
    return TransformRequest(
        source_text=text,
        output_types=list(ALL_OUTPUT_TYPES) if types is None else types,
        settings=GenerationSettings(**settings),
    )


@pytest.mark.parametrize("output_type", ALL_OUTPUT_TYPES)
def test_each_output_format(sample_text, output_type):
    res = run_transform(make_req(sample_text, [output_type]))
    assert res.status == "completed" and res.mode == "demo"
    assert len(res.outputs) == 1
    out = res.outputs[0]
    assert out.type == output_type and out.content.strip()
    assert "DEMO MODE" in out.content, "demo output must always be labelled"
    assert out.validation_warnings == [], out.validation_warnings


def test_multiple_outputs_in_one_job(sample_text):
    res = run_transform(make_req(sample_text))
    assert [o.type for o in res.outputs] == ALL_OUTPUT_TYPES
    assert res.source_representation["summary"]
    assert any("DEMO MODE" in w for w in res.warnings)
    assert res.metadata["provider"] == "demo"
    assert res.job_id


def test_duplicate_output_types_are_deduplicated(sample_text):
    res = run_transform(make_req(sample_text, ["linkedin", "linkedin", "advisory"]))
    assert [o.type for o in res.outputs] == ["linkedin", "advisory"]


def test_no_output_types_selected(sample_text):
    with pytest.raises(AppError) as e:
        run_transform(make_req(sample_text, []))
    assert e.value.status_code == 422


@pytest.mark.parametrize(
    "bad",
    [{"tone": "Sarcastic"}, {"language": "Klingon"}, {"objective": "Trick"}, {"style": "Poem"}, {"audience": "  "}],
)
def test_invalid_settings_rejected(sample_text, bad):
    with pytest.raises(AppError) as e:
        run_transform(make_req(sample_text, ["linkedin"], **bad))
    assert e.value.status_code == 422


def test_invalid_detail_level_rejected_by_schema():
    with pytest.raises(ValueError):
        GenerationSettings(detail_level="Extreme")


def test_detail_level_changes_demo_length(sample_text):
    low = run_transform(make_req(sample_text, ["executive_summary"], detail_level="Low")).outputs[0].content
    high = run_transform(make_req(sample_text, ["executive_summary"], detail_level="High")).outputs[0].content
    assert len(high) > len(low)


def test_empty_source_rejected():
    with pytest.raises(AppError) as e:
        run_transform(make_req("   "))
    assert e.value.status_code == 400


def test_prompt_contains_settings_and_grounding_rules():
    system, user = build_generation_prompt(
        "advisory", {"summary": "x"}, {"audience": "Executives", "tone": "Formal", "language": "Hindi",
                                      "detail_level": "High", "objective": "Alert", "style": "Concise"}
    )
    assert "ONLY facts" in system and "Not specified in the source." in system
    for token in ("Executives", "Formal", "Hindi", "High", "Alert", "Concise", "Recommended Actions"):
        assert token in user


def test_every_format_has_a_prompt():
    for t in OUTPUT_SPECS:
        system, user = build_generation_prompt(t, {}, {"detail_level": "Medium"})
        assert system and user


# ---------------------------------------------------------------- AI mode / failures

GOOD_JSON = json.dumps({"summary": "AcmeCorp announced a flaw.", "key_points": ["Flaw in AcmeVPN Gateway"]})
GOOD_SUMMARY = "# Title\n## Overview\nok\n## Key Findings\n- a\n## Important Facts\n- b\n## Conclusion\nc"


def fake_llm(per_type):
    """Build a replacement for client._call_anthropic that answers by prompt content."""

    def _fake(system, user, max_tokens, timeout):
        if "information-extraction" in system:
            return GOOD_JSON
        for key, handler in per_type.items():
            if f"Create the output format: {OUTPUT_SPECS[key]['label']}" in user:
                return handler()
        return GOOD_SUMMARY

    return _fake


def test_ai_mode_success(ai_mode, monkeypatch, sample_text):
    monkeypatch.setattr(client, "_call_anthropic", fake_llm({}))
    res = run_transform(make_req(sample_text, ["executive_summary"]))
    assert res.mode == "ai" and res.status == "completed"
    assert "DEMO MODE" not in res.outputs[0].content
    assert not any("DEMO" in w for w in res.warnings)


def test_ai_mode_strips_code_fences(ai_mode, monkeypatch, sample_text):
    monkeypatch.setattr(client, "_call_anthropic", fake_llm({"executive_summary": lambda: f"```markdown\n{GOOD_SUMMARY}\n```"}))
    res = run_transform(make_req(sample_text, ["executive_summary"]))
    assert not res.outputs[0].content.startswith("```")


def test_missing_api_key_gives_setup_message(monkeypatch, sample_text):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(AppError) as e:
        run_transform(make_req(sample_text, ["linkedin"]))
    assert e.value.status_code == 503 and "ANTHROPIC_API_KEY" in e.value.message


def test_unknown_provider_rejected(monkeypatch, sample_text):
    monkeypatch.setenv("LLM_PROVIDER", "mystery")
    with pytest.raises(AppError):
        run_transform(make_req(sample_text, ["linkedin"]))


def test_llm_failure_on_understanding_fails_job(ai_mode, monkeypatch, sample_text):
    def boom(*a, **k):
        raise client.LLMError("provider down", 502, retryable=False)

    monkeypatch.setattr(client, "_call_anthropic", boom)
    with pytest.raises(client.LLMError):
        run_transform(make_req(sample_text, ["linkedin"]))


def test_one_format_failing_gives_partial_result(ai_mode, monkeypatch, sample_text):
    def fail():
        raise client.LLMError("overloaded", 502, retryable=False)

    monkeypatch.setattr(client, "_call_anthropic", fake_llm({"linkedin": fail}))
    res = run_transform(make_req(sample_text, ["executive_summary", "linkedin"]))
    assert res.status == "partial"
    by_type = {o.type: o for o in res.outputs}
    assert by_type["executive_summary"].status == "completed"
    assert by_type["linkedin"].status == "failed" and "overloaded" in by_type["linkedin"].error
    assert res.errors


def test_all_formats_failing_marks_job_failed(ai_mode, monkeypatch, sample_text):
    def fail():
        raise client.LLMError("nope", 502, retryable=False)

    monkeypatch.setattr(client, "_call_anthropic", fake_llm({"linkedin": fail}))
    res = run_transform(make_req(sample_text, ["linkedin"]))
    assert res.status == "failed"


def test_rate_limit_is_retried_then_succeeds(ai_mode, monkeypatch):
    calls = {"n": 0}

    def flaky(system, user, max_tokens, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            raise client.LLMError("rate limited", 429, retryable=True)
        return "ok"

    monkeypatch.setattr(client, "_call_anthropic", flaky)
    assert client.complete("s", "u") == "ok" and calls["n"] == 3


def test_retries_are_bounded(ai_mode, monkeypatch):
    calls = {"n": 0}

    def always(system, user, max_tokens, timeout):
        calls["n"] += 1
        raise client.LLMError("timeout", 504, retryable=True)

    monkeypatch.setattr(client, "_call_anthropic", always)
    with pytest.raises(client.LLMError) as e:
        client.complete("s", "u")
    assert calls["n"] == 3 and e.value.status_code == 504  # 1 try + LLM_MAX_RETRIES=2


def test_non_retryable_error_is_not_retried(ai_mode, monkeypatch):
    calls = {"n": 0}

    def bad_key(system, user, max_tokens, timeout):
        calls["n"] += 1
        raise client.LLMError("bad key", 502, retryable=False)

    monkeypatch.setattr(client, "_call_anthropic", bad_key)
    with pytest.raises(client.LLMError):
        client.complete("s", "u")
    assert calls["n"] == 1


@pytest.mark.parametrize("empty", ["", "   \n  "])
def test_empty_ai_response_is_an_error(ai_mode, monkeypatch, empty):
    monkeypatch.setattr(client, "_call_anthropic", lambda *a: empty)
    with pytest.raises(client.LLMError) as e:
        client.complete("s", "u")
    assert "empty" in e.value.message.lower()


def test_malformed_ai_output_yields_validation_warnings_not_a_crash(ai_mode, monkeypatch, sample_text):
    monkeypatch.setattr(client, "_call_anthropic", fake_llm({"advisory": lambda: "Just some random text with no structure."}))
    res = run_transform(make_req(sample_text, ["advisory"]))
    out = res.outputs[0]
    assert out.status == "completed"
    assert any("missing" in w for w in out.validation_warnings)
