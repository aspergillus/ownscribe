"""Minimal web UI for ownscribe: upload audio -> transcript + summary. Run: uvicorn webui.app:app"""
import asyncio
import glob
import logging
import os
import subprocess
import tempfile
import threading
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
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
log = logging.getLogger("uvicorn.error")


class Cancelled(Exception):
    pass


def transcribe(path: str, cancel: threading.Event) -> str:
    """Downmix to 16 kHz mono mp3 in 10-min chunks so any recording fits the endpoint's size limit."""
    with tempfile.TemporaryDirectory() as d:
        r = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "32k",
                            "-f", "segment", "-segment_time", "600", f"{d}/c%04d.mp3"], capture_output=True, text=True)
        chunks = sorted(glob.glob(f"{d}/c*.mp3"))
        if r.returncode or not chunks:
            raise HTTPException(400, f"Could not read audio: {r.stderr.strip()[-200:]}")
        parts = []
        for c in chunks:
            if cancel.is_set():
                raise Cancelled
            with open(c, "rb") as audio:
                parts.append(client.audio.transcriptions.create(model=WHISPER_MODEL, file=audio).text.strip())
        return " ".join(parts)  # ponytail: no overlap between chunks, a word on a boundary may split


@app.get("/", response_class=HTMLResponse)
def index():
    return (Path(__file__).parent / "index.html").read_text(encoding="utf-8")


def work(data: bytes, suffix: str, cancel: threading.Event) -> dict:
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
    try:
        try:
            transcript = transcribe(tmp.name, cancel)
        except openai.APIError as e:
            raise HTTPException(502, f"Whisper endpoint error: {e}")
        if cancel.is_set():
            raise Cancelled
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


@app.post("/process")
async def process(request: Request, file: UploadFile = File(...)):
    """Runs the job in a thread; if the browser disconnects (Cancel), stop before the next step."""
    cancel = threading.Event()
    job = asyncio.create_task(asyncio.to_thread(
        work, await file.read(), Path(file.filename or "audio").suffix or ".wav", cancel))
    while not job.done():
        if await request.is_disconnected():
            cancel.set()  # ponytail: the in-flight Whisper/LLM call finishes first, then work stops
            break
        await asyncio.sleep(0.5)
    try:
        return await job
    except Cancelled:
        log.info("job cancelled by client")
        return {"cancelled": True}
