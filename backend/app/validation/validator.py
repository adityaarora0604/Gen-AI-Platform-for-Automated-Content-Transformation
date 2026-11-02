"""Output validation: structure checks and basic source-fidelity heuristics. (Owner: Shivam)

These are heuristics. They CANNOT prove that an output is accurate; they only flag obvious problems.
"""
import re
from typing import List, Optional

from app.prompt_templates.templates import OUTPUT_SPECS
from app.schemas import AppError

UNCERTAINTY_WORDS = re.compile(
    r"\b(unconfirmed|alleged|allegedly|reportedly|suspected|preliminary|unclear|under investigation|not yet confirmed)\b", re.I
)
CERTAINTY_WORDS = re.compile(r"\b(confirmed|verified|proven|definitely|guaranteed|certainly)\b", re.I)
NEGATED_CERTAINTY = re.compile(
    r"\b(?:not|never|no|yet to be|to be)\b[\w\s]{0,15}?\b(?:confirmed|verified|proven)\b", re.I
)
SEVERITY_WORDS =re.compile(r"\b(critical|high|medium|low|severe|severity|priority|urgent)\b", re.I)
PLACEHOLDER = re.compile(r"\[(?:insert|your|todo|tbd)[^\]]*\]|lorem ipsum", re.I)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower()).strip()


def _headings(content: str) -> List[str]:
    return [_norm(h) for h in re.findall(r"^\s*#{2,6}\s*(.+?)\s*$", content, re.M)]


def _numbers(text: str) -> set:
    text = re.sub(r"(?m)^\s*\d+/\d+\s", " ", text)  # thread numbering
    text = re.sub(r"(?i)slide\s+\d+", " ", text)  # slide numbers
    text = re.sub(r"(?m)^\s*\d+[.)]\s", " ", text)  # numbered lists
    text = re.sub(r"(?<![#\w])#\w+", " ", text)  # hashtags
    nums = set()
    for m in re.findall(r"\d+(?:[.,]\d+)*", text):
        n = m.replace(",", "")
        if len(n) > 1:  # ignore single digits such as "3 takeaways"
            nums.add(n)
    return nums


def check_structure(output_type: str, content: str) -> List[str]:
    warnings: List[str] = []
    spec = OUTPUT_SPECS[output_type]
    label = spec["label"]

    if spec["title_required"] and not re.search(r"(?m)^\s*#(?!#)\s*\S", content):
        warnings.append(f"{label}: missing title (a line starting with '# ').")

    found = _headings(content)
    for section in spec["sections"]:
        if not any(h.startswith(_norm(section)) for h in found):
            warnings.append(f"{label}: missing required section '{section}'.")

    if output_type == "linkedin" and not re.search(r"(?<![#\w])#[A-Za-z0-9_]+", content):
        warnings.append("LinkedIn Post: no hashtags found.")

    if output_type == "x_thread":
        posts = re.findall(r"(?m)^\s*(\d+)/(\d+)\s+(.+?)\s*$", content)
        if not posts:
            warnings.append("X Thread: no numbered posts found (expected lines like '1/3 text').")
        else:
            nums = [int(p[0]) for p in posts]
            totals = {int(p[1]) for p in posts}
            if nums != list(range(1, len(posts) + 1)) or totals != {len(posts)}:
                warnings.append("X Thread: post numbering is inconsistent.")
            for n, _, text in posts:
                length = len(f"{n}/{len(posts)} {text}")
                if length > 280:
                    warnings.append(f"X Thread: post {n} is {length} characters (limit 280).")

    if output_type == "presentation":
        slides = re.findall(r"(?im)^\s*#{2,6}\s*slide\s+\d+", content)
        if len(slides) < 3:
            warnings.append("Presentation: fewer than 3 slides found.")
        if len(re.findall(r"(?i)suggested visual", content)) < len(slides):
            warnings.append("Presentation: some slides are missing a 'Suggested visual'.")
        if len(re.findall(r"(?i)speaker notes", content)) < len(slides):
            warnings.append("Presentation: some slides are missing 'Speaker notes'.")
    return warnings


def check_fidelity(output_type: str, content: str, source_text: str) -> List[str]:
    """Heuristic source-fidelity checks."""
    warnings: List[str] = []
    label = OUTPUT_SPECS[output_type]["label"]

    extra = sorted(_numbers(content) - _numbers(source_text), key=lambda x: (len(x), x))
    if extra:
        shown = ", ".join(extra[:6])
        warnings.append(f"{label}: contains figure(s) not found in the source: {shown}. Please verify.")

    # Ignore negated or pending phrasing such as "has not been verified" or "yet to be confirmed".
    asserted = NEGATED_CERTAINTY.sub(" ", content)
    if UNCERTAINTY_WORDS.search(source_text) and CERTAINTY_WORDS.search(asserted):
        warnings.append(
            f"{label}: uses certainty wording (e.g. 'confirmed') while the source contains uncertain or "
            "unconfirmed information. Check that nothing uncertain is presented as fact."
        )

    if output_type == "advisory":
        m = re.search(r"(?is)##\s*severity[^\n]*\n(.+?)(?=\n#|\Z)", content)
        if m:
            value = m.group(1).strip()
            if "not specified" not in value.lower() and not SEVERITY_WORDS.search(source_text):
                warnings.append("Advisory: a severity/priority is stated but the source does not mention one.")

    if PLACEHOLDER.search(content):
        warnings.append(f"{label}: contains placeholder text.")
    return warnings


def validate_output(output_type: str, content: str, source_text: Optional[str] = "") -> List[str]:
    """Return a list of validation warnings (empty list = no issues found)."""
    if output_type not in OUTPUT_SPECS:
        raise AppError(f"Unknown output type '{output_type}'.", 400)
    if not content or not content.strip():
        return [f"{OUTPUT_SPECS[output_type]['label']}: output is empty."]
    warnings = check_structure(output_type, content)
    warnings += check_fidelity(output_type, content, source_text or "")
    return warnings
