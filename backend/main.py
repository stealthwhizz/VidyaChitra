"""
VidyaChitra Backend — FastAPI application.

Routes:
  POST /api/upload   — Upload PDF, extract chapter JSON, return session ID
  GET  /api/generate — SSE stream: run all generation tasks in parallel
  POST /api/chat     — Stream a grounded chat response
"""

import asyncio
import json
import os
import tempfile
import traceback
import uuid
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv

# Load .env from project root (VidyaChitra/.env) regardless of where uvicorn is started.
# Falls back to CWD as well, so Docker / other setups still work.
_root_env = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_root_env)
load_dotenv()  # also check CWD as fallback

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from ingestion.pdf_processor import process_pdf
from generation.question_forger import generate_questions
from generation.vernacular_narrator import generate_narration
from generation.video_generator import generate_diagram_video
from generation.document_chat import chat_stream

app = FastAPI(title="VidyaChitra API", version="1.0.0")

# CORS — allow frontend dev servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve generated files locally when GCS is not configured
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
PDF_DIR = STATIC_DIR / "pdfs"
PDF_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory session store: { session_id: chapter_json }
sessions: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# POST /api/upload
# ---------------------------------------------------------------------------

@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
):
    """
    Accept a PDF upload, auto-detect language/board/class via Gemini vision,
    and return a session ID plus detected metadata.
    """
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        # Be lenient — some browsers send octet-stream for PDF
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Verify GOOGLE_API_KEY is present before wasting time on processing
    if not os.environ.get("GOOGLE_API_KEY"):
        raise HTTPException(
            status_code=500,
            detail="GOOGLE_API_KEY is not set. Add it to your .env file."
        )

    session_id = str(uuid.uuid4())
    content = await file.read()

    # Save PDF to static/pdfs/ so the frontend can display it
    pdf_static_path = PDF_DIR / f"{session_id}.pdf"
    pdf_static_path.write_bytes(content)
    pdf_url = f"/static/pdfs/{session_id}.pdf"

    tmp_path: str | None = None
    try:
        # Also write to a temp file for pdf_processor (which needs a file path)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        # Run PDF processing in thread pool (language/board/class are auto-detected)
        loop = asyncio.get_running_loop()
        chapter_json = await loop.run_in_executor(
            None, process_pdf, tmp_path
        )

    except HTTPException:
        raise
    except Exception as e:
        # Surface the real error instead of a silent 500
        tb = traceback.format_exc()
        print(f"[upload] Error during PDF processing:\n{tb}")
        raise HTTPException(status_code=500, detail=f"PDF processing failed: {str(e)}")
    finally:
        if tmp_path and Path(tmp_path).exists():
            os.unlink(tmp_path)

    # Attach session_id and pdf_url to chapter JSON so sub-modules can use them
    chapter_json["session_id"] = session_id
    chapter_json["pdf_url"] = pdf_url
    sessions[session_id] = chapter_json

    return {
        "session_id": session_id,
        "chapter_name": chapter_json.get("chapter_name", "Unknown Chapter"),
        "num_pages": chapter_json.get("num_pages_processed", 0),
        "total_pages": chapter_json.get("total_pages", 0),
        "num_diagrams": len(chapter_json.get("diagrams", [])),
        "key_concepts": chapter_json.get("key_concepts", [])[:10],
        "pdf_url": pdf_url,
        "language": chapter_json.get("language", "en-IN"),
        "board": chapter_json.get("board", ""),
        "class_level": chapter_json.get("class_level", "10"),
    }


# ---------------------------------------------------------------------------
# GET /api/generate  (SSE)
# ---------------------------------------------------------------------------

@app.get("/api/generate")
async def generate(
    request: Request,
    session_id: str,
    board: str = "CBSE Class 10",
    language: str = "en-IN",
    class_level: str = "10",
):
    """
    SSE stream that runs question generation, audio narration, and video
    generation concurrently. Yields each result the moment it's ready.
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found. Please upload a PDF first.")

    chapter_json = sessions[session_id]
    # Update session metadata with current request params
    chapter_json["board"] = board
    chapter_json["language"] = language
    chapter_json["class_level"] = class_level

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Yield summary immediately — it was computed during PDF processing
        summary_text = chapter_json.get("summary_text", "")
        yield {
            "event": "summary",
            "data": json.dumps({"text": summary_text, "chapter_name": chapter_json.get("chapter_name", "")})
        }

        # Set up queue for concurrent tasks
        queue: asyncio.Queue = asyncio.Queue()

        async def run_task(coro, event_type: str) -> None:
            try:
                result = await coro
                await queue.put({"event": event_type, "data": result})
            except Exception as e:
                print(f"[main] Task '{event_type}' failed: {e}")
                await queue.put({
                    "event": "error",
                    "data": {"branch": event_type, "msg": str(e)}
                })
            finally:
                await queue.put(None)  # sentinel

        loop = asyncio.get_running_loop()
        tasks = [
            asyncio.create_task(run_task(
                loop.run_in_executor(None, generate_questions, chapter_json, board, language),
                "mcqs"
            )),
            asyncio.create_task(run_task(
                loop.run_in_executor(None, generate_narration, chapter_json, language),
                "audio"
            )),
            asyncio.create_task(run_task(
                # Two-step pipeline: Gemini picks concept + writes script,
                # then Gemini writes Manim code from that script.
                generate_diagram_video(chapter_json, language, session_id),
                "video"
            )),
        ]

        # Drain the queue as results arrive
        pending = len(tasks)
        while pending > 0:
            # Check if client disconnected
            if await request.is_disconnected():
                for task in tasks:
                    task.cancel()
                return

            try:
                item = await asyncio.wait_for(queue.get(), timeout=15.0)
            except asyncio.TimeoutError:
                # Keepalive — prevents browser/proxy from dropping the SSE connection
                # while Manim is rendering (can take 60-180 seconds per attempt)
                yield {"event": "ping", "data": "{}"}
                continue

            if item is None:
                pending -= 1
                continue

            event_type = item["event"]
            data = item["data"]

            if event_type == "error":
                yield {"event": "error", "data": json.dumps(data)}
            elif event_type == "mcqs":
                yield {"event": "mcqs", "data": json.dumps(data)}
                if isinstance(data, dict) and data.get("exam_tip"):
                    yield {"event": "examtip", "data": json.dumps({"tip": data["exam_tip"]})}
            elif event_type == "audio":
                yield {"event": "audio", "data": json.dumps({"url": data})}
            elif event_type == "video":
                yield {"event": "video", "data": json.dumps({"url": data})}

        yield {"event": "done", "data": json.dumps({"msg": "All generation complete"})}

    return EventSourceResponse(event_generator())


# ---------------------------------------------------------------------------
# POST /api/chat
# ---------------------------------------------------------------------------

class ChatBody(BaseModel):
    session_id: str
    question: str
    language: str = "en-IN"
    history: list[dict] = []


@app.post("/api/chat")
async def chat_endpoint(body: ChatBody):
    """
    Stream a grounded chat response from VidyaChitra.
    Response is streamed as plain text chunks.
    """
    if body.session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found.")

    chapter_json = sessions[body.session_id]

    async def response_generator():
        async for chunk in chat_stream(
            body.question,
            chapter_json,
            body.language,
            body.history
        ):
            yield chunk

    return StreamingResponse(response_generator(), media_type="text/plain; charset=utf-8")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    api_key_set = bool(os.environ.get("GOOGLE_API_KEY"))
    return {
        "status": "ok",
        "sessions": len(sessions),
        "google_api_key_set": api_key_set,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080, reload=True)
