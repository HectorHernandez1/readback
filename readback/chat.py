from openai import OpenAI

from .config import (
    CHAT_CONTEXT_CHARS,
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_MODEL,
)

SYSTEM_PROMPT = (
    "You are a reading assistant for academic papers. Answer the user's question "
    "using the provided paper context. If the user highlighted a specific phrase, "
    "focus your explanation on that phrase and define any jargon. Quote short spans "
    "from the context when helpful. If the answer is not in the context, say so "
    "plainly rather than guessing."
)


def answer_question(
    question: str,
    paper_text: str,
    selection: str = "",
) -> str:
    """Answer a question about the paper using DeepSeek, with the paper as context."""
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    context = paper_text[:CHAT_CONTEXT_CHARS]
    user_parts = [f"### Paper context\n{context}"]
    if selection.strip():
        user_parts.append(f"### Highlighted phrase\n{selection.strip()}")
    user_parts.append(f"### Question\n{question.strip()}")
    user_content = "\n\n".join(user_parts)

    response = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )
    return response.choices[0].message.content or ""
