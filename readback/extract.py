import re

import pdfplumber


def extract_text(pdf_path: str) -> str:
    """Extract text from a PDF, stripping common page artifacts."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    full_text = "\n\n".join(pages)

    # Strip standalone page numbers (lines that are just a number)
    full_text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", full_text)

    return full_text.strip()
