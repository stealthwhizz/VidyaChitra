"""
Question Forger — generates board-pattern exam questions using Gemini 2.5 Flash.

Produces MCQs, short answers, and a Higher Order Thinking question strictly
following the target board's pattern and marking scheme.
"""

import json
import os
import re
from typing import Any

from google import genai
from google.genai import types

from utils.board_patterns import format_board_pattern_for_prompt

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    return _client


def _extract_json(text: str) -> Any:
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


QUESTION_PROMPT_TEMPLATE = """You are an expert question paper setter for Indian school exams.

{board_pattern}

Chapter Content:
Chapter Name: {chapter_name}
Key Concepts: {key_concepts}
Formulas: {formulas}
Diagrams in this chapter: {diagram_summary}

Full chapter text (excerpt):
{chapter_text}

Generate exam questions STRICTLY following the board pattern above.
Respond with ONLY a valid JSON object matching this exact schema:

{{
  "mcqs": [
    {{
      "question": "<question text>",
      "options": ["A. <option>", "B. <option>", "C. <option>", "D. <option>"],
      "correct_index": 0,
      "explanation": "<why this answer is correct, 1-2 sentences>",
      "is_diagram_based": false,
      "prev_year_hint": false
    }}
  ],
  "short_answers": [
    {{
      "question": "<question text>",
      "model_answer": "<complete model answer>",
      "marks": 2,
      "word_count_target": 40,
      "is_diagram_based": false
    }}
  ],
  "hot_question": {{
    "question": "<Higher Order Thinking question that requires application or analysis>",
    "model_answer": "<detailed model answer>",
    "marks": 5,
    "hint": "<hint for students struggling with this question>"
  }},
  "exam_tip": "<1-2 sentence exam tip specific to this chapter and board pattern>"
}}

Requirements:
- Generate exactly 10 MCQs with 4 options each, correct_index is 0-based
- Generate exactly 3 short answer questions
- If the chapter has diagrams, at least 2 MCQs and 1 short answer must be diagram-based
- Mark prev_year_hint as true if the question covers a concept frequently tested in past papers
- word_count_target for short answers: {word_count_target}
- All questions must be answerable from the chapter content provided
- The HOT question must require analysis or application beyond direct recall
- Respond with ONLY the JSON, no other text"""


def generate_questions(chapter_json: dict, board: str, language: str) -> dict:
    """
    Generate board-pattern exam questions from the chapter JSON.

    Args:
        chapter_json: The consolidated chapter JSON from pdf_processor.
        board: Board name (e.g. "Karnataka SSLC").
        language: Target language code (used for labelling, questions are in English).

    Returns:
        Dict with mcqs, short_answers, hot_question, exam_tip.
    """
    client = _get_client()

    board_pattern_str = format_board_pattern_for_prompt(board)

    # Determine word count target for short answers based on board
    word_count_map = {
        "Karnataka SSLC": 40,
        "CBSE Class 10": 50,
        "Maharashtra SSC": 40,
        "Tamil Nadu State Board": 60,
    }
    word_count_target = word_count_map.get(board, 50)

    # Summarise diagrams for the prompt
    diagrams = chapter_json.get("diagrams", [])
    diagram_summary = (
        ", ".join(f"{d.get('type', 'diagram')}: {d.get('concept', '')}" for d in diagrams[:5])
        if diagrams else "No diagrams in this chapter"
    )

    # Truncate chapter text for prompt
    chapter_text = chapter_json.get("full_text", "")[:8000]

    prompt = QUESTION_PROMPT_TEMPLATE.format(
        board_pattern=board_pattern_str,
        chapter_name=chapter_json.get("chapter_name", "Unknown Chapter"),
        key_concepts=", ".join(chapter_json.get("key_concepts", [])[:20]),
        formulas=", ".join(chapter_json.get("formulas", [])[:10]),
        diagram_summary=diagram_summary,
        chapter_text=chapter_text,
        word_count_target=word_count_target,
    )

    print(f"[question_forger] Generating questions for {board}...")
    response = _get_client().models.generate_content(
        model="gemini-2.5-flash",
        contents=[types.Part.from_text(text=prompt)]
    )

    result = _extract_json(response.text)

    # Ensure all required keys exist
    result.setdefault("mcqs", [])
    result.setdefault("short_answers", [])
    result.setdefault("hot_question", {"question": "", "model_answer": "", "marks": 5, "hint": ""})
    result.setdefault("exam_tip", "")

    # Add mark info to MCQs if missing
    for mcq in result["mcqs"]:
        mcq.setdefault("marks", 1)
        mcq.setdefault("is_diagram_based", False)
        mcq.setdefault("prev_year_hint", False)

    print(f"[question_forger] Generated {len(result['mcqs'])} MCQs, "
          f"{len(result['short_answers'])} short answers")
    return result
