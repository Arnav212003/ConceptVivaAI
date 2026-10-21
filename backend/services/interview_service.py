"""Interview / ML-practice question generation and answer evaluation."""
import random

from services import llm
from services.grading import safety
from services.grading.evaluators import evaluate_answer, normalize_level
from services.grading.prompts import INTERVIEW_QUESTION
from services.grading.schemas import InterviewQuestionOutput

# Topic pools for "leave it blank and let AI choose". Selection happens on the
# server so the client never sends free-form instructions to the model.
AUTO_TOPIC_POOLS = {
    "ml": [
        "Supervised vs Unsupervised Learning", "Linear Regression", "Logistic Regression",
        "K-Nearest Neighbors", "Decision Trees", "Overfitting and Underfitting",
        "Bias-Variance Tradeoff", "Train/Test Split and Cross-Validation", "Feature Scaling",
        "Model Evaluation Metrics", "Confusion Matrix", "Precision, Recall and F1 Score",
    ],
    "interview": [
        "Machine Learning Basics", "Linear Regression", "Logistic Regression", "KNN",
        "Clustering", "Overfitting and Underfitting", "Bias-Variance Tradeoff",
        "Model Evaluation Metrics", "DSA Arrays", "DSA Strings", "Binary Search", "Graphs",
        "System Design Basics", "URL Shortener", "Rate Limiter", "Caching",
        "Load Balancing", "Database Design",
    ],
}


def choose_auto_topic(track: str, revision_topics=None) -> str:
    revision = [t.strip()[:120] for t in (revision_topics or []) if t and t.strip()]
    if revision:
        return revision[0]
    return random.choice(AUTO_TOPIC_POOLS.get(track, AUTO_TOPIC_POOLS["interview"]))


def fallback_question(topic: str) -> str:
    return f"Can you explain the core idea of {topic[:120]} and give one practical example?"


async def generate_interview_question(topic: str, level: str) -> dict:
    """Return {"question", "source"}; source is "ai" or "fallback"."""
    prompt = "\n\n".join([
        f"Difficulty: {normalize_level(level)}",
        "Topic:\n" + safety.wrap_untrusted("topic", topic, safety.new_boundary()),
    ])
    try:
        output = await llm.generate_structured(
            "interview_question",
            system_instruction=INTERVIEW_QUESTION.system_instruction,
            prompt=prompt,
            schema=InterviewQuestionOutput,
            temperature=0.8,
        )
        question = output.question.strip()
        if question:
            return {"question": question, "source": "ai"}
    except llm.LLMUnavailableError:
        pass
    return {"question": fallback_question(topic), "source": "fallback"}


async def evaluate_semantic_answer_with_gemini(request):
    return await evaluate_answer(
        topic=request.topic,
        level=request.level,
        question=request.question,
        answer=request.answer,
    )


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
