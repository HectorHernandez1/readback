import anthropic

from .config import ANTHROPIC_API_KEY

SYSTEM_PROMPT = (
    "You are a narrator preparing study material for audio. "
    "Rewrite the following content as a clear, spoken-word script. "
    "Make it sound natural when read aloud — use transitions, explain "
    "concepts clearly, and avoid jargon notation that doesn't work in "
    "audio (like equations or citations). Keep the substance intact."
)


def rewrite_as_script(text: str) -> str:
    """Send extracted text to Claude and return a narrator-style script."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return message.content[0].text
