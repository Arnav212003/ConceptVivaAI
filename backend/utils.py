"""Small stateless helpers shared across services and routes."""
import json
import re


def extract_json(text):
    try:
        return json.loads(text)
    except Exception:
        match = re.search(r"\{[\s\S]*\}", text)

        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return None

        return None


def get_topic_key(topic):
    return topic.lower().strip()


def public_dsa_question(question):
    if not question:
        return None
    return {key: value for key, value in question.items() if key != "runner"}


def extract_question_id_from_problem_text(problem_text):
    if not problem_text:
        return None

    match = re.search(r"Question ID:\s*(\S+)", problem_text)

    if match:
        return match.group(1).strip()

    match = re.search(r"Problem ID:\s*(\S+)", problem_text)

    if match:
        return match.group(1).strip()

    return None


def get_difficulty_distribution(questions):
    easy = 0
    medium = 0
    hard = 0

    for question in questions:
        difficulty = question.get("difficulty", "").lower().strip()

        if difficulty == "easy":
            easy += 1
        elif difficulty == "medium":
            medium += 1
        elif difficulty == "hard":
            hard += 1

    return {
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "total": len(questions),
    }


def format_datetime(value):
    if not value:
        return ""

    try:
        return value.isoformat()
    except Exception:
        return str(value)
