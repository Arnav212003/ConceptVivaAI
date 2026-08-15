"""Loads the curated DSA question bank.

Isolated in its own module so a missing/broken `data.dsa_question` module
only degrades DSA-bank features, instead of taking down the whole backend.
"""
try:
    from data.dsa_question import (
        DSA_QUESTION_BANK,
        get_all_dsa_questions,
        get_dsa_questions_by_difficulty,
        get_dsa_questions_by_topic,
        get_dsa_questions_by_topic_and_difficulty,
        get_dsa_question_by_id,
        get_dsa_question_by_title,
        get_dsa_mock_set,
        get_dsa_practice_question,
    )
except Exception:
    DSA_QUESTION_BANK = []

    def get_all_dsa_questions():
        return []

    def get_dsa_questions_by_difficulty(difficulty):
        return []

    def get_dsa_questions_by_topic(topic):
        return []

    def get_dsa_questions_by_topic_and_difficulty(topic, difficulty):
        return []

    def get_dsa_question_by_id(question_id):
        return None

    def get_dsa_question_by_title(title):
        return None

    def get_dsa_mock_set(topic="Arrays", difficulty="Mixed", count=10):
        return []

    def get_dsa_practice_question(topic="Arrays", difficulty="Mixed"):
        return None
