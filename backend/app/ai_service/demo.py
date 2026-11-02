"""DEMO MODE: rule-based extraction and templating. NOT AI-generated. (Owner: Anishk)

Used only when LLM_PROVIDER=demo so the frontend can be tested without an API key.
All demo output carries a visible banner.
"""
import re
from collections import Counter
from typing import List

from app.prompt_templates.templates import MISSING
from app.schemas import SourceRepresentation

DEMO_BANNER = "[DEMO MODE: rule-based extract from the source, NOT AI-generated]"

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December|"
    "Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec"
)
DATE_PATTERNS = [
    rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+(?:{MONTHS})\.?,?\s+\d{{4}}\b",
    rf"\b(?:{MONTHS})\.?\s+\d{{1,2}}(?:st|nd|rd|th)?,?\s+\d{{4}}\b",
    rf"\b(?:{MONTHS})\s+\d{{4}}\b",
    r"\b\d{4}-\d{2}-\d{2}\b",
    r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
]
FIGURE_PATTERN = re.compile(
    r"(?:[$€£₹]\s?\d[\d,]*(?:\.\d+)?(?:\s?(?:million|billion|crore|lakh|thousand))?)"
    r"|(?:\b\d[\d,]*(?:\.\d+)?\s?(?:%|(?:percent|per cent|million|billion|crore|lakh|thousand|hours|days|weeks|"
    r"months|users|systems|devices|servers|organisations|organizations|incidents|attacks|records|MB|GB|TB)\b))",
    re.I,
)
CAVEAT_PATTERN = re.compile(
    r"\b(may|might|could|reportedly|allegedly|alleged|unconfirmed|suspected|preliminary|estimated|"
    r"appears?|likely|unclear|unknown|not yet|under investigation|yet to be)\b",
    re.I,
)
STOP_WORDS = set(
    "The This That These Those It In On At As For By With From And But Or If However Additionally According "
    "A An We They He She Our Their There When While After Before During Also No Not Is Are Was Were Of To "
    "Monday Tuesday Wednesday Thursday Friday Saturday Sunday".split()
) | set(MONTHS.split("|"))
ENTITY_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9&'\-]*(?:\s[A-Z][A-Za-z0-9&'\-]*)*\b")
CODE_PATTERN = re.compile(r"\bCVE-\d{4}-\d{4,7}\b|\b[A-Z]{2,}[A-Z0-9\-]*\b")


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    out = []
    for p in parts:
        p = re.sub(r"^\s*(?:[-•*]|\d+[.)])\s*", "", p).strip()
        if len(p) >= 15:
            out.append(p)
    return out


def _trim(s: str, n: int) -> str:
    s = s.strip()
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def _extract_dates(text: str) -> List[str]:
    found = []
    for pat in DATE_PATTERNS:
        for m in re.finditer(pat, text, re.I):
            found.append(m.group(0))
    unique = []
    for d in found:
        if d not in unique:
            unique.append(d)
    # drop dates that are contained in a longer date
    return [d for d in unique if not any(d != o and d in o for o in unique)]


def _extract_entities(text: str, sentences: List[str]) -> List[str]:
    counts: Counter = Counter()
    order: dict = {}
    for sent in sentences:
        for m in ENTITY_PATTERN.finditer(sent):
            words = m.group(0).split()
            while words and words[0] in STOP_WORDS:
                words = words[1:]
            if not words:
                continue
            ent = " ".join(words)
            at_start = m.start() == 0
            if len(words) == 1 and at_start and not ent.isupper():
                continue
            if ent in STOP_WORDS or len(ent) < 2:
                continue
            counts[ent] += 1
            order.setdefault(ent, len(order))
    for m in CODE_PATTERN.finditer(text):
        ent = m.group(0)
        if ent not in STOP_WORDS:
            counts[ent] += 1
            order.setdefault(ent, len(order))
    ranked = sorted(counts, key=lambda e: (-counts[e], order[e]))
    return ranked[:15]


