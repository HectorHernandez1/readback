import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")

DEFAULT_OUTPUT_DIR = Path(
    os.environ.get("READBACK_OUTPUT_DIR", "~/Documents/mp3")
).expanduser()

DATA_DIR = Path(
    os.environ.get("READBACK_DATA_DIR", "~/.readback")
).expanduser()

DEFAULT_VOICE_ID = os.environ.get("READBACK_VOICE_ID", "U9tZtg3uJtVgXPkvosWR")

ELEVENLABS_MODEL = "eleven_multilingual_v2"
CHUNK_SIZE = 4500  # chars per TTS chunk

# DeepSeek (OpenAI-compatible) for the chat Q&A bot. Claude still does the script rewrite.
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.environ.get("READBACK_DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.environ.get("READBACK_DEEPSEEK_MODEL", "deepseek-chat")
CHAT_CONTEXT_CHARS = 50_000  # max extracted-text chars fed to the chat model
CLEAN_CHUNK_SIZE = 50_000   # max chars per DeepSeek cleanup chunk

# Unpaywall is used to resolve DOI links to an open-access PDF. A real email is polite.
UNPAYWALL_EMAIL = os.environ.get("READBACK_UNPAYWALL_EMAIL", "readback@example.com")
