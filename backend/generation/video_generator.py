"""
Video Generator — two-step pipeline (cerebralvalley approach):

  Step 1  Gemini reads the chapter JSON and writes a structured 3-step
          concept script in the student's language (Kannada, Hindi, etc.).
          Gemini acts as the "user typing the prompt" that cerebralvalley
          requires — AI generates the concept description automatically.

  Step 2  Gemini writes a Manim scene from that script.
          Text is shown with self.add() (full opacity, instant) instead of
          FadeIn() — Cairo on Windows crashes when rendering Indic glyphs at
          partial opacity during FadeIn interpolation, but renders them fine
          at opacity=1. Shapes still use Create() for visual interest.

- Pure Python / Manim Community Edition
- asyncio.Lock serialises renders so concurrent sessions don't collide
"""

import asyncio
import glob
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from google import genai
from google.genai import types

from utils.gcs_uploader import upload_file

_client: genai.Client | None = None
_render_lock = asyncio.Lock()

LANGUAGE_NAMES = {
    "kn-IN": "Kannada",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "en-IN": "English",
}

import platform as _platform
_INDIC_FONT = "Noto Sans" if _platform.system() == "Linux" else "Nirmala UI"

LANGUAGE_FONTS = {
    "kn-IN": _INDIC_FONT,
    "hi-IN": _INDIC_FONT,
    "ta-IN": _INDIC_FONT,
    "te-IN": _INDIC_FONT,
    "mr-IN": _INDIC_FONT,
    "en-IN": "",
}


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


# ── Step 1: Concept script prompt ─────────────────────────────────────────────
# Gemini acts as the "user typing the prompt" that cerebralvalley needs.
# Produces structured JSON so the Manim prompt has exact, length-controlled text.

SCRIPT_PROMPT = """\
You are VidyaChitra, an AI tutor for Indian school students.
Your job: read the chapter summary below and create a 3-step visual
explanation of the MOST IMPORTANT concept from that chapter.

Chapter name : {chapter_name}
Chapter summary (this is the chapter's own language — use the SAME language
for ALL your output):
---
{summary_excerpt}
---

Respond with ONLY a valid JSON object — no other text:

{{
  "concept_english": "<concept name in English — for logging only>",
  "steps": [
    {{
      "heading": "<step heading — MAX 20 chars — write in the SAME language as the summary>",
      "body":    "<1-sentence explanation — MAX 50 chars — same language as summary — NO \\n>",
      "shape":   "<one of: none | arrow | circle | rectangle | coil>"
    }}
  ]
}}

CRITICAL:
- Exactly 3 steps
- heading and body MUST be in the same language as the summary above (NOT English, unless the summary is in English)
- heading ≤ 20 characters, body ≤ 50 characters
- shape must be exactly one of: none, arrow, circle, rectangle, coil
- Respond with ONLY the JSON object\
"""


# ── Step 2: Manim code prompt ─────────────────────────────────────────────────
# KEY: use self.add(text) not FadeIn(text).
# Cairo on Windows crashes rendering Indic glyphs at partial opacity (FadeIn
# interpolates 0→1).  self.add() places text at opacity=1 instantly — no crash.

