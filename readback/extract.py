import re

import pdfplumber

_CITATION_BRACKET_RE = re.compile(r"\[[^\]\n]{0,60}\]")
_CITATION_PAREN_RE = re.compile(r"\([A-Z][A-Za-z'`-]+(?:\s+(?:et al\.?|and|&)\s+[A-Z][A-Za-z'`-]+)?,?\s+\d{4}[a-z]?\)")
_EQ_CHARS = re.compile(r"[=+∑∏∫∂√≤≥≠≈→←↔∞±÷×∈∉∀∃∇α-ωΑ-Ω]")
_URL_RE = re.compile(r"https?://\S+|doi:\S+|10\.\d{4,9}/\S+")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_FOOTNOTE_MARK_RE = re.compile(r"[∗†‡§¶]")
_ARXIV_STAMP_RE = re.compile(r"(?m)^\s*[\d.]+v\d+\s*\[.*?\]\s*$")


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF, stripping page artifacts and structural junk."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    full_text = "\n\n".join(pages)
    return _clean(full_text)


def _clean(text: str) -> str:
    # Strip everything from the References heading onward
    ref_match = re.search(r"(?m)^\s*References\s*$", text)
    if ref_match:
        text = text[: ref_match.start()]

    # Strip citations
    text = _CITATION_BRACKET_RE.sub(" ", text)
    text = _CITATION_PAREN_RE.sub(" ", text)

    # Strip URLs, DOIs, emails, footnote markers, arXiv stamps
    text = _URL_RE.sub(" ", text)
    text = _EMAIL_RE.sub(" ", text)
    text = _FOOTNOTE_MARK_RE.sub("", text)
    text = _ARXIV_STAMP_RE.sub("", text)

    # Drop equation-heavy lines
    kept_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            kept_lines.append("")
            continue
        if len(_EQ_CHARS.findall(stripped)) >= 2 and len(stripped) < 120:
            continue
        kept_lines.append(line)
    text = "\n".join(kept_lines)

    # Strip standalone page numbers
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)

    # Collapse whitespace
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
