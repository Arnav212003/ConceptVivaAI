"""Benchmark metrics, dataset validation, and the offline pipeline."""
import asyncio
import json
from pathlib import Path

import pytest

from benchmarks.grader import metrics
from benchmarks.grader.dataset import BenchmarkItem, import_labeling_csv, load_dataset
from benchmarks.grader.graders import FooledModelGrader, KeywordBaselineGrader
from benchmarks.grader.run_benchmark import SYNTHETIC_BANNER, collect_gradings, compute_report, main, render_markdown

SEED = Path(__file__).resolve().parents[1] / "benchmarks" / "grader" / "data" / "synthetic_seed.jsonl"


# ------------------------------------------------------------------ metrics


def test_mae_rmse_known_values():
    assert metrics.mae([1, 2, 3], [2, 2, 5]) == 1.0
    assert metrics.rmse([0, 0], [3, 4]) == pytest.approx(3.5355, rel=1e-3)


def test_pearson_and_spearman():
    assert metrics.pearson([1, 2, 3, 4], [2, 4, 6, 8]) == pytest.approx(1.0)
    assert metrics.pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert metrics.pearson([1, 1, 1], [1, 2, 3]) is None
    # Monotonic but non-linear: Spearman is exactly 1.
    assert metrics.spearman([1, 2, 3, 4], [1, 4, 9, 100]) == pytest.approx(1.0)


def test_average_ranks_handles_ties():
    assert metrics.average_ranks([10, 20, 20, 30]) == [1.0, 2.5, 2.5, 4.0]


def test_cohen_kappa():
    assert metrics.cohen_kappa(["A", "B", "A", "B"], ["A", "B", "A", "B"]) == pytest.approx(1.0)
    # Textbook example: observed 0.7, expected 0.5 -> kappa 0.4
    a = ["Y"] * 25 + ["N"] * 25
    b = ["Y"] * 20 + ["N"] * 5 + ["Y"] * 10 + ["N"] * 15
    assert metrics.cohen_kappa(a, b) == pytest.approx(0.4)


def test_repeatability_and_bootstrap():
    rep = metrics.repeatability([[5, 5, 5], [4, 6], [7]])
    assert rep["items"] == 2
    assert rep["identical_rate"] == 0.5
    low, high = metrics.bootstrap_ci([1, 2, 3, 4, 5, 6], [1, 2, 4, 4, 6, 6])
    assert 0 <= low <= high <= 1


def test_length_mismatch_raises():
    with pytest.raises(ValueError):
        metrics.mae([1], [1, 2])


# ------------------------------------------------------------------ dataset


def _row(**overrides):
    row = {"id": "x1", "source": "human", "topic": "KNN", "question": "Q", "answer": "A",
           "human_scores": [7], "labelers": ["a"]}
    row.update(overrides)
    return row


def test_human_rows_need_labelers_and_no_synthetic_reference():
    BenchmarkItem.model_validate(_row())
    with pytest.raises(ValueError):
        BenchmarkItem.model_validate(_row(labelers=[]))
    with pytest.raises(ValueError):
        BenchmarkItem.model_validate(_row(reference_score=5))
    with pytest.raises(ValueError):
        BenchmarkItem.model_validate(_row(human_scores=[11], labelers=["a"]))


def test_synthetic_rows_cannot_claim_human_scores():
    with pytest.raises(ValueError):
        BenchmarkItem.model_validate(_row(source="synthetic", reference_score=5))


def test_mixed_datasets_are_rejected(tmp_path):
    path = tmp_path / "mixed.jsonl"
    synthetic = _row(id="s1", source="synthetic", human_scores=[], labelers=[], reference_score=5)
    path.write_text(json.dumps(_row()) + "\n" + json.dumps(synthetic) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mixes"):
        load_dataset(path)


def test_seed_set_is_fully_synthetic_and_valid():
    items = load_dataset(SEED)
    assert len(items) == 41
    assert {item.source for item in items} == {"synthetic"}
    assert sum(item.adversarial for item in items) == 10


def test_csv_import_groups_labelers(tmp_path):
    csv_path = tmp_path / "labels.csv"
    csv_path.write_text(
        "id,topic,level,question,answer,labeler,score\n"
        "h1,KNN,Easy,What is KNN?,Votes of neighbours,ann,7\n"
        "h1,KNN,Easy,What is KNN?,Votes of neighbours,bob,8\n"
        "h2,KNN,Easy,What is KNN?,No idea,ann,\n",
        encoding="utf-8",
    )
    out = tmp_path / "human.jsonl"
    assert import_labeling_csv(csv_path, out) == 1
    item = load_dataset(out)[0]
    assert item.human_scores == [7.0, 8.0]
    assert item.target == 7.5


# ------------------------------------------------------------------ pipeline


def test_report_marks_synthetic_data_prominently():
    items = load_dataset(SEED)
    gradings = asyncio.run(collect_gradings(items, KeywordBaselineGrader(), repeats=2))
    report = compute_report(items, gradings, {
        "grader": "keyword_baseline", "dataset": SEED.name, "dataset_fingerprint": "x", "items": len(items),
        "repeats": 2, "run_at": "now", "prompt_versions": [], "models": [],
    })
    markdown = render_markdown(report)

    assert report["meta"]["synthetic"] is True
    assert markdown.startswith(f"> **{SYNTHETIC_BANNER}**")
    assert report["agreement"]["items"] == 31
    assert report["repeatability"]["identical_rate"] == 1.0  # deterministic baseline


def test_server_side_defenses_hold_when_model_is_fully_fooled():
    items = load_dataset(SEED)
    gradings = asyncio.run(collect_gradings(items, FooledModelGrader(), repeats=1, concurrency=1))
    report = compute_report(items, gradings, {
        "grader": "fooled_model", "dataset": SEED.name, "dataset_fingerprint": "x", "items": len(items),
        "repeats": 1, "run_at": "now", "prompt_versions": [], "models": [],
    })
    assert report["adversarial"]["attack_success_rate"] == 0.0
    # Honest answers, including the security-topic control that quotes an attack, keep their score.
    assert report["false_positives"]["capped_rate"] == 0.0


def test_production_grader_requires_explicit_cost_opt_in():
    with pytest.raises(SystemExit, match="allow-api-calls"):
        main(["--dataset", str(SEED), "--grader", "production"])


def test_cli_writes_reports(tmp_path):
    assert main(["--dataset", str(SEED), "--grader", "keyword_baseline", "--out-dir", str(tmp_path)]) == 0
    run_dir = next(tmp_path.iterdir())
    assert {p.name for p in run_dir.iterdir()} == {"gradings.jsonl", "report.json", "report.md"}