def demo_understand(text: str) -> SourceRepresentation:
    # A short first line without end punctuation is a heading, not a sentence.
    first, _, rest = text.partition("\n")
    body = rest if rest.strip() and len(first) <= 120 and not re.search(r"[.!?]\s*$", first) else text
    sentences = split_sentences(body)
    dates = _extract_dates(text)
    entities = _extract_entities(text, sentences)

    figures = []
    for m in FIGURE_PATTERN.finditer(text):
        f = m.group(0).strip()
        if f not in figures:
            figures.append(f)

    caveat_sents = [s for s in sentences if CAVEAT_PATTERN.search(s)]
    fact_pattern = re.compile(r"\d|announced|reported|stated|confirmed|discovered|detected|issued|released", re.I)
    facts = [s for s in sentences if s not in caveat_sents and fact_pattern.search(s)]

    scored = []
    for idx, s in enumerate(sentences):
        score = (2 if re.search(r"\d", s) else 0) + min(2, sum(1 for e in entities if e in s))
        score += 1 if 40 <= len(s) <= 220 else 0
        score += 1 if idx < 3 else 0
        scored.append((score, idx, s))
    top = sorted(scored, key=lambda t: (-t[0], t[1]))[:6]
    key_points = [_trim(s, 300) for _, _, s in sorted(top, key=lambda t: t[1])]

    non_ascii = sum(1 for ch in text if ord(ch) > 127)
    if re.search(r"[ऀ-ॿ]", text):
        lang = "Hindi"
    elif non_ascii > len(text) * 0.3:
        lang = "Non-English (unidentified)"
    else:
        lang = "English"

    return SourceRepresentation(
        summary=_trim(" ".join(sentences[:2]) if sentences else text, 450),
        key_points=key_points,
        facts=[_trim(f, 300) for f in facts[:8]],
        entities=entities,
        dates=dates[:10],
        important_figures=figures[:10],
        caveats=[_trim(c, 300) for c in caveat_sents[:5]],
        source_language=lang,
    )


# ---------------------------------------------------------------- generation

def _n_items(settings: dict) -> int:
    return {"Low": 3, "Medium": 5, "High": 8}.get(settings.get("detail_level", "Medium"), 5)


def _bullets(items: List[str], n: int, empty: str = MISSING) -> str:
    items = [i for i in items if i][:n]
    return "\n".join(f"- {i}" for i in items) if items else empty


def _title(rep: dict) -> str:
    base = (rep.get("summary") or "").strip()
    if not base and rep.get("key_points"):
        base = rep["key_points"][0]
    first = re.split(r"(?<=[.!?])\s", base)[0] if base else "Source briefing"
    return _trim(first.rstrip(".!?"), 90) or "Source briefing"


def _hashtags(rep: dict) -> str:
    tags = []
    for e in rep.get("entities", []):
        tag = re.sub(r"[^A-Za-z0-9]", "", e.title().replace(" ", ""))
        if tag and not tag.isdigit() and f"#{tag}" not in tags:
            tags.append(f"#{tag}")
        if len(tags) >= 4:
            break
    for fallback in ("#Briefing", "#Insights"):
        if len(tags) < 3 and fallback not in tags:
            tags.append(fallback)
    return " ".join(tags)


def _cta(objective: str) -> str:
    return {
        "Alert": "Share this with your team and review your exposure today.",
        "Persuade": "Join the conversation and share your view.",
        "Educate": "Save this post and share it with colleagues who should know.",
        "Recommend action": "Review the recommendations with your team and act on what applies.",
    }.get(objective, "Read the full source and share your perspective.")


def _exec_summary(rep: dict, s: dict) -> str:
    n = _n_items(s)
    facts = rep.get("facts", []) + [f"Figure: {x}" for x in rep.get("important_figures", [])]
    caveat = f" Caveat noted in the source: {rep['caveats'][0]}" if rep.get("caveats") else ""
    return (
        f"# {_title(rep)}\n## Overview\n{rep.get('summary') or MISSING}\n"
        f"## Key Findings\n{_bullets(rep.get('key_points', []), n)}\n"
        f"## Important Facts\n{_bullets(facts, n)}\n"
        f"## Conclusion\nThe source points summarised above are the findings it supports.{caveat}"
    )


