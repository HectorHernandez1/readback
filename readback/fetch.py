import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

import httpx

from .config import UNPAYWALL_EMAIL

_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})(v\d+)?", re.IGNORECASE)
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"']+")
_TIMEOUT = 60.0


class FetchError(Exception):
    """Raised when a paper URL cannot be resolved or downloaded."""


@dataclass
class FetchedPaper:
    path: Path
    title: str


def fetch_pdf(url: str) -> FetchedPaper:
    """Resolve a paper URL (arXiv, DOI, or direct PDF) and download it locally."""
    url = url.strip()
    if not url:
        raise FetchError("empty URL")

    pdf_url, title = _resolve(url)
    path = _download(pdf_url)
    return FetchedPaper(path=path, title=title or path.stem)


def _resolve(url: str) -> tuple[str, str]:
    lowered = url.lower()

    if "arxiv.org" in lowered:
        return _resolve_arxiv(url)

    if "doi.org" in lowered or _DOI_RE.search(url):
        return _resolve_doi(url)

    # Assume a direct PDF link; derive a title from the URL.
    parsed = urlparse(url)
    stem = Path(parsed.path).stem
    title = unquote(stem).replace("-", " ").replace("_", " ").strip()
    return url, title or "paper"


def _resolve_arxiv(url: str) -> tuple[str, str]:
    match = _ARXIV_ID_RE.search(url)
    if not match:
        raise FetchError(f"could not parse arXiv ID from: {url}")
    arxiv_id = match.group(1)
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    return pdf_url, _arxiv_title(arxiv_id)


def _arxiv_title(arxiv_id: str) -> str:
    """Ask the arXiv API for the paper title; fall back to the id."""
    try:
        resp = httpx.get(
            "http://export.arxiv.org/api/query",
            params={"id_list": arxiv_id, "max_results": 1},
            timeout=15.0,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            m = re.search(r"<entry>.*?<title>(.*?)</title>", resp.text, re.DOTALL)
            if m:
                return _clean_title(m.group(1))
    except httpx.HTTPError:
        pass
    return arxiv_id


def _resolve_doi(url: str) -> tuple[str, str]:
    doi_match = _DOI_RE.search(url)
    if doi_match:
        doi = doi_match.group(0)
    else:
        # Handle bare doi.org/<doi> links.
        doi = url.split("doi.org/", 1)[-1]
        doi = doi.split("?", 1)[0].split("#", 1)[0]

    if not doi:
        raise FetchError(f"could not parse DOI from: {url}")

    # Try Unpaywall for an open-access PDF first (avoids publisher paywalls).
    title = doi
    try:
        resp = httpx.get(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": UNPAYWALL_EMAIL},
            timeout=_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code == 200:
            data = resp.json()
            title = _clean_title(data.get("title") or doi)
            best = data.get("best_oa_location") or {}
            pdf = best.get("url_for_pdf")
            if pdf:
                return pdf, title
    except httpx.HTTPError:
        pass

    raise FetchError(
        f"no open-access PDF found for DOI {doi}; Unpaywall had no PDF link. "
        "Try pasting the direct PDF URL instead."
    )


def _clean_title(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()


def _download(pdf_url: str) -> Path:
    try:
        with httpx.stream(
            "GET", pdf_url, timeout=_TIMEOUT, follow_redirects=True,
            headers={"User-Agent": "readback/0.1 (+https://github.com/anomalyco/readback)"},
        ) as resp:
            if resp.status_code != 200:
                raise FetchError(f"download failed: HTTP {resp.status_code} for {pdf_url}")

            content_type = resp.headers.get("content-type", "")
            suffix = ".pdf"
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
            with tmp as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
            path = Path(tmp.name)
    except httpx.HTTPError as exc:
        raise FetchError(f"download failed: {exc}") from exc

    if not _looks_like_pdf(path, content_type):
        path.unlink(missing_ok=True)
        raise FetchError(
            f"resolved URL did not return a PDF (content-type {content_type!r}). "
            "Paste the direct PDF link."
        )
    return path


def _looks_like_pdf(path: Path, content_type: str) -> bool:
    if "pdf" in content_type.lower():
        return True
    with path.open("rb") as f:
        return f.read(5) == b"%PDF-"
