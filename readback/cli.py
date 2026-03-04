import argparse
import sys
from pathlib import Path

from .config import DEFAULT_OUTPUT_DIR, DEFAULT_VOICE_ID
from .extract import extract_text
from .rewrite import rewrite_as_script
from .speak import synthesize


def main():
    parser = argparse.ArgumentParser(
        description="Readback — convert a PDF into narrator-style audio",
    )
    parser.add_argument("pdf", help="Path to the PDF file")
    parser.add_argument("--voice", default=DEFAULT_VOICE_ID, help="ElevenLabs voice ID")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"Error: file not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    print(f"[1/3] Extracting text from {pdf_path.name}...")
    text = extract_text(str(pdf_path))
    if not text:
        print("Error: no text extracted from PDF", file=sys.stderr)
        sys.exit(1)
    print(f"  Extracted {len(text):,} characters")

    print("[2/3] Rewriting as narrator script...")
    script = rewrite_as_script(text)
    print(f"  Script: {len(script):,} characters")

    print("[3/3] Generating audio...")
    output = synthesize(script, pdf_path.name, voice_id=args.voice, output_dir=args.output_dir)
    print(f"Done! Saved to {output}")
