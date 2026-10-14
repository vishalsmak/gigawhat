"""Does a quote really appear in its source? Matching that tolerates how models and PDFs write
punctuation, but never a changed number."""

import re
from difflib import SequenceMatcher

MIN_QUOTE_FRAGMENT = 12
# Near-exact matching for long quotes: most of the quote must be one unbroken match.
NEAR_MATCH_MIN_LENGTH = 40
NEAR_MATCH_SHARE = 0.85
ELLIPSIS = re.compile(r"\s*(?:\.\.\.|…)\s*")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
# Typographic quotes, hyphens, dashes and spaces, which models and documents use interchangeably:
# "ESS\u2011BRK" with a non-breaking hyphen must match "ESS-BRK".
TYPOGRAPHY = {
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2010": "-",
    "\u2011": "-",
    "\u2012": "-",
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u00a0": " ",
    "\u202f": " ",
}


def quote_found(quote: str, source_text: str) -> bool:
    """True when every fragment of the quote (split at ellipses) appears in the source, in order,
    exactly or near-exactly; and every number in the quote appears in the source."""
    fragments = [f for f in ELLIPSIS.split(_normalise(quote)) if f]
    if not fragments or any(len(f) < MIN_QUOTE_FRAGMENT for f in fragments):
        return False
    haystack = _normalise(source_text)
    if not set(NUMBER.findall(quote)) <= set(NUMBER.findall(source_text)):
        return False
    position = 0
    for fragment in fragments:
        position = _find_near(fragment, haystack, position)
        if position < 0:
            return False
    return True


def _find_near(fragment: str, haystack: str, start: int) -> int:
    """End of the fragment's match at or after start, or -1. Long fragments may differ slightly
    (PDF hyphenation, punctuation) as long as most of them is one unbroken match."""
    exact = haystack.find(fragment, start)
    if exact >= 0:
        return exact + len(fragment)
    if len(fragment) < NEAR_MATCH_MIN_LENGTH:
        return -1
    matcher = SequenceMatcher(None, fragment, haystack, autojunk=False)
    block = matcher.find_longest_match(0, len(fragment), start, len(haystack))
    if block.size / len(fragment) < NEAR_MATCH_SHARE:
        return -1
    return block.b + block.size


def _normalise(text: str) -> str:
    for old, new in TYPOGRAPHY.items():
        text = text.replace(old, new)
    return " ".join(text.lower().split()).strip(" .\"'")
