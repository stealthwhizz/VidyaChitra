"""
Vernacular Narrator — generates Indian-language audio narration of the chapter.

1. Uses Gemini 2.5 Flash to write a teacher-style spoken summary in the target language.
2. Synthesises audio using Sarvam AI Bulbul v1 (primary — best for Indian languages).
3. Falls back to Gemini TTS (gemini-2.5-flash-preview-tts) if Sarvam is unavailable.
4. Uploads the resulting WAV file to GCS (or local static dir) and returns the URL.
"""

import base64
import io
import os
import tempfile
import wave
from typing import Optional

import httpx
from google import genai
from google.genai import types

from utils.gcs_uploader import upload_file

SARVAM_TTS_URL = "https://api.sarvam.ai/text-to-speech"

_gemini_client: genai.Client | None = None

LANGUAGE_NAMES = {
    "kn-IN": "Kannada",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "en-IN": "English",
}

# Sarvam Bulbul v1 speaker mapping
SARVAM_SPEAKERS = {
    "kn-IN": "arvind",
    "hi-IN": "meera",
    "ta-IN": "arjun",
    "te-IN": "pavithra",
    "mr-IN": "amol",
    "en-IN": "meera",
}

# Gemini TTS voices — used as fallback
GEMINI_VOICES = {
    "kn-IN": "Kore",
    "hi-IN": "Kore",
    "ta-IN": "Kore",
    "te-IN": "Kore",
    "mr-IN": "Kore",
    "en-IN": "Puck",
}

NARRATION_PROMPT_TEMPLATE = """You are an enthusiastic, knowledgeable Indian school teacher.
Write a spoken narration of this chapter in {language_name} for a Class {class_level} student.

Chapter: {chapter_name}
Summary: {summary_text}
Key Concepts: {key_concepts}
Formulas: {formulas}

Requirements:
- Write ONLY in {language_name} (not English, not a mix)
- Write as if you are speaking aloud to a student — conversational, friendly, encouraging
- Do NOT use bullet points or numbered lists — write in flowing paragraphs as natural speech
- Include simple analogies relevant to everyday Indian life where helpful
- Mention each formula with a brief verbal explanation
- Keep it 200-280 words (concise for TTS synthesis)
- End with one motivational sentence for the student

Respond with ONLY the narration text in {language_name}, nothing else."""


def _get_gemini_client() -> genai.Client:
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _gemini_client


def _generate_narration_text(chapter_json: dict, language_code: str) -> str:
    """Use Gemini to generate a teacher-style spoken narration in the target language."""
    client = _get_gemini_client()
    language_name = LANGUAGE_NAMES.get(language_code, "English")

    prompt = NARRATION_PROMPT_TEMPLATE.format(
        language_name=language_name,
        class_level=chapter_json.get("class_level", "10"),
        chapter_name=chapter_json.get("chapter_name", "this chapter"),
        summary_text=chapter_json.get("summary_text", "")[:3000],
        key_concepts=", ".join(chapter_json.get("key_concepts", [])[:15]),
        formulas=", ".join(chapter_json.get("formulas", [])[:8]),
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_text(text=prompt)]
    )
    return response.text.strip()


