import argparse
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .chat import answer_question
from .clean import clean_text
from .config import DEFAULT_OUTPUT_DIR, DEFAULT_VOICE_ID
from .extract import extract_text
from .fetch import FetchError, fetch_pdf
from .speak import synthesize
from .storage import list_sessions, load_session, pdf_path, save_pdf, save_session, update_audio

WEB_DIR = Path(__file__).parent / "web"


@dataclass
class PaperSession:
    url: str
    pdf_path: Path
    text: str
    audio_path: Path | None = None
    metadata: dict = field(default_factory=dict)


_SESSIONS: dict[str, PaperSession] = {}

app = FastAPI(title="Readback")


class LoadRequest(BaseModel):
    url: str


class AudioRequest(BaseModel):
    paper_id: str
    voice: str | None = None


class ChatRequest(BaseModel):
    paper_id: str
    question: str
    selection: str = ""


def _require(paper_id: str) -> PaperSession:
    session = _SESSIONS.get(paper_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="This paper is no longer loaded (the server may have restarted). "
            "Click Load again to re-fetch it.",
        )
    return session


@app.get("/api/health")
def health() -> dict:
    return {"ok": True}


@app.post("/api/load")
def load_paper(req: LoadRequest) -> dict:
    try:
        fetched = fetch_pdf(req.url)
    except FetchError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    raw_text = extract_text(str(fetched.path))
    if not raw_text:
        raise HTTPException(status_code=400, detail="no text extracted from PDF")

    try:
        text = clean_text(raw_text)
    except Exception:
        text = raw_text

    paper_id = uuid.uuid4().hex[:12]
    title = fetched.title or fetched.path.stem
    pdf_filename = save_pdf(paper_id, fetched.path, title)
    _SESSIONS[paper_id] = PaperSession(
        url=req.url,
        pdf_path=fetched.path,
        text=text,
        metadata={"title": title, "pdf_filename": pdf_filename},
    )
    save_session(paper_id=paper_id, url=req.url, title=title, text=text, pdf_filename=pdf_filename)
    return {
        "paper_id": paper_id,
        "title": title,
        "char_count": len(text),
        "text": text,
    }


@app.get("/api/papers")
def list_papers() -> dict:
    """List all previously loaded papers (library), newest first."""
    return {"papers": list_sessions()}


@app.get("/api/papers/{paper_id}")
def reopen_paper(paper_id: str) -> dict:
    """Reopen a previously saved paper without re-fetching."""
    data = load_session(paper_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Paper not found in library.")
    # Hydrate the in-memory session so audio/chat work.
    _SESSIONS[paper_id] = PaperSession(
        url=data["url"],
        pdf_path=Path(),
        text=data["text"],
        metadata={
            "title": data["title"],
            "audio_filename": data.get("audio_filename"),
            "pdf_filename": data.get("pdf_filename"),
        },
    )
    return {
        "paper_id": paper_id,
        "title": data["title"],
        "char_count": len(data["text"]),
        "text": data["text"],
        "saved_at": data.get("saved_at", ""),
    }


@app.post("/api/audio")
def make_audio(req: AudioRequest) -> dict:
    session = _require(req.paper_id)

    output_dir = DEFAULT_OUTPUT_DIR
    safe_title = "".join(c for c in session.metadata.get("title", "paper") if c not in '/\\:*?"<>|') or "paper"
    try:
        session.audio_path = synthesize(
            script=session.text,
            pdf_name=safe_title + ".pdf",
            voice_id=req.voice or DEFAULT_VOICE_ID,
            output_dir=output_dir,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=_friendly_api_error("ElevenLabs TTS", exc),
        )
    update_audio(req.paper_id, session.audio_path.name)
    return {"audio_url": f"/api/audio/{req.paper_id}"}


@app.get("/api/audio/{paper_id}")
def get_audio(paper_id: str):
    session = _require(paper_id)
    audio_path = session.audio_path
    # Fall back to the persisted filename if the in-memory path was lost on restart.
    if (audio_path is None or not audio_path.exists()) and session.metadata.get("audio_filename"):
        candidate = DEFAULT_OUTPUT_DIR / session.metadata["audio_filename"]
        if candidate.exists():
            audio_path = candidate
            session.audio_path = audio_path
    if audio_path is None or not audio_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Audio hasn't been generated yet. Click Generate audio first.",
        )
    return FileResponse(audio_path, media_type="audio/mpeg")


@app.get("/api/pdf/{paper_id}")
def download_pdf(paper_id: str):
    session = _require(paper_id)
    pdf_filename = session.metadata.get("pdf_filename")
    if not pdf_filename:
        raise HTTPException(status_code=404, detail="No PDF stored for this paper.")
    path = pdf_path(paper_id, pdf_filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found on disk.")
    safe_title = "".join(c for c in session.metadata.get("title", "paper") if c not in '/\\:*?"<>|') or "paper"
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=f"{safe_title}.pdf",
    )


@app.post("/api/chat")
def chat(req: ChatRequest) -> dict:
    session = _require(req.paper_id)
    try:
        answer = answer_question(
            question=req.question,
            paper_text=session.text,
            selection=req.selection,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=_friendly_api_error("DeepSeek chat", exc),
        )
    return {"answer": answer}


def _friendly_api_error(label: str, exc: Exception) -> str:
    """Turn an SDK exception into a human-readable message."""
    msg = str(exc).strip().lower()
    if "401" in msg or "unauthorized" in msg or "invalid api key" in msg:
        return f"{label} failed: API key is missing or invalid (check your .env)."
    if "429" in msg or "rate limit" in msg or "quota" in msg:
        return f"{label} failed: rate limit / quota exceeded. Wait and try again."
    if "connection" in msg or "timeout" in msg or "timed out" in msg:
        return f"{label} failed: could not reach the service (network/timeout)."
    return f"{label} failed: {exc}"


app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(WEB_DIR / "index.html")


def main():
    parser = argparse.ArgumentParser(description="Readback — local web UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    if not WEB_DIR.exists():
        print(f"Error: web directory missing: {WEB_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Readback UI: http://{args.host}:{args.port}")
    uvicorn.run("readback.server:app", host=args.host, port=args.port, reload=args.reload)
