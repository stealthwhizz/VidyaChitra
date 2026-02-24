"""
Board exam patterns for Indian school boards.
Describes section structure, mark allocation, and special requirements.
"""

BOARD_PATTERNS = {
    "Karnataka SSLC": {
        "name": "Karnataka SSLC",
        "total_marks": 80,
        "diagram_required": True,
        "sections": [
            {
                "name": "Section A",
                "type": "MCQ",
                "marks_per_question": 1,
                "num_questions": 10,
                "description": "Multiple choice questions with one correct answer"
            },
            {
                "name": "Section B",
                "type": "Fill in the blank / Very Short Answer",
                "marks_per_question": 1,
                "num_questions": 10,
                "description": "Fill in the blanks or one-word answers"
            },
            {
                "name": "Section C",
                "type": "Short Answer",
                "marks_per_question": 2,
                "num_questions": 8,
                "description": "Short answers in 2-3 sentences (approx 30-40 words)"
            },
            {
                "name": "Section D",
                "type": "Long Answer with Diagram",
                "marks_per_question": 4,
                "num_questions": 4,
                "description": "Descriptive answers with labelled diagrams for science chapters. "
                               "Diagrams carry 1-2 marks of the total. Answer in 80-100 words."
            }
        ],
        "notes": (
            "Diagrams must be neatly drawn and labelled in Section D for science subjects. "
            "MCQs cover factual recall. Short answers test understanding. "
            "Internal choice is given in Section D questions."
        )
    },

    "CBSE Class 10": {
        "name": "CBSE Class 10",
        "total_marks": 80,
        "diagram_required": True,
        "sections": [
            {
                "name": "Section A",
                "type": "MCQ and Assertion-Reason",
                "marks_per_question": 1,
                "num_questions": 20,
                "description": (
                    "20 questions of 1 mark each. Q1-Q16 are MCQs. "
                    "Q17-Q20 are Assertion-Reason questions where student selects "
                    "the correct relationship between assertion and reason."
                )
            },
            {
                "name": "Section B",
                "type": "Very Short Answer",
                "marks_per_question": 2,
                "num_questions": 6,
                "description": "6 questions of 2 marks each. Answer in 2-3 sentences."
            },
            {
                "name": "Section C",
                "type": "Short Answer with Diagram",
                "marks_per_question": 3,
                "num_questions": 7,
                "description": (
                    "7 questions of 3 marks each. Diagrams required for science questions. "
                    "Answer in 40-60 words. Internal choice provided."
                )
            },
            {
                "name": "Section D",
                "type": "Case Study / Long Answer",
                "marks_per_question": 5,
                "num_questions": 3,
                "description": (
                    "3 questions of 5 marks each. Includes case study questions introduced "
                    "in recent years. Read a passage and answer related sub-questions. "
                    "Detailed diagrams required for science. Answer in 80-100 words."
                )
            }
        ],
        "notes": (
            "Assertion-Reason questions require understanding of scientific reasoning. "
            "Case study questions (introduced in 2021-22) test application of concepts. "
            "All diagrams must be labelled. Internal choices given in Sections C and D."
        )
    },

    "Maharashtra SSC": {
        "name": "Maharashtra SSC",
        "total_marks": 80,
        "diagram_required": True,
        "sections": [
            {
                "name": "Q1",
                "type": "Objective",
                "marks_per_question": 1,
                "num_questions": 20,
                "description": (
                    "Multiple sub-types: (A) MCQ with 4 options, (B) True/False with justification, "
                    "(C) Match the column (Column A with Column B), (D) Identify the odd one out."
                )
            },
            {
                "name": "Q2-Q4",
                "type": "Short Answer",
                "marks_per_question": 2,
                "num_questions": 12,
                "description": "Short answers of 2 marks each. Answer in 3-4 sentences."
            },
            {
                "name": "Q5-Q6",
                "type": "Long Answer",
                "marks_per_question": 3,
                "num_questions": 6,
                "description": "Long answers of 3 marks each with diagrams where applicable."
            },
            {
                "name": "Q7",
                "type": "Activity / Diagram Based",
                "marks_per_question": 5,
                "num_questions": 2,
                "description": (
                    "Activity-based or diagram-based questions. Students may be asked to draw, "
                    "label or explain experimental setups."
                )
            }
        ],
        "notes": (
            "Q1 has varied formats so students must be prepared for MCQ, T/F, and matching. "
            "True/False requires justification — just stating True or False is not enough. "
            "Diagrams are awarded specific marks in Q5-Q7."
        )
    },

    "Tamil Nadu State Board": {
        "name": "Tamil Nadu State Board",
        "total_marks": 100,
        "diagram_required": True,
        "sections": [
            {
                "name": "Part I",
                "type": "MCQ",
                "marks_per_question": 1,
                "num_questions": 15,
                "description": "15 MCQs of 1 mark each. One correct answer from 4 options."
            },
            {
                "name": "Part II",
                "type": "Very Short Answer",
                "marks_per_question": 2,
                "num_questions": 10,
                "description": "10 questions of 2 marks each. Answer in 1-2 sentences."
            },
            {
                "name": "Part III",
                "type": "Short Answer",
                "marks_per_question": 5,
                "num_questions": 7,
                "description": "7 questions of 5 marks each with internal choice. Answer in a paragraph."
            },
            {
                "name": "Part IV",
                "type": "Long Answer with Detailed Diagram",
                "marks_per_question": 8,
                "num_questions": 3,
                "description": (
                    "3 questions of 8 marks each with internal choice. "
                    "Requires detailed, fully labelled diagrams for science. "
                    "Diagrams carry 3-4 marks of the total. Answer in 150-200 words."
                )
            }
        ],
        "notes": (
            "Part IV carries the highest marks and detailed diagrams are mandatory. "
            "Internal choice given in Part III and IV. "
            "Students must write the answer in the correct sequence as expected by the board."
        )
    }
}


def get_board_pattern(board_name: str) -> dict:
    """Return the board pattern dict for a given board name."""
    return BOARD_PATTERNS.get(board_name, BOARD_PATTERNS["CBSE Class 10"])


def get_board_names() -> list[str]:
    """Return list of supported board names."""
    return list(BOARD_PATTERNS.keys())


def format_board_pattern_for_prompt(board_name: str) -> str:
    """Format board pattern as a readable string for inclusion in AI prompts."""
    pattern = get_board_pattern(board_name)
    lines = [
        f"Board: {pattern['name']}",
        f"Total Marks: {pattern['total_marks']}",
        f"Diagrams Required: {pattern['diagram_required']}",
        "",
        "Sections:"
    ]
    for section in pattern["sections"]:
        lines.append(
            f"  - {section['name']}: {section['type']} | "
            f"{section['marks_per_question']} mark(s) each | "
            f"{section['num_questions']} questions"
        )
        lines.append(f"    {section['description']}")
    lines.append("")
    lines.append(f"Notes: {pattern['notes']}")
    return "\n".join(lines)
