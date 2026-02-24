"""
PDF Processor — feeds the raw PDF bytes directly to Gemini 2.5 Flash for native
document understanding.

Gemini's PDF mode reads vector text, embedded fonts (including Indic scripts),
and visual diagrams in one pass — no page-image rendering needed.

API call budget: 1 Gemini call for the entire PDF.
"""

import io
import json
import os
import re
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF — used only for page count + truncation
from google import genai
from google.genai import types

MAX_PAGES = 15   # Truncate long PDFs to keep generation under ~30 s

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


def _extract_json(text: str) -> Any:
    """Extract JSON from a string that may contain markdown fences."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = match.group(1) if match else text
    raw = raw.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{") if "{" in raw else raw.find("[")
        if start != -1:
            return json.loads(raw[start:])
        raise


def _truncate_pdf(pdf_path: str, max_pages: int) -> bytes:
    """Return raw bytes of a PDF containing only the first max_pages pages."""
    doc = fitz.open(pdf_path)
    total = len(doc)
    if total <= max_pages:
        doc.close()
        return Path(pdf_path).read_bytes()

    # Build a new in-memory PDF with just the first max_pages pages
    out = fitz.open()
    out.insert_pdf(doc, from_page=0, to_page=max_pages - 1)
    buf = io.BytesIO()
    out.save(buf)
    out.close()
    doc.close()
    return buf.getvalue()


# ── Gemini native-PDF prompt ─────────────────────────────────────────────────
BATCH_PROMPT = """You are an expert at analysing Indian school textbook PDFs.
You are given a complete PDF chapter from an Indian school textbook.

Read the ENTIRE document (all pages, diagrams, tables, formulas) and respond
with ONLY a single valid JSON object — no other text, no markdown:

{
  "chapter_name": "<title of the chapter, from the first page heading>",
  "detected_language": "<BCP-47 code of the textbook's primary language: kn-IN, hi-IN, ta-IN, te-IN, mr-IN, or en-IN>",
  "detected_board": "<school board name if identifiable (e.g. 'Karnataka SSLC', 'CBSE Class 10', 'Maharashtra SSC', 'Tamil Nadu State Board'), otherwise null>",
  "detected_class_level": "<class/grade number as a string if identifiable (e.g. '10', '9'), otherwise null>",
  "pages": [
    {
      "page_number": 1,
      "page_text": "<all visible text on this page verbatim — preserve Indic script exactly>",
      "has_diagrams": true,
      "diagrams": [
        {
          "type": "<ray diagram | circuit diagram | biological diagram | chemical diagram | geographical map | flow chart | other>",
          "description": "<detailed visual description of the diagram including all elements>",
          "labels": ["<label as it appears in the book>"],
          "concept": "<the scientific concept this diagram illustrates — in English>",
          "animation_hint": "<how to animate this: e.g. 'Draw coil first, then show magnetic field lines, then label N and S poles'>"
        }
      ],
      "formulas": ["<formula as readable text, e.g. 'F = ma'>"],
      "key_concepts": ["<concept 1>", "<concept 2>"]
    }
  ],
  "all_key_concepts": ["<deduplicated, all key concepts across all pages>"],
  "all_formulas": ["<deduplicated, all formulas across all pages>"],
  "all_diagrams": ["<English concept name for every diagram found>"],
  "summary_text": "<IMPORTANT: 300-400 word teacher-style chapter summary written ENTIRELY in the textbook language (detected_language). Write conversationally as a teacher explaining to a student. Cover all key concepts and formulas. End with 2 board-pattern exam tips. Must be 100% in detected_language — NOT in English unless the textbook is English.>"
}

