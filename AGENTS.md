# AGENTS.md

PDF → narrator-style audio. Two entry points: a CLI (`readback`) and a local web UI (`readback-web`). pdfplumber extracts text; DeepSeek cleans it (fixes spacing, strips equations/citations/references); ElevenLabs synthesizes an MP3; the web UI adds a DeepSeek-powered chat panel that answers questions about the paper. Single package, no tests/lint/CI configured.

## Commands

```bash
pip install -e .          # installs `readback` (CLI) and `readback-web` (UI)
readback paper.pdf        # CLI: extract → clean → synthesize
readback-web              # UI: FastAPI on http://127.0.0.1:8000 (--reload supported)
```

Requires Python ≥3.10 (`pyproject.toml`); README sets up a conda env `readback` on 3.12. API keys come from `.env` (see `.env.example`): `ELEVENLABS_API_KEY`, `DEEPSEEK_API_KEY`, plus optional `READBACK_OUTPUT_DIR`, `READBACK_VOICE_ID`, `READBACK_DEEPSEEK_MODEL`, `READBACK_UNPAYWALL_EMAIL`. If adding tests or linting, prefer pytest and ruff.

## Architecture

Two surfaces share one pipeline of single-responsibility modules.

- `cli.py` — argparse CLI entry `main()`; orchestrates extract → clean → synthesize.
- `server.py` — FastAPI app + `main()` (uvicorn). In-memory `_SESSIONS` dict maps `paper_id → PaperSession` (url, pdf_path, text, audio_path). Endpoints: `POST /api/load` (fetch+extract+clean), `/api/audio` (TTS), `GET /api/audio/{id}` (MP3 stream), `POST /api/chat` (DeepSeek). Serves the static UI from `web/` at `/` and `/static`.
- `fetch.py` — `fetch_pdf(url)` resolves arXiv abs/pdf, DOI (via Unpaywall for an open PDF), or direct PDF links, downloads to a temp file, validates `%PDF-` magic bytes. Returns `FetchedPaper(path, title)`. Raises `FetchError`.
- `extract.py` — `extract_text()` via pdfplumber; regex-strips references section, bracketed/parenthetical citations, equation-heavy lines, URLs/DOIs, emails, footnote markers, arXiv stamps, and page numbers.
- `clean.py` — `clean_text()` via the DeepSeek API (OpenAI-compatible `openai` SDK). Fixes word-spacing artifacts from pdfplumber and removes residual equations/tables. Chunks at `CLEAN_CHUNK_SIZE` (50K chars) for long papers. Falls back to raw extraction if DeepSeek fails.
- `chat.py` — `answer_question()` via the DeepSeek API. Feeds the cleaned paper (capped at `CHAT_CONTEXT_CHARS`) plus an optional highlighted selection.
- `speak.py` — `synthesize()` via the ElevenLabs SDK. Chunks text at `CHUNK_SIZE` (4500 chars) on sentence boundaries and threads `previous_request_ids` (last 3) for voice continuity. Writes `{pdf_stem}_{YYYYMMDD_HHMMSS}.mp3` into `output_dir` (default `~/Documents/mp3`).
- `config.py` — env loading + module-level constants (`CHUNK_SIZE`, `ELEVENLABS_MODEL`, `DEEPSEEK_*`, `CLEAN_CHUNK_SIZE`, default voice Rachel).
- `web/` — vanilla JS frontend (no build step): `index.html`, `app.js`, `style.css`. Word-by-word highlight is **proportional** (timing estimated from `audio.duration` weighted by token length in `app.js`, not from ElevenLabs alignment), good enough for karaoke.

CLI prints numbered progress `[1/3]`..`[3/3]`; the UI shows status in the top bar.

## Conventions

- **Config loads at import time.** `config.py` calls `load_dotenv()` and reads env vars at module top level. Any `from .config import ...` triggers `.env` loading and freezes values at that point — set keys in `.env` (or export them) before running.
- **Clients are constructed inside functions, not at module level** (`clean.py`, `speak.py`, `chat.py`). API keys default to `""`, so missing keys surface as API errors at call time, not import time.
- **Errors:** CLI uses `print("Error: ...", file=sys.stderr)` then `sys.exit(1)`; the server raises `HTTPException(status_code=4xx/5xx, detail=...)`. Validate inputs early (`cli.py`, `fetch.py`).
- **Style:** modern type hints (`list[str]`, not `List[str]`, and `Path | None`), `pathlib.Path` for all paths (expand `~`), double-quoted strings, f-strings, private helpers prefixed `_`, UPPER_CASE constants in `config.py`, dataclasses for simple state. Mirror the existing modules rather than introducing new patterns.
