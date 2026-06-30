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

### Web UI

```bash
conda activate readback
readback-web
```

Open the printed URL (default http://127.0.0.1:8000), paste an arXiv, DOI, or
direct-PDF link, click **Load**, then **Generate audio**. The reader highlights
word-by-word as it plays (pause/play with the audio controls). Select any phrase
in the script, then ask questions in the chat panel — answers come from DeepSeek
with the paper as context.

### CLI

```bash
conda activate readback
readback paper.pdf
```

#### CLI Options

- `--voice` — ElevenLabs voice ID (defaults to Rachel)
- `--output-dir` — Output directory (defaults to `~/Documents/mp3`)

## How it works

1. Extracts text from PDF using pdfplumber, stripping citations, equations, and page artifacts
2. Converts the cleaned text to speech via ElevenLabs
3. Saves the MP3 locally
