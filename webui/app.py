"""Minimal web UI for ownscribe: upload audio -> transcript + summary. Run: uvicorn webui.app:app"""
import glob
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

import openai
from ownscribe.config import Config
from ownscribe.summarization import create_summarizer

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    k, _, v = line.partition("=")
    if k.strip() and not line.startswith("#"):
        os.environ.setdefault(k.strip(), v.strip())

config = Config.load()
config.summarization.host = os.environ.get("OPENAI_BASE_URL", config.summarization.host)

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "whisper-large-v3")  # served by the remote endpoint, nothing runs locally
client = openai.OpenAI(base_url=config.summarization.host, api_key=config.summarization.api_key or "not-needed")

app = FastAPI(title="meetingnotes")


def transcribe(path: str) -> str:
    """Downmix to 16 kHz mono mp3 in 10-min chunks so any recording fits the endpoint's size limit."""
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
                            "-f", "segment", "-segment_time", "600", f"{d}/c%04d.mp3"], capture_output=True, text=True)
        chunks = sorted(glob.glob(f"{d}/c*.mp3"))
        if r.returncode or not chunks:
            raise HTTPException(400, f"Could not read audio: {r.stderr.strip()[-200:]}")
        parts = []
        for c in chunks:
            with open(c, "rb") as audio:
                parts.append(client.audio.transcriptions.create(model=WHISPER_MODEL, file=audio).text.strip())
        return " ".join(parts)  # ponytail: no overlap between chunks, a word on a boundary may split


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


@app.post("/process")
def process(file: UploadFile = File(...)):
    suffix = Path(file.filename or "audio").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
    try:
        try:
            transcript = transcribe(tmp.name)
        except openai.APIError as e:
            raise HTTPException(502, f"Whisper endpoint error: {e}")
        summarizer = create_summarizer(config)
        if not summarizer.is_available():
            raise HTTPException(502, f"Summarizer not reachable at {config.summarization.host}")
        try:
            summary = summarizer.summarize(transcript)
        finally:
            summarizer.close()
        return {"transcript": transcript, "summary": summary}
    finally:
        os.unlink(tmp.name)
