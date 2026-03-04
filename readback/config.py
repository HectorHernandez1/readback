import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("READBACK_OUTPUT_DIR", "~/Documents/mp3")
).expanduser()

DEFAULT_VOICE_ID = os.environ.get("READBACK_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel

ELEVENLABS_MODEL = "eleven_multilingual_v2"
CHUNK_SIZE = 4500  # chars per TTS chunk
