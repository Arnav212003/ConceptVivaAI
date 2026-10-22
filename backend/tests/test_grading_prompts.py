"""Prompt versioning guard.

If this test fails you edited a prompt. Bump that PromptSpec's version, update the
fingerprint below, and re-run the grader benchmark so results stay comparable.
"""
from services.grading.prompts import ALL_PROMPTS, ANSWER_RUBRIC, CODE_RUBRIC, PROJECT_RUBRIC

PINNED_FINGERPRINTS = {
    "answer_eval@2.0.0": "3ba46e278789951e",
    "code_review@2.0.0": "148d62a541accb5f",
    "project_review@2.0.0": "7c76e16b84966acb",
    "interview_question@2.0.0": "5dacf9a67aa5fd4f",
    "dsa_problem@2.0.0": "ced45a793e3e878e",
    "ai_practice_problem@1.0.0": "a2a89b30b8ea90cd",
    "project_challenge@2.0.0": "f1615c4393d324fc",
    "translate_hindi@2.0.0": "b39dcaed9fe48825",
}


def test_prompt_text_matches_pinned_version():
    actual = {spec.id: spec.fingerprint for spec in ALL_PROMPTS}
    assert actual == PINNED_FINGERPRINTS


def test_prompt_ids_are_unique():
    ids = [spec.id for spec in ALL_PROMPTS]
    assert len(ids) == len(set(ids))


def test_every_prompt_carries_untrusted_data_rules():
    for spec in ALL_PROMPTS:
        assert "untrusted_" in spec.system_instruction, spec.id


def test_rubrics_sum_to_ten():
    for rubric in (ANSWER_RUBRIC, CODE_RUBRIC, PROJECT_RUBRIC):
        assert rubric.max_total == 10, rubric.name