def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2) -> bytes:
    """Wrap raw 16-bit PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)  # 2 bytes = 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def _call_sarvam_tts(text: str, language_code: str) -> Optional[bytes]:
    """
    Call Sarvam AI Bulbul v1 TTS via its REST API (httpx).
    Returns raw audio bytes (WAV-encoded by Sarvam), or None on failure.
    """
    api_key = os.environ.get("SARVAM_API_KEY", "")
    if not api_key:
        print("[vernacular_narrator] SARVAM_API_KEY not set, skipping Sarvam TTS")
        return None

    speaker = SARVAM_SPEAKERS.get(language_code, "meera")
    print(f"[vernacular_narrator] Calling Sarvam TTS (speaker={speaker}, lang={language_code})...")

    # Sarvam TTS accepts up to ~500 chars per request — split into chunks
    chunks = _split_text(text, max_chars=450)
    all_audio = b""

    headers = {
        "api-subscription-key": api_key,
        "Content-Type": "application/json",
    }

    for i, chunk in enumerate(chunks):
        payload = {
            "inputs": [chunk],
            "target_language_code": language_code,
            "speaker": speaker,
            "model": "bulbul:v1",
            "enable_preprocessing": True,
            "pace": 1.2,
            "loudness": 1.5,
        }
        try:
            resp = httpx.post(SARVAM_TTS_URL, json=payload, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"[vernacular_narrator] Sarvam chunk {i+1} HTTP {resp.status_code}: {resp.text[:300]}")
                return None
            data = resp.json()
            audios = data.get("audios", [])
            if audios:
                all_audio += base64.b64decode(audios[0])
            else:
                print(f"[vernacular_narrator] Sarvam chunk {i+1}: empty audios")
                return None
        except Exception as e:
            print(f"[vernacular_narrator] Sarvam TTS chunk {i+1} failed: {e}")
            return None

    return all_audio if all_audio else None


def _call_gemini_tts(text: str, language_code: str) -> bytes:
    """
    Fallback: Call Gemini TTS (gemini-2.5-flash-preview-tts) and return WAV bytes.
    Gemini returns raw 16-bit linear PCM at 24 kHz mono; we wrap it in WAV.
    """
    client = _get_gemini_client()
    voice_name = GEMINI_VOICES.get(language_code, "Kore")
    print(f"[vernacular_narrator] Calling Gemini TTS fallback (voice={voice_name})...")

    response = client.models.generate_content(
        model="gemini-2.5-flash-preview-tts",
        contents=text,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        ),
    )

    audio_part = response.candidates[0].content.parts[0]
    pcm_data: bytes = audio_part.inline_data.data
    print(f"[vernacular_narrator] Gemini TTS returned {len(pcm_data)} bytes PCM")
    return _pcm_to_wav(pcm_data)


def _split_text(text: str, max_chars: int = 450) -> list[str]:
    """Split text into chunks at sentence boundaries."""
    sentences = text.replace("।", ".").split(".")
    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = (current + ". " + sentence).strip() if current else sentence.strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = sentence.strip()
    if current:
        chunks.append(current)
    return chunks or [text[:max_chars]]


def generate_narration(chapter_json: dict, language_code: str) -> str:
    """
    Generate spoken narration audio for the chapter in the target language.

    Args:
        chapter_json: Consolidated chapter JSON from pdf_processor.
        language_code: BCP-47 language code (e.g. "kn-IN", "hi-IN").

    Returns:
        Public URL of the uploaded audio file.
    """
    session_id = chapter_json.get("session_id", "unknown")
    print(f"[vernacular_narrator] Generating {language_code} narration for session {session_id}...")

    # Step 1: Generate narration script via Gemini
    narration_text = _generate_narration_text(chapter_json, language_code)
    print(f"[vernacular_narrator] Narration script ({len(narration_text)} chars) ready")

    # Step 2: Synthesise audio — Sarvam primary, Gemini TTS fallback
    audio_bytes: Optional[bytes] = _call_sarvam_tts(narration_text, language_code)

    if audio_bytes is None:
        print("[vernacular_narrator] Falling back to Gemini TTS...")
        audio_bytes = _call_gemini_tts(narration_text, language_code)

    print(f"[vernacular_narrator] Audio ready ({len(audio_bytes)} bytes)")

    # Step 3: Save to temp file and upload to GCS / local static
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    gcs_path = f"audio/{session_id}_{language_code}.wav"
    url = upload_file(tmp_path, gcs_path, "audio/wav")

    import os as _os
    _os.unlink(tmp_path)

    print(f"[vernacular_narrator] Audio available at: {url}")
    return url
