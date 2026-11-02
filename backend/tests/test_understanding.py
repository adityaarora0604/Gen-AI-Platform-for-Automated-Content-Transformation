"""Test 7 and 12: structured source representation, malformed AI responses."""
import json

import pytest

from app.ai_service import client
from app.content_understanding import understand as u
from app.schemas import SourceRepresentation


def test_demo_representation_has_all_fields(sample_text):
    rep, warnings = u.understand(sample_text)
    assert isinstance(rep, SourceRepresentation)
    assert rep.summary and rep.key_points and rep.facts
    assert rep.source_language == "English"
    assert warnings == []


def test_demo_extracts_dates_entities_figures_caveats(sample_text):
    rep, _ = u.understand(sample_text)
    assert "12 March 2026" in rep.dates
    assert "CVE-2026-12345" in rep.entities
    assert any("12%" in f for f in rep.important_figures)
    assert rep.caveats, "uncertainty must be preserved as caveats"


def test_demo_does_not_invent_items(sample_text):
    rep, _ = u.understand(sample_text)
    lower = sample_text.lower()
    for e in rep.entities:
        assert e.lower() in lower


def test_parse_json_with_code_fences():
    assert u.parse_json_response('```json\n{"summary": "x"}\n```') == {"summary": "x"}


def test_parse_json_with_surrounding_text():
    assert u.parse_json_response('Here you go: {"summary": "x"} Hope this helps') == {"summary": "x"}


@pytest.mark.parametrize("bad", ["", "not json at all", "[1, 2, 3]", "{broken"])
def test_parse_json_malformed_raises(bad):
    with pytest.raises(client.LLMError):
        u.parse_json_response(bad)


def test_ungrounded_items_are_dropped():
    source = "AcmeCorp reported 25 incidents on 3 May 2026."
    data = {
        "summary": "AcmeCorp reported incidents.",
        "key_points": ["AcmeCorp reported incidents."],
        "entities": ["AcmeCorp", "Globex"],  # Globex is not in the source
        "dates": ["3 May 2026", "9 June 2031"],  # second date has digits not in the source
        "important_figures": ["25 incidents", "900 incidents"],
    }
    rep, warnings = u.build_representation(data, source)
    assert rep.entities == ["AcmeCorp"]
    assert rep.dates == ["3 May 2026"]
    assert rep.important_figures == ["25 incidents"]
    assert warnings and "removed" in warnings[0]


def test_wrong_types_are_coerced():
    rep, _ = u.build_representation({"summary": "ok", "key_points": "single string", "facts": None}, "ok text")
    assert rep.key_points == ["single string"] and rep.facts == []


def test_empty_extraction_is_an_error():
    with pytest.raises(client.LLMError):
        u.build_representation({"summary": "", "key_points": []}, "some text")


def test_ai_mode_parses_model_json(ai_mode, monkeypatch, sample_text):
    payload = {"summary": "AcmeCorp announced a flaw.", "key_points": ["Flaw in AcmeVPN Gateway"], "entities": ["AcmeCorp"]}
    monkeypatch.setattr(client, "complete", lambda s, usr, max_tokens=None: json.dumps(payload))
    rep, _ = u.understand(sample_text)
    assert rep.summary.startswith("AcmeCorp")


def test_ai_mode_retries_once_on_malformed_json(ai_mode, monkeypatch, sample_text):
    replies = iter(["garbage", json.dumps({"summary": "ok", "key_points": ["a point"]})])
    monkeypatch.setattr(client, "complete", lambda s, usr, max_tokens=None: next(replies))
    rep, _ = u.understand(sample_text)
    assert rep.summary == "ok"


def test_ai_mode_gives_up_after_two_malformed_replies(ai_mode, monkeypatch, sample_text):
    monkeypatch.setattr(client, "complete", lambda s, usr, max_tokens=None: "still not json")
    with pytest.raises(client.LLMError):
        u.understand(sample_text)
