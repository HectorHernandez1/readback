import io
from datetime import datetime
from pathlib import Path

from elevenlabs import ElevenLabs

from .config import CHUNK_SIZE, DEFAULT_OUTPUT_DIR, DEFAULT_VOICE_ID, ELEVENLABS_API_KEY, ELEVENLABS_MODEL


def _chunk_text(text: str, size: int = CHUNK_SIZE) -> list[str]:
    """Split text into chunks, breaking at sentence boundaries when possible."""
    chunks = []
    while text:
        if len(text) <= size:
            chunks.append(text)
            break
        # Find last sentence-ending punctuation within the size limit
        cut = size
        for sep in [". ", "! ", "? ", "\n\n", "\n"]:
            pos = text.rfind(sep, 0, size)
            if pos != -1:
                cut = pos + len(sep)
                break
        chunks.append(text[:cut])
        text = text[cut:]
    return chunks


def synthesize(
    script: str,
    pdf_name: str,
    voice_id: str = DEFAULT_VOICE_ID,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Convert script to speech and save as MP3."""
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    chunks = _chunk_text(script)
    audio_parts: list[bytes] = []
    previous_request_ids: list[str] = []

    for i, chunk in enumerate(chunks, 1):
        print(f"  Generating audio chunk {i}/{len(chunks)}...")
        response = client.text_to_speech.convert(
            text=chunk,
            voice_id=voice_id,
            model_id=ELEVENLABS_MODEL,
            output_format="mp3_44100_128",
            previous_request_ids=previous_request_ids[-3:],
        )
        # response is a generator of bytes
        chunk_bytes = b"".join(response)
        audio_parts.append(chunk_bytes)

        # Extract request ID from the last response for continuity
        if hasattr(response, "request_id"):
            previous_request_ids.append(response.request_id)

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(pdf_name).stem
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"{stem}_{timestamp}.mp3"

    with open(output_path, "wb") as f:
        for part in audio_parts:
            f.write(part)

    return output_path
