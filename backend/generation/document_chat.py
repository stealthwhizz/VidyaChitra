"""
Document Chat — answers student questions grounded strictly in chapter content.

Uses Gemini 2.5 Flash with the full chapter JSON as context.
Maintains conversational history across turns.
Responds in the student's chosen language.
"""

import os

from google import genai
from google.genai import types

LANGUAGE_NAMES: dict[str, str] = {
    "kn-IN": "Kannada",
    "hi-IN": "Hindi",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "mr-IN": "Marathi",
    "en-IN": "English",
}

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


SYSTEM_PROMPT_TEMPLATE = """You are VidyaChitra, an AI study companion for Indian school students.
You are helping a Class {class_level} student with the chapter: "{chapter_name}" from {board}.

STRICT RULES:
1. Answer ONLY from the chapter content provided below. Do NOT use any outside knowledge.
2. Respond in {language_name}. If the student writes in English, still respond in {language_name}.
3. When answering, cite which concept, formula, or diagram you are referring to.
4. If the answer is not present in the chapter content, respond with:
   "यह विषय इस अध्याय में शामिल नहीं है।" (or the equivalent in {language_name}:
   "This topic is not covered in this chapter.")
5. Keep answers student-friendly, clear, and encouraging.
6. For numerical problems, show step-by-step working.
7. If a diagram is relevant, describe it clearly.

CHAPTER CONTENT:
Chapter: {chapter_name}
Board: {board}
Class: {class_level}

Key Concepts: {key_concepts}

Formulas: {formulas}

Diagrams in this chapter:
{diagram_descriptions}

Full Chapter Text:
{chapter_text}"""


def _build_system_prompt(chapter_json: dict, language_code: str) -> str:
    """Build the system prompt with chapter content embedded."""
    language_name = LANGUAGE_NAMES.get(language_code, "English")

    # Format diagram descriptions
    diagrams = chapter_json.get("diagrams", [])
    if diagrams:
        diagram_parts = []
        for i, d in enumerate(diagrams[:10], 1):
            diagram_parts.append(
                f"{i}. {d.get('type', 'Diagram')}: {d.get('concept', '')} — "
                f"{d.get('description', '')} "
                f"(Labels: {', '.join(d.get('labels', []))})"
            )
        diagram_descriptions = "\n".join(diagram_parts)
    else:
        diagram_descriptions = "No diagrams in this chapter."

    # Truncate chapter text
    chapter_text = chapter_json.get("full_text", "")[:10000]

    return SYSTEM_PROMPT_TEMPLATE.format(
        class_level=chapter_json.get("class_level", "10"),
        chapter_name=chapter_json.get("chapter_name", "Unknown Chapter"),
        board=chapter_json.get("board", "CBSE"),
        language_name=language_name,
        key_concepts=", ".join(chapter_json.get("key_concepts", [])[:25]),
        formulas="\n".join(f"- {f}" for f in chapter_json.get("formulas", [])[:15]),
        diagram_descriptions=diagram_descriptions,
        chapter_text=chapter_text,
    )


def chat(
    question: str,
    chapter_json: dict,
    language_code: str,
    history: list[dict[str, str]]
) -> str:
    """
    Answer a student's question grounded in the chapter content.

    Args:
        question: The student's question string.
        chapter_json: Consolidated chapter JSON from pdf_processor.
        language_code: BCP-47 language code for the response language.
        history: List of previous turns: [{"role": "user"|"model", "content": "..."}]

    Returns:
        AI response string.
    """
    client = _get_client()
    system_prompt = _build_system_prompt(chapter_json, language_code)

    # Build contents list: system prompt as first user turn, then history, then current question
    contents = []

    # Gemini chat pattern: alternate user/model
    # Prepend system context as a user message that the model has already "answered"
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=system_prompt + "\n\n[Ready to answer questions about this chapter]")]
    ))
    contents.append(types.Content(
        role="model",
        parts=[types.Part.from_text(text="Understood! I will only answer from this chapter's content. Ask me anything about this chapter!")]
    ))

    # Add conversation history
    for turn in history[-10:]:  # Keep last 10 turns to manage context
        role = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "model") and content:
            contents.append(types.Content(
                role=role,
                parts=[types.Part.from_text(text=content)]
            ))

    # Add current question
    contents.append(types.Content(
        role="user",
        parts=[types.Part.from_text(text=question)]
    ))

    print(f"[document_chat] Answering: {question[:80]}...")
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=contents,
    )

    return response.text.strip()


async def chat_stream(
    question: str,
    chapter_json: dict,
    language_code: str,
    history: list[dict[str, str]]
):
    """
    Streaming version of chat — yields text chunks as they arrive.
    Suitable for use with FastAPI StreamingResponse.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    # Run synchronous Gemini call in thread pool
    result = await loop.run_in_executor(
        None, chat, question, chapter_json, language_code, history
    )

    # Simulate streaming by yielding words for a smooth UX
    words = result.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        await asyncio.sleep(0.02)  # Small delay for smooth stream effect