MANIM_PROMPT = """\
You are a Manim Community Edition expert writing a concept-explanation video.

SCRIPT (JSON):
{script_json}

Language : {language_name}
Font     : {font_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD RULES — any violation = crash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Class name must be exactly: DiagramScene(Scene)
2.  ONLY import: from manim import *
3.  First line of construct(): self.camera.background_color = "#0E1117"
4.  NEVER use Write(), FadeIn(), or DrawBorderThenFill() on Text objects.
    Text must be shown with self.add() — this avoids the partial-opacity
    Cairo crash that occurs with Indic Unicode glyphs on Windows.
    CORRECT: self.add(heading, body)
    WRONG:   self.play(FadeIn(heading))   ← CRASHES
    WRONG:   self.play(Write(heading))    ← CRASHES
5.  Every Text() MUST include font="{font_name}"
6.  NEVER use MathTex or Tex
7.  run_time must be > 0 (minimum 0.1)
8.  Do NOT put \\n inside Text strings — keep each string on one line

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMATION STRUCTURE (one block per step)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FONT = "{font_name}"

For EACH step in steps[]:
  a. heading = Text(step.heading, font_size=40, color=YELLOW, font=FONT).to_edge(UP)
  b. body    = Text(step.body,    font_size=26, color=WHITE,  font=FONT)
               body.next_to(heading, DOWN, buff=0.6)
  c. self.add(heading, body)          ← instant, full opacity, no crash
  d. shape animation (runs AFTER text is visible):
       "arrow"     → arr = Arrow(LEFT*2, RIGHT*2, color=RED, buff=0)
                     self.play(Create(arr, run_time=1.2))
       "circle"    → shp = Circle(radius=1.2, color=BLUE)
                     self.play(Create(shp, run_time=1.2))
       "rectangle" → shp = Rectangle(width=3.5, height=1.8, color=BLUE)
                     self.play(Create(shp, run_time=1.2))
       "coil"      → shp = Rectangle(width=3.2, height=0.35, color=ORANGE)
                     self.play(Create(shp, run_time=1.2))
       "none"      → (no shape)
  e. self.wait(2)
  f. self.remove(heading, body)       ← instant remove for text
     if shape was created: self.play(FadeOut(shp, run_time=0.5))

After all 3 steps:
  if self.mobjects:
      self.play(FadeOut(*self.mobjects, run_time=0.6))
  self.wait(0.5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE (Kannada, font="Nirmala UI")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```python
from manim import *

class DiagramScene(Scene):
    def construct(self):
        self.camera.background_color = "#0E1117"
        FONT = "Nirmala UI"

        # Step 1 — text via self.add(), shape via Create()
        h1 = Text("ಕಾಂತೀಯ ಪ್ರಭಾವ", font_size=40, color=YELLOW, font=FONT).to_edge(UP)
        b1 = Text("ವಿದ್ಯುತ್ ಪ್ರವಾಹ ಕಾಂತ ಕ್ಷೇತ್ರ ಸೃಷ್ಟಿಸುತ್ತದೆ", font_size=26, color=WHITE, font=FONT)
        b1.next_to(h1, DOWN, buff=0.6)
        self.add(h1, b1)
        coil = Rectangle(width=3.2, height=0.35, color=ORANGE)
        self.play(Create(coil, run_time=1.2))
        self.wait(2)
        self.remove(h1, b1)
        self.play(FadeOut(coil, run_time=0.5))

        # Step 2
        h2 = Text("ಬಲಗೈ ನಿಯಮ", font_size=40, color=YELLOW, font=FONT).to_edge(UP)
        b2 = Text("ಹೆಬ್ಬೆರಳು ಪ್ರವಾಹ ದಿಕ್ಕು ತೋರಿಸುತ್ತದೆ", font_size=26, color=WHITE, font=FONT)
        b2.next_to(h2, DOWN, buff=0.6)
        self.add(h2, b2)
        arr = Arrow(LEFT*2, RIGHT*2, color=RED, buff=0)
        self.play(Create(arr, run_time=1.2))
        self.wait(2)
        self.remove(h2, b2)
        self.play(FadeOut(arr, run_time=0.5))

        # Step 3
        h3 = Text("ಉಪಯೋಗಗಳು", font_size=40, color=YELLOW, font=FONT).to_edge(UP)
        b3 = Text("ವಿದ್ಯುತ್ ಮೋಟಾರ್ ಈ ತತ್ವ ಬಳಸುತ್ತದೆ", font_size=26, color=WHITE, font=FONT)
        b3.next_to(h3, DOWN, buff=0.6)
        self.add(h3, b3)
        self.wait(2)
        self.remove(h3, b3)

        if self.mobjects:
            self.play(FadeOut(*self.mobjects, run_time=0.6))
        self.wait(0.5)
```

Now write the ACTUAL scene for the script JSON above in {language_name}.
Use self.add() for all Text. font="{font_name}" on every Text().
Respond with ONLY the Python code in a ```python ... ``` block.\
"""


