import regex as re

# Non-breaking spaces, thin spaces, en-dash, em-dash, soft hyphen, zero-width chars
_INVISIBLE_OR_DASH = r'[\s\u00a0\u2002\u2003\u2009\u200a\u200b\u200c\u200d\u00ad\u2010\u2011\u2012\u2013\u2014\-]*'

# Match broken year tokens: "2 0 3 0", "2-0-3-0", "20\u00a030", ligatures, etc.
_YEAR_RE = re.compile(
    r'(?<!\d)2' + _INVISIBLE_OR_DASH + r'0' + _INVISIBLE_OR_DASH +
    r'([0-9])' + _INVISIBLE_OR_DASH + r'([0-9])(?!\d)',
    re.IGNORECASE
)


def normalize_year_tokens(text: str) -> str:
    """Repair broken year tokens from PDF extraction.

    Handles: '20 30', '2-0-3-0', '20\u00a030' (non-breaking space),
    '20\u201330' (en-dash), soft hyphens, zero-width chars, etc.
    """
    return _YEAR_RE.sub(r'20\1\2', text)
