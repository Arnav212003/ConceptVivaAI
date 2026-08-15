"""Business logic for interview/ML-practice question generation and evaluation."""
from config import GEMINI_API_KEY
from services.gemini_client import client
from utils import extract_json


def generate_interview_question(topic, level):
    if not GEMINI_API_KEY or not client:
        return f"Can you explain the basic concept of {topic}?"

    prompt = f"""
You are ConceptVivaAI, a strict real interview agent.

Generate only one interview question.

Topic: {topic}
Difficulty: {level}

Rules:
- Ask only one question.
- Stay strictly inside the selected topic.
- Do not provide the answer.
- Question should sound like a real interviewer.
- Keep it clear and natural.
- Prefer conceptual, practical, and interview-relevant questions.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        return response.text
    except Exception:
        return f"Can you explain the basic concept of {topic} and why it is important?"


def evaluate_semantic_answer_with_gemini(request):
    fallback = {
        "score": 5.0,
        "verdict": "PARTIAL",
        "feedback": "Your answer was received. Detailed AI evaluation is temporarily unavailable.",
        "missing_points": "Add the most important technical points and one relevant example.",
        "corrected_answer": "Use a simple structure: definition, how it works, example, and limitation or trade-off.",
        "improvement": "Make the answer more structured and technically specific.",
        "follow_up_question": f"Can you give one practical example related to {request.display_topic or 'this topic'}?",
    }

    if not GEMINI_API_KEY or not client:
        return fallback

    prompt = f"""
You are ConceptVivaAI, a strict but fair semantic mock interview evaluator.

Topic:
{request.topic}

Difficulty:
{request.level}

Interviewer Question:
{request.question}

Student Answer:
{request.answer}

Evaluation rules:
1. Judge semantic correctness, not exact wording.
2. Accept simple English when the technical meaning is correct.
3. Penalize wrong technical claims, contradictions, vague non-answers, and missing core concepts.
4. Check relevance, clarity, structure, depth, and whether an example is useful.
5. Stay strictly within the selected topic.

Scoring guide:
0-2: wrong or unrelated.
3-4: partly related but concept mostly wrong.
5-6: basic idea but incomplete/vague.
7-8: correct with minor gaps.
9-10: strong, structured, interview-ready.

Verdict rules:
- STRONG: score >= 8
- PARTIAL: score 5 to 7.9
- WEAK: score < 5

Return only valid JSON:
{{
  "score": number from 0 to 10,
  "verdict": "STRONG or PARTIAL or WEAK",
  "feedback": "what was correct and what needs correction",
  "missing_points": "important missing points",
  "corrected_answer": "better interview-ready answer in simple English",
  "improvement": "one specific improvement tip",
  "follow_up_question": "one targeted follow-up question"
}}
"""

    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        result = extract_json(response.text) or {}
    except Exception:
        return fallback

    try:
        score = max(0.0, min(10.0, float(result.get("score", 5))))
    except Exception:
        score = 5.0

    result["score"] = score
    if score >= 8:
        result["verdict"] = "STRONG"
    elif score >= 5:
        result["verdict"] = "PARTIAL"
    else:
        result["verdict"] = "WEAK"

    for key, value in fallback.items():
        result.setdefault(key, value)
    return result


def interview_summary(avg_score):
    if avg_score >= 8:
        return (
            "Concept clarity and answer structure are strong.",
            "Add more edge cases and real-world examples for extra depth.",
            "Strong performance. Continue with harder follow-up questions.",
        )
    if avg_score >= 6:
        return (
            "The core understanding is present.",
            "Improve depth, examples, technical keywords, and answer structure.",
            "Good base. Revise weak concepts and repeat a focused mock interview.",
        )
    return (
        "You are attempting the questions and building recall.",
        "Core definitions, working, examples, and trade-offs need revision.",
        "Revise the weak concepts first, then retry a shorter structured interview.",
    )