FIX_PROMPT = """\
This Manim scene failed to render. Fix it.

ERROR:
{error}

ORIGINAL CODE:
```python
{code}
```

Common fixes:
- Replace FadeIn(text_obj) / Write(text_obj) with self.add(text_obj) — FadeIn/Write
  crash with Indic Unicode glyphs on Windows due to partial-opacity Cairo rendering
- Replace MathTex/Tex with Text()
- Ensure every run_time > 0 (minimum 0.1)
- VGroup children must be Mobjects, not strings
- self.camera.background_color must be the first line in construct()
- Only 'from manim import *' is allowed — remove all other imports
- Guard FadeOut(*self.mobjects) with: if self.mobjects: self.play(FadeOut(...))
- Arrow(start, end) needs Manim directions: LEFT, RIGHT, UP, DOWN
- Remove any \\n from inside Text() string arguments
- Every Text() must have font="<fontname>" argument

Return ONLY the corrected Python code in a ```python ... ``` block.\
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*([\s\S]*?)```", text)
    return match.group(1).strip() if match else text.strip()


def _extract_json(text: str):
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    raw = (match.group(1) if match else text).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        if start != -1:
            return json.loads(raw[start:])
        raise


def _run_manim(script_path: str, media_dir: str) -> tuple[bool, str, str]:
    """Run manim and return (success, mp4_path, error_msg)."""
    if not shutil.which("ffmpeg"):
        return False, "", (
            "FFmpeg not found in PATH. "
            "Windows: https://www.gyan.dev/ffmpeg/builds/ — add bin/ to PATH. "
            "macOS: brew install ffmpeg  |  Ubuntu: apt install ffmpeg"
        )
    try:
        result = subprocess.run(
            ["manim", "-ql", script_path, "DiagramScene",
             "--media_dir", media_dir, "--disable_caching"],
            capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            return False, "", result.stderr + result.stdout

        mp4_files = glob.glob(f"{media_dir}/**/*.mp4", recursive=True)
        if not mp4_files:
            return False, "", "Manim completed but no MP4 found."
        return True, mp4_files[0], ""

    except subprocess.TimeoutExpired:
        return False, "", "Manim render timed out after 180s."
    except FileNotFoundError:
        return False, "", "manim not found. Run: pip install manim"
    except Exception as e:
        return False, "", str(e)


# ── Main entry point ──────────────────────────────────────────────────────────

async def generate_diagram_video(chapter_json: dict, language_code: str, session_id: str) -> str:
    """
    Two-step pipeline (cerebralvalley approach):
      1. Gemini reads chapter_json → picks concept → writes 3-step script in
         the student's language (Kannada/Hindi/etc.) — Gemini acts as the
         "user typing the concept prompt" that cerebralvalley needs manually.
      2. Gemini writes a Manim scene from that script. Text shown via
         self.add() (opacity=1 instantly) to avoid FadeIn/Cairo Indic crash.

    Returns public URL of the rendered MP4.
    """
    client = _get_client()
    language_name = LANGUAGE_NAMES.get(language_code, "English")
    font_name = LANGUAGE_FONTS.get(language_code, "Nirmala UI")

    chapter_name    = chapter_json.get("chapter_name", "Chapter")
    # Use summary_text as the primary source — it's already in the student's
    # language (Kannada/Hindi/etc.) so Gemini will write the script in that
    # language too. key_concepts are in English and confuse the model.
    summary_excerpt = chapter_json.get("summary_text", "")[:800]

    # ── Step 1: Gemini generates the concept script ───────────────────────────
    print(f"[video_generator] Step 1 — concept script ({language_name})...")
    script_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_text(text=SCRIPT_PROMPT.format(
            chapter_name=chapter_name,
            summary_excerpt=summary_excerpt,
        ))]
    )
    script = _extract_json(script_resp.text)
    concept = script.get("concept_english", chapter_name)
    print(f"[video_generator] Concept: {concept}")

    # ── Step 2: Gemini writes Manim scene from the script ─────────────────────
    print(f"[video_generator] Step 2 — Manim scene generation...")
    manim_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_text(text=MANIM_PROMPT.format(
            script_json=json.dumps(script, ensure_ascii=False, indent=2),
            language_name=language_name,
            font_name=font_name or "Manim default",
        ))]
    )
    scene_code = _extract_code(manim_resp.text)

    # ── Render ────────────────────────────────────────────────────────────────
    _tmp = tempfile.gettempdir()
    script_path = os.path.join(_tmp, f"vc_scene_{session_id}.py")
    media_dir   = os.path.join(_tmp, f"manim_{session_id}")
    Path(media_dir).mkdir(parents=True, exist_ok=True)
    Path(script_path).write_text(scene_code, encoding="utf-8")

    async with _render_lock:
        loop = asyncio.get_running_loop()
        success, mp4_path, error_msg = await loop.run_in_executor(
            None, _run_manim, script_path, media_dir
        )

        if not success:
            print(f"[video_generator] First render failed:\n{error_msg[:600]}")
            print("[video_generator] Asking Gemini to fix...")
            fix_resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[types.Part.from_text(
                    text=FIX_PROMPT.format(error=error_msg[:2000], code=scene_code[:6000])
                )]
            )
            scene_code = _extract_code(fix_resp.text)
            Path(script_path).write_text(scene_code, encoding="utf-8")

            success, mp4_path, error_msg = await loop.run_in_executor(
                None, _run_manim, script_path, media_dir
            )
            if not success:
                raise RuntimeError(f"Manim render failed after retry: {error_msg[:400]}")

    # ── Upload & cleanup ──────────────────────────────────────────────────────
    gcs_path = f"video/{session_id}.mp4"
    print(f"[video_generator] Uploading video...")
    url = upload_file(mp4_path, gcs_path, "video/mp4")

    try:
        os.unlink(script_path)
        shutil.rmtree(media_dir, ignore_errors=True)
    except Exception:
        pass

    print(f"[video_generator] Video ready: {url}")
    return url
