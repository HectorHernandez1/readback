# Readback

PDF to podcast — converts study material into narrator-style audio using Claude and ElevenLabs.

## Setup

Create and activate the conda environment:

```bash
conda create -n readback python=3.12 -y
conda activate readback
```

Install the package:

```bash
cd readback
pip install -e .
```

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
```

## Usage

```bash
conda activate readback
readback paper.pdf
```

### Options

- `--voice` — ElevenLabs voice ID (defaults to Rachel)
- `--output-dir` — Output directory (defaults to `~/Documents/mp3`)

## How it works

1. Extracts text from PDF using pdfplumber
2. Rewrites content as a spoken-word narrator script via Claude
3. Converts script to speech via ElevenLabs
4. Saves the MP3 locally
