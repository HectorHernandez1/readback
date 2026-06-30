from openai import OpenAI

from .config import (
    CLEAN_CHUNK_SIZE,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)

SYSTEM_PROMPT = (
    "You are a text cleanup tool for text-to-speech. The user will give you text "
    "extracted from a PDF that has formatting problems. Clean it for spoken audio:\n\n"
    "1. Insert missing spaces between words that got joined during PDF extraction "
    "(e.g. 'Providedproperattributionisprovided' -> 'Provided proper attribution is provided')\n"
    "2. Remove any remaining equations, formulas, and mathematical notation\n"
    "3. Remove table data, tabular content, and numbers-only lines\n"
    "4. Remove figure captions and visualization artifacts\n"
    "5. Remove reversed or garbled text\n"
    "6. Keep ALL prose content exactly as written — do NOT rewrite, summarize, "
    "or change the wording\n"
    "7. Preserve paragraph breaks\n"
    "8. Return ONLY the cleaned text with no commentary or preamble"
)


def clean_text(text: str) -> str:
    """Clean extracted PDF text via DeepSeek: fix spacing, remove non-spoken junk."""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    chunks = _chunk(text)
    cleaned = []
    for chunk in chunks:
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk},
            ],
        )
        cleaned.append(response.choices[0].message.content or "")

    return "\n\n".join(cleaned).strip()


def _chunk(text: str, size: int = CLEAN_CHUNK_SIZE) -> list[str]:
    """Split text into chunks at paragraph/sentence boundaries."""
    chunks = []
    while text:
        if len(text) <= size:
            chunks.append(text)
            break
        cut = size
        for sep in ["\n\n", ". ", "! ", "? ", "\n"]:
            pos = text.rfind(sep, 0, size)
            if pos != -1:
                cut = pos + len(sep)
                break
        chunks.append(text[:cut])
        text = text[cut:]
    return chunks
