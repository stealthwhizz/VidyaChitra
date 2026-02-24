"""
Video Generator — two-step pipeline inspired by cerebralvalley:

  Step 1  Gemini reads the chapter JSON and writes a structured 3-step
          concept-explanation SCRIPT (JSON).  This controls exactly what
          text will appear on screen, keeping lines short and safe.

  Step 2  Gemini writes a Manim scene from that script.  The scene uses
          ONLY FadeIn() for text (Write() crashes on Indic Unicode glyphs)
          and simple geometric shapes — no complex diagram recreation.

- Pure Python / Manim Community Edition (no Node.js)
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
    "en-IN": "",          # English — Manim default font is fine
}


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


# ── Step 1: Concept script prompt ────────────────────────────────────────────

SCRIPT_PROMPT = """\
You are VidyaChitra, an AI tutor for Indian school students.

Read this chapter and pick the SINGLE most important concept that can be
explained in 3 clear visual steps. Write a structured animation script for it.

Chapter   : {chapter_name}
Concepts  : {key_concepts}
Language  : {language_name}
Summary   : {summary_excerpt}

Respond with ONLY a valid JSON object — no other text:

{{
  "concept_english": "<concept name in English — used for logging only>",
  "concept_title":   "<concept title in {language_name} — max 25 chars>",
  "steps": [
    {{
      "heading":  "<step heading in {language_name} — MAX 22 chars>",
      "body":     "<1-sentence explanation in {language_name} — MAX 60 chars>",
      "shape":    "<one of: none | arrow | circle | rectangle | coil>"
    }}
  ]
}}

Rules:
- Exactly 3 steps
- ALL heading and body text MUST be in {language_name}
- heading ≤ 22 characters (hard limit — it goes on screen)
- body    ≤ 60 characters (hard limit — split with \\n if needed)
- shape must be exactly one of: none, arrow, circle, rectangle, coil
- Respond with ONLY the JSON object\
"""


# ── Step 2: Manim code prompt ─────────────────────────────────────────────────

MANIM_PROMPT = """\
You are a Manim Community Edition expert.
Write a complete scene that animates this concept explanation.

SCRIPT (JSON):
{script_json}

Language : {language_name}
Font     : {font_name}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HARD RULES — any violation = crash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  Class name: DiagramScene(Scene)
2.  ONLY import: from manim import *
3.  First line of construct():  self.camera.background_color = "#0E1117"
4.  NEVER use Write() or DrawBorderThenFill() on Text — they CRASH on
    Unicode/Indic glyphs.  Use FadeIn() for EVERY Text object.
    CORRECT: self.play(FadeIn(text, run_time=1))
    WRONG:   self.play(Write(text, run_time=1))
5.  Every Text() MUST include  font="{font_name}"
6.  NEVER use MathTex or Tex
7.  run_time must be > 0  (minimum 0.1)
8.  Text max 22 chars per line — use "\\n" to split longer strings

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ANIMATION STRUCTURE (one block per step)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For EACH step in steps[]:
  a. Create heading  Text at top:  font_size=38, color=YELLOW, .to_edge(UP)
  b. Create body     Text below:   font_size=26, color=WHITE,
                                   .next_to(heading, DOWN, buff=0.6)
  c. If shape == "arrow"     : arr = Arrow(LEFT*2, RIGHT*2, color=RED, buff=0)
     If shape == "circle"    : shp = Circle(radius=1.2, color=BLUE)
     If shape == "rectangle" : shp = Rectangle(width=3.5, height=1.8, color=BLUE)
     If shape == "coil"      : shp = Rectangle(width=3, height=0.35, color=ORANGE)
     If shape == "none"      : (no shape)
  d. self.play(FadeIn(heading, run_time=0.8), FadeIn(body, run_time=0.8))
     If shape != none: self.play(Create(shp, run_time=1.2))
  e. self.wait(2)
  f. Fade out ALL objects from this step before the next step

