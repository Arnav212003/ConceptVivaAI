"""Graders the benchmark can evaluate.

- ProductionGrader: the exact production evaluator (`evaluate_answer`) including
  injection heuristics and score caps. Makes real Gemini calls.
- KeywordBaselineGrader: deterministic token-overlap with the reference answer.
  A deliberately naive baseline; the LLM grader should clearly beat it.
- ReplayGrader: re-reads gradings recorded by an earlier run so metrics can be
  recomputed (or compared across metric code changes) without new API calls.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from benchmarks.grader.dataset import BenchmarkItem

_STOPWORDS = set("""a an the is are was were be to of and or in on for with by it this that as at from
we you can use used using into than then so if which what how why when does do its their our""".split())


class ProductionGrader:
    name = "production"

    async def grade(self, item: BenchmarkItem, repeat: int) -> dict:
        from services.grading.evaluators import evaluate_answer

        result = await evaluate_answer(topic=item.topic, level=item.level,
                                       question=item.question, answer=item.answer)
        return {
            "score": result.get("score"),
            "status": result["evaluation_status"],
            "verdict": result.get("verdict"),
            "integrity_flags": result.get("integrity_flags", []),
            "score_capped": bool(result.get("score_capped")),
            "prompt_version": result.get("prompt_version"),
            "model": result.get("model"),
        }


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS and len(t) > 2}


class KeywordBaselineGrader:
    name = "keyword_baseline"

    async def grade(self, item: BenchmarkItem, repeat: int) -> dict:
        reference = _tokens(item.reference_answer or item.question)
        answer = _tokens(item.answer)
        recall = len(reference & answer) / len(reference) if reference else 0.0
        score = round(min(10.0, 10.0 * recall), 1)
        return {"score": score, "status": "completed", "verdict": None, "integrity_flags": [],
                "prompt_version": "keyword_baseline@1", "model": "none"}


class _FullyFooledBackend:
    """Simulates a model that has been completely taken over by an injection:
    it awards maximum rubric points and never reports manipulation."""

    model_name = "simulated-fooled-model"

    async def generate(self, *, system_instruction, prompt, response_schema, temperature):
        criteria = response_schema.model_fields["rubric"].annotation.model_fields
        rubric = {}
        for name, field in criteria.items():
            points_field = field.annotation.model_fields["points"]
            maximum = next(m.le for m in points_field.metadata if hasattr(m, "le"))
            rubric[name] = {"points": maximum, "rationale": "simulated"}
        return json.dumps({
            "rubric": rubric, "manipulation_attempt": False, "feedback": "simulated",
            "missing_points": "", "corrected_answer": "", "improvement": "", "follow_up_question": "",
        })


class FooledModelGrader(ProductionGrader):
    """Production evaluator + a fully fooled model: measures server-side defenses alone."""

    name = "fooled_model"

    async def grade(self, item: BenchmarkItem, repeat: int) -> dict:
        from services import llm

        llm.set_llm_backend(_FullyFooledBackend())
        try:
            return await super().grade(item, repeat)
        finally:
            llm.set_llm_backend(None)


class ReplayGrader:
    name = "replay"

    def __init__(self, gradings_path: Path):
        self.records = defaultdict(list)
        for line in Path(gradings_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                self.records[record["item_id"]].append(record)

    async def grade(self, item: BenchmarkItem, repeat: int) -> dict:
        records = self.records.get(item.id) or []
        if repeat >= len(records):
            return {"score": None, "status": "missing_in_replay", "verdict": None, "integrity_flags": []}
        return {k: v for k, v in records[repeat].items() if k not in ("item_id", "repeat")}
