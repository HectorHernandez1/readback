import json
import shutil
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR

SESSIONS_DIR = DATA_DIR / "sessions"
PDFS_DIR = DATA_DIR / "pdfs"


def _ensure_dir() -> Path:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return SESSIONS_DIR


def save_pdf(paper_id: str, source_pdf: Path, title: str) -> str:
    """Copy a fetched PDF into the data dir so it survives restarts.

    Returns the stored filename (not full path).
    """
    PDFS_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = "".join(c for c in title if c not in '/\\:*?"<>|') or "paper"
    filename = f"{paper_id}_{safe_title}.pdf"
    dest = PDFS_DIR / filename
    shutil.copy2(source_pdf, dest)
    return filename


def pdf_path(paper_id: str, filename: str) -> Path:
    return PDFS_DIR / filename


def save_session(
    paper_id: str,
    url: str,
    title: str,
    text: str,
    audio_filename: str | None = None,
    pdf_filename: str | None = None,
) -> None:
    """Persist a paper session to disk so it survives restarts."""
    _ensure_dir()
    record = {
        "paper_id": paper_id,
        "url": url,
        "title": title,
        "text": text,
        "audio_filename": audio_filename,
        "pdf_filename": pdf_filename,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
    }
    path = SESSIONS_DIR / f"{paper_id}.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")


def load_session(paper_id: str) -> dict | None:
    path = SESSIONS_DIR / f"{paper_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def list_sessions() -> list[dict]:
    """Return all saved sessions, newest first, without the full text body."""
    _ensure_dir()
    records = []
    for path in SESSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            records.append({
                "paper_id": data["paper_id"],
                "url": data["url"],
                "title": data["title"],
                "saved_at": data.get("saved_at", ""),
                "char_count": len(data.get("text", "")),
                "has_audio": bool(data.get("audio_filename")),
            })
        except (json.JSONDecodeError, KeyError):
            continue
    records.sort(key=lambda r: r.get("saved_at", ""), reverse=True)
    return records


def update_audio(paper_id: str, audio_filename: str) -> None:
    """Record the generated audio filename on an existing session."""
    data = load_session(paper_id)
    if data is None:
        return
    data["audio_filename"] = audio_filename
    path = SESSIONS_DIR / f"{paper_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