After all steps:
  self.play(FadeOut(*self.mobjects, run_time=0.8))
  self.wait(1)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EXAMPLE (3 steps, Kannada, font="Nirmala UI")
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```python
from manim import *

class DiagramScene(Scene):
    def construct(self):
        self.camera.background_color = "#0E1117"
        FONT = "Nirmala UI"

        # Step 1
        h1 = Text("ಕಾಂತೀಯ ಪ್ರಭಾವ", font_size=38, color=YELLOW, font=FONT).to_edge(UP)
        b1 = Text("ವಿದ್ಯುತ್ ಪ್ರವಾಹ ಕಾಂತೀಯ\\nಕ್ಷೇತ್ರ ಸೃಷ್ಟಿಸುತ್ತದೆ",
                  font_size=26, color=WHITE, font=FONT).next_to(h1, DOWN, buff=0.6)
        coil = Rectangle(width=3, height=0.35, color=ORANGE)
        self.play(FadeIn(h1, run_time=0.8), FadeIn(b1, run_time=0.8))
        self.play(Create(coil, run_time=1.2))
        self.wait(2)
        self.play(FadeOut(h1, b1, coil, run_time=0.6))

        # Step 2
        h2 = Text("ಬಲಗೈ ನಿಯಮ", font_size=38, color=YELLOW, font=FONT).to_edge(UP)
        b2 = Text("ಹೆಬ್ಬೆರಳು ಪ್ರವಾಹ ದಿಕ್ಕು\\nತೋರಿಸುತ್ತದೆ",
                  font_size=26, color=WHITE, font=FONT).next_to(h2, DOWN, buff=0.6)
        arr = Arrow(LEFT*2, RIGHT*2, color=RED, buff=0)
        self.play(FadeIn(h2, run_time=0.8), FadeIn(b2, run_time=0.8))
        self.play(Create(arr, run_time=1.2))
        self.wait(2)
        self.play(FadeOut(h2, b2, arr, run_time=0.6))

        # Step 3
        h3 = Text("ಉಪಯೋಗಗಳು", font_size=38, color=YELLOW, font=FONT).to_edge(UP)
        b3 = Text("ವಿದ್ಯುತ್ ಮೋಟಾರ್ ಮತ್ತು\\nಜನರೇಟರ್ ಈ ತತ್ವ ಬಳಸುತ್ತವೆ",
                  font_size=26, color=WHITE, font=FONT).next_to(h3, DOWN, buff=0.6)
        self.play(FadeIn(h3, run_time=0.8), FadeIn(b3, run_time=0.8))
        self.wait(2)
        self.play(FadeOut(h3, b3, run_time=0.6))

        self.play(FadeOut(*self.mobjects, run_time=0.8))
        self.wait(1)
```

Now write the ACTUAL scene for the script JSON above in {language_name}.
Remember: FadeIn() for ALL Text objects.  font="{font_name}" on every Text().
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
- Replace ALL Write(obj) / DrawBorderThenFill(obj) on Text with FadeIn(obj, run_time=1)
- Replace MathTex/Tex with Text()
- Ensure every run_time > 0 (minimum 0.1)
- VGroup children must be Mobjects, not strings
- self.camera.background_color must be set before any self.play()
- Only 'from manim import *' is allowed — remove all other imports
- FadeOut(*self.mobjects) fails if mobjects is empty — guard with 'if self.mobjects'
- Arrow(start, end) needs Manim directions (LEFT, RIGHT, UP, DOWN) or np.array([x,y,0])
- Shorten any Text string that exceeds 22 chars per line

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
            "Install: Windows → https://www.gyan.dev/ffmpeg/builds/ "
            "| macOS → brew install ffmpeg | Ubuntu → apt install ffmpeg"
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
    Two-step pipeline:
      1. Gemini reads chapter_json → produces a 3-step concept script (JSON)
      2. Gemini writes Manim code from that script → rendered to MP4

    Args:
        chapter_json: Consolidated chapter JSON from pdf_processor.
        language_code: BCP-47 code (e.g. "kn-IN").
        session_id: Unique session ID for temp file naming.

    Returns:
        Public URL of the rendered MP4.
    """
    client = _get_client()
    language_name = LANGUAGE_NAMES.get(language_code, "English")
    font_name = LANGUAGE_FONTS.get(language_code, "Nirmala UI")

    chapter_name   = chapter_json.get("chapter_name", "Chapter")
    key_concepts   = ", ".join(chapter_json.get("key_concepts", [])[:12])
    summary_excerpt = chapter_json.get("summary_text", "")[:600]

    # ── Step 1: Generate concept script ──────────────────────────────────────
    print(f"[video_generator] Step 1 — generating concept script ({language_name})...")
    script_resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_text(text=SCRIPT_PROMPT.format(
            chapter_name=chapter_name,
            key_concepts=key_concepts,
            language_name=language_name,
            summary_excerpt=summary_excerpt,
        ))]
    )
    script = _extract_json(script_resp.text)
    concept = script.get("concept_english", chapter_name)
    print(f"[video_generator] Concept selected: {concept}")

    # ── Step 2: Generate Manim code from script ───────────────────────────────
    print(f"[video_generator] Step 2 — generating Manim scene...")
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
            print(f"[video_generator] First render failed:\n{error_msg[:500]}")
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
