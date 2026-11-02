"""Preprocessing: basic cleaning and normalisation of extracted text. (Owner: Aditya)"""
import re
import unicodedata


def clean_text(text: str) -> str:
    """Normalise unicode, strip control chars, collapse whitespace, de-hyphenate line breaks."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # remove control characters except newline and tab
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    # join words hyphenated across line breaks: "inter-\nnational" -> "international"
    text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
    text = text.replace("\t", " ")
    text = re.sub(r"[ ]{2,}", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_text(text: str, max_chars: int):
    """Return (text, truncated_flag)."""
    if len(text) <= max_chars:
        return text, False
    cut = text[:max_chars]
    # try to end on a sentence boundary
    idx = max(cut.rfind(". "), cut.rfind("\n"))
    if idx > max_chars * 0.8:
        cut = cut[: idx + 1]
    return cut.strip(), True
