"""Minimal web UI for ownscribe: upload audio -> transcript + summary. Run: uvicorn webui.app:app"""
import os
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse

from ownscribe.config import Config
from ownscribe.output.markdown import format_transcript
from ownscribe.pipeline import _create_transcriber
from ownscribe.summarization import create_summarizer

ROOT = Path(__file__).resolve().parent.parent
for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    k, _, v = line.partition("=")
    if k.strip() and not line.startswith("#"):
        os.environ.setdefault(k.strip(), v.strip())

config = Config.load()
config.summarization.host = os.environ.get("OPENAI_BASE_URL", config.summarization.host)

app = FastAPI(title="meetingnotes")
_lock = threading.Lock()  # ponytail: one job at a time; queue/worker if concurrency matters
_transcriber = None


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


@app.post("/process")
def process(file: UploadFile = File(...)):
    global _transcriber
    suffix = Path(file.filename or "audio").suffix or ".wav"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(file.file.read())
    try:
        with _lock:
            _transcriber = _transcriber or _create_transcriber(config)
            result = _transcriber.transcribe(Path(tmp.name))
        summarizer = create_summarizer(config)
        if not summarizer.is_available():
            raise HTTPException(502, f"Summarizer not reachable at {config.summarization.host}")
        try:
            summary = summarizer.summarize(result.speaker_text)
        finally:
            summarizer.close()
        return {"transcript": format_transcript(result), "summary": summary}
    finally:
        os.unlink(tmp.name)
