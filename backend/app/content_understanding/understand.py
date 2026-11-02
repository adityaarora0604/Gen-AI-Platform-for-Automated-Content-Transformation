"""Content understanding: turn raw source text into a structured representation. (Owner: Aaditya)"""
import json
import re
from typing import Any, List, Tuple

from app.ai_service import client
from app.ai_service.demo import demo_understand
from app.prompt_templates.templates import build_understanding_prompt
from app.schemas import SourceRepresentation


def parse_json_response(text: str) -> dict:
    """Parse JSON from an LLM reply, tolerating code fences and surrounding text."""
    t = (text or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.I).strip()
    candidates = [t]
    if "{" in t and "}" in t:
        candidates.append(t[t.index("{") : t.rindex("}") + 1])
    for c in candidates:
        try:
            data = json.loads(c)
            if isinstance(data, dict):
                return data
        except (json.JSONDecodeError, ValueError):
            continue
    raise client.LLMError("The AI returned malformed structured data for the source analysis.", 502, True)


def _str_list(value: Any) -> List[str]:
    if isinstance(value, str):
        value = [value]
    if not isinstance(value, list):
        return []
    out = []
    for v in value:
        s = str(v).strip()
        if s and s not in out:
            out.append(s)
    return out


def _digits(text: str) -> List[str]:
    return re.findall(r"\d+", text.replace(",", ""))


def build_representation(data: dict, source_text: str) -> Tuple[SourceRepresentation, List[str]]:
    """Coerce raw dict into SourceRepresentation and drop items that are not grounded in the source."""
    source_lower = source_text.lower()
    source_digits = set(_digits(source_text))
    dropped = 0

    def grounded_numeric(items: List[str]) -> List[str]:
        nonlocal dropped
        kept = []
        for it in items:
            if all(d in source_digits for d in _digits(it)):
                kept.append(it)
            else:
                dropped += 1
        return kept

    entities = []
    for e in _str_list(data.get("entities")):
        if e.lower() in source_lower:
            entities.append(e)
        else:
            dropped += 1

    rep = SourceRepresentation(
        summary=str(data.get("summary") or "").strip(),
        key_points=_str_list(data.get("key_points")),
        facts=_str_list(data.get("facts")),
        entities=entities,
        dates=grounded_numeric(_str_list(data.get("dates"))),
        important_figures=grounded_numeric(_str_list(data.get("important_figures"))),
        caveats=_str_list(data.get("caveats")),
        source_language=str(data.get("source_language") or "").strip(),
    )
    warnings = []
    if dropped:
        warnings.append(
            f"{dropped} extracted item(s) could not be matched to the source text and were removed."
        )
    if not (rep.summary or rep.key_points or rep.facts):
        raise client.LLMError("The AI could not extract any content from the source.", 502, False)
    return rep, warnings


def understand(source_text: str) -> Tuple[SourceRepresentation, List[str]]:
    """Return (structured representation, warnings)."""
    client.check_configuration()
    if client.is_demo():
        return demo_understand(source_text), []

    system, user = build_understanding_prompt(source_text)
    last_error = None
    for _ in range(2):  # one extra attempt if the JSON is malformed
        raw = client.complete(system, user)
        try:
            data = parse_json_response(raw)
            return build_representation(data, source_text)
        except client.LLMError as e:
            last_error = e
            if not e.retryable:
                raise
    raise last_error