def _linkedin(rep: dict, s: dict) -> str:
    n = _n_items(s)
    kp = rep.get("key_points", [])
    hook = _trim(kp[0], 140) if kp else _title(rep)
    return (
        f"## Hook\n{hook}\n## Post\n{rep.get('summary') or MISSING}\n"
        f"## Key Takeaways\n{_bullets(kp[1:] or kp, n)}\n"
        f"## Hashtags\n{_hashtags(rep)}\n## Call to Action\n{_cta(s.get('objective', ''))}"
    )


def _x_thread(rep: dict, s: dict) -> str:
    n = _n_items(s)
    texts = [rep.get("summary") or _title(rep)] + rep.get("key_points", [])[: n - 1 if n > 3 else n]
    texts = [t for t in texts if t]
    if s.get("detail_level") == "Low":
        texts = texts[:1]
    total = len(texts)
    posts = [f"{i}/{total} {_trim(t, 255)}" for i, t in enumerate(texts, 1)]
    return "\n\n".join(posts)


def _advisory(rep: dict, s: dict) -> str:
    n = _n_items(s)
    pool = rep.get("key_points", []) + rep.get("facts", []) + rep.get("caveats", [])
    severity = MISSING
    for item in pool:
        m = re.search(r"\b(critical|high|medium|low)\s+(?:severity|priority|risk)\b|severity[:\s]+(critical|high|medium|low)\b", item, re.I)
        if m:
            severity = _trim(item, 200)
            break
    impact = [i for i in pool if re.search(r"impact|affect|risk|loss|exposed|damage|compromis", i, re.I)]
    actions = [i for i in pool if re.search(r"recommend|should|must|advise|apply|update|patch|ensure|monitor", i, re.I)]
    caveats = list(rep.get("caveats", [])) + ["This advisory was generated automatically and has not been verified; human review is required."]
    return (
        f"# Advisory: {_title(rep)}\n## Severity / Priority\n{severity}\n"
        f"## Background\n{rep.get('summary') or MISSING}\n"
        f"## Key Observations\n{_bullets(rep.get('key_points', []), n)}\n"
        f"## Potential Impact\n{_bullets(impact, n)}\n"
        f"## Recommended Actions\n{_bullets(actions, n)}\n"
        f"## Caveats\n{_bullets(caveats, n + 1)}"
    )


def _presentation(rep: dict, s: dict) -> str:
    n = _n_items(s)
    kp = rep.get("key_points", [])
    facts = rep.get("facts", []) + [f"Figure: {x}" for x in rep.get("important_figures", [])]
    slides = [
        ("Overview", [rep.get("summary") or MISSING], "Title graphic or cover image", "Introduce the topic using the overview above."),
        ("Key Points", kp[:n] or [MISSING], "Icon list or numbered diagram", "Walk through each key point in order."),
        ("Facts and Figures", facts[:n] or [MISSING], "Table or bar chart of the figures", "Read out the exact figures and where they come from in the source."),
        ("Caveats and Limits", rep.get("caveats", [])[:n] or ["No caveats stated in the source."], "Warning callout box", "State clearly what is uncertain or unconfirmed."),
    ]
    out = [f"# {_title(rep)}"]
    for i, (title, bullets, visual, notes) in enumerate(slides, 1):
        body = "\n".join(f"- {_trim(b, 200)}" for b in bullets)
        out.append(f"## Slide {i}: {title}\n{body}\n**Suggested visual:** {visual}\n**Speaker notes:** {notes}")
    return "\n".join(out)


_DEMO_GENERATORS = {
    "executive_summary": _exec_summary,
    "linkedin": _linkedin,
    "x_thread": _x_thread,
    "advisory": _advisory,
    "presentation": _presentation,
}


def demo_generate(output_type: str, rep: dict, settings: dict) -> str:
    body = _DEMO_GENERATORS[output_type](rep, settings)
    return f"{DEMO_BANNER}\n\n{body}"
