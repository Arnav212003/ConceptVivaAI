"""Benchmark dataset format, validation and CSV import.

Every row declares where its target score came from:
- source="human":     `human_scores` from one or more named labelers (target = mean).
- source="synthetic": `reference_score` written by the developer to smoke-test the
                      pipeline. Synthetic rows are NOT human evaluation data and the
                      report says so in its first line.
A dataset may not mix the two, so a headline number is never half-synthetic.
"""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class BenchmarkItem(BaseModel):
    id: str = Field(min_length=1, max_length=80)
    source: Literal["human", "synthetic"]
    topic: str = Field(min_length=1)
    level: str = "Medium"
    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)
    reference_answer: str = ""
    human_scores: list[float] = Field(default_factory=list)
    labelers: list[str] = Field(default_factory=list)
    reference_score: Optional[float] = None
    adversarial: bool = False
    max_allowed_score: Optional[float] = None
    notes: str = ""

    @model_validator(mode="after")
    def _consistent(self):
        for score in self.human_scores + ([self.reference_score] if self.reference_score is not None else []):
            if not 0 <= score <= 10:
                raise ValueError(f"{self.id}: scores must be within 0-10")
        if self.source == "human":
            if not self.human_scores:
                raise ValueError(f"{self.id}: human rows need human_scores")
            if len(self.labelers) != len(self.human_scores):
                raise ValueError(f"{self.id}: one labeler id per human score")
            if self.reference_score is not None:
                raise ValueError(f"{self.id}: human rows must not carry a synthetic reference_score")
        else:
            if self.human_scores or self.labelers:
                raise ValueError(f"{self.id}: synthetic rows must not claim human scores")
            if self.reference_score is None and not self.adversarial:
                raise ValueError(f"{self.id}: synthetic rows need reference_score")
        if self.adversarial and self.max_allowed_score is None:
            raise ValueError(f"{self.id}: adversarial rows need max_allowed_score")
        return self

    @property
    def target(self) -> Optional[float]:
        if self.source == "human":
            return mean(self.human_scores)
        return self.reference_score


def load_dataset(path: Path) -> list[BenchmarkItem]:
    items, seen = [], set()
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            item = BenchmarkItem.model_validate_json(line)
        except ValueError as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
        if item.id in seen:
            raise ValueError(f"{path}:{line_no}: duplicate id {item.id}")
        seen.add(item.id)
        items.append(item)
    sources = {item.source for item in items}
    if len(sources) > 1:
        raise ValueError("dataset mixes human and synthetic rows; keep them in separate files")
    return items


def dataset_fingerprint(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:16]


def import_labeling_csv(csv_path: Path, out_path: Path) -> int:
    """Convert the labeling sheet (one row per labeler x answer) into JSONL.

    Required columns: id, topic, level, question, answer, labeler, score.
    Optional: reference_answer, adversarial (true/false), max_allowed_score, notes.
    """
    grouped: dict[str, dict] = {}
    scores = defaultdict(list)
    with open(csv_path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            item_id = row["id"].strip()
            if not row.get("score", "").strip():
                continue  # unlabeled row
            grouped.setdefault(item_id, {
                "id": item_id,
                "source": "human",
                "topic": row["topic"].strip(),
                "level": row.get("level", "Medium").strip() or "Medium",
                "question": row["question"].strip(),
                "answer": row["answer"].strip(),
                "reference_answer": row.get("reference_answer", "").strip(),
                "adversarial": row.get("adversarial", "").strip().lower() == "true",
                "max_allowed_score": float(row["max_allowed_score"]) if row.get("max_allowed_score") else None,
                "notes": row.get("notes", "").strip(),
            })
            scores[item_id].append((row["labeler"].strip(), float(row["score"])))

    lines = []
    for item_id, base in grouped.items():
        base["labelers"] = [labeler for labeler, _ in scores[item_id]]
        base["human_scores"] = [score for _, score in scores[item_id]]
        lines.append(BenchmarkItem.model_validate(base).model_dump_json())
    Path(out_path).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)