Rules:
- Preserve Indic/vernacular script verbatim in page_text and summary_text
- diagram 'concept' field must always be in English (used for video animation)
- diagram 'labels' can be in the original language of the book
- Respond with ONLY the JSON object — absolutely no other text"""


def process_pdf(pdf_path: str, board: str = "Unknown", language: str = "auto", class_level: str = "10") -> dict:
    """
    Process a PDF using Gemini's native PDF understanding.
    Passes raw PDF bytes (not rendered images) for better text accuracy,
    especially for Indic scripts and complex diagrams.
    Language, board, and class are auto-detected from the content.
    """
    client = _get_client()

    # Get total page count and build a (possibly truncated) PDF
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()

    pages_to_process = min(total_pages, MAX_PAGES)
    print(f"[pdf_processor] PDF has {total_pages} pages; sending first {pages_to_process} to Gemini (native PDF mode)...")

    pdf_bytes = _truncate_pdf(pdf_path, MAX_PAGES)

    contents: list[Any] = [
        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
        types.Part.from_text(text=BATCH_PROMPT),
    ]

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
        )
        result = _extract_json(response.text)
    except Exception as e:
        print(f"[pdf_processor] Gemini extraction failed: {e}")
        result = _make_fallback_result(pdf_path, pages_to_process)

    # ── Auto-detected metadata (fall back to passed-in values if missing) ────
    _LANG_NORMALIZE = {
        "kannada": "kn-IN", "kn": "kn-IN", "kn-in": "kn-IN",
        "hindi":   "hi-IN", "hi": "hi-IN", "hi-in": "hi-IN",
        "tamil":   "ta-IN", "ta": "ta-IN", "ta-in": "ta-IN",
        "telugu":  "te-IN", "te": "te-IN", "te-in": "te-IN",
        "marathi": "mr-IN", "mr": "mr-IN", "mr-in": "mr-IN",
        "english": "en-IN", "en": "en-IN", "en-in": "en-IN",
    }
    raw_lang = (result.get("detected_language") or "").strip()
    detected_language = _LANG_NORMALIZE.get(raw_lang.lower(), raw_lang) or (language if language != "auto" else "en-IN")
    detected_board    = result.get("detected_board")    or board
    detected_class    = result.get("detected_class_level") or class_level

    print(f"[pdf_processor] Detected: lang={detected_language} board={detected_board} class={detected_class}")

    # ── Normalise ────────────────────────────────────────────────────────────
    pages_data: list[dict] = result.get("pages", [])

    all_diagrams: list[dict] = []
    for page in pages_data:
        all_diagrams.extend(page.get("diagrams", []))

    full_text = "\n\n".join(
        p.get("page_text", "") for p in pages_data if p.get("page_text")
    )

    chapter_name = result.get("chapter_name") or _infer_chapter_name_from_text(full_text, pdf_path)

    chapter_json = {
        "chapter_name": chapter_name,
        "board": detected_board,
        "language": detected_language,
        "class_level": detected_class,
        "num_pages_processed": pages_to_process,
        "total_pages": total_pages,
        "key_concepts": result.get("all_key_concepts", []),
        "formulas": result.get("all_formulas", []),
        "diagrams": all_diagrams,
        "full_text": full_text,
        "summary_text": result.get("summary_text", ""),
        "pages": pages_data,
    }

    print(
        f"[pdf_processor] Done: '{chapter_name}' | "
        f"{len(all_diagrams)} diagrams | "
        f"{len(chapter_json['key_concepts'])} concepts"
    )
    return chapter_json


def _infer_chapter_name_from_text(full_text: str, pdf_path: str) -> str:
    lines = [l.strip() for l in full_text.split("\n") if l.strip()]
    for line in lines[:10]:
        if len(line) > 4 and not line.startswith("Class") and not line.isdigit():
            return line[:100]
    return Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()


def _make_fallback_result(pdf_path: str, num_pages: int) -> dict:
    name = Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()
    return {
        "chapter_name": name,
        "detected_language": None,
        "detected_board": None,
        "detected_class_level": None,
        "pages": [{"page_number": i + 1, "page_text": "", "has_diagrams": False,
                   "diagrams": [], "formulas": [], "key_concepts": []}
                  for i in range(num_pages)],
        "all_key_concepts": [],
        "all_formulas": [],
        "all_diagrams": [],
        "summary_text": f"Chapter: {name}. (Content extraction failed — please retry.)",
    }
