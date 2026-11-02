"""Test 6: text preprocessing."""
from app.preprocessing.cleaner import clean_text, truncate_text


def test_collapses_whitespace_and_blank_lines():
    assert clean_text("a   b\n\n\n\n c") == "a b\n\nc"


def test_normalises_line_endings_and_tabs():
    assert clean_text("one\r\ntwo\rthree\tfour") == "one\ntwo\nthree four"


def test_removes_control_characters():
    assert clean_text("he\x00llo\x07 world") == "hello world"


def test_dehyphenates_line_breaks():
    assert clean_text("inter-\nnational") == "international"


def test_unicode_normalisation():
    assert clean_text("ﬁnance") == "finance"  # ligature -> plain letters


def test_empty_input():
    assert clean_text("") == "" and clean_text(None) == ""


def test_truncate_not_needed():
    assert truncate_text("short", 100) == ("short", False)


def test_truncate_prefers_sentence_boundary():
    # a sentence ends in the last 20% of the allowed length, so the cut snaps back to it
    text, truncated = truncate_text("One sentence here. Another sentence follows now.", 20)
    assert truncated and text == "One sentence here."
