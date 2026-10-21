"""Grader benchmark CLI.

Examples (run from backend/):
  # Offline pipeline check on the clearly-labelled synthetic seed set (free):
  python -m benchmarks.grader.run_benchmark --dataset benchmarks/grader/data/synthetic_seed.jsonl \
      --grader keyword_baseline

  # Real benchmark against human labels (makes Gemini calls: items x repeats):
  python -m benchmarks.grader.run_benchmark --dataset benchmarks/grader/data/human_labels.jsonl \
      --grader production --repeats 3 --allow-api-calls

  # Recompute metrics from a previous run without API calls:
  python -m benchmarks.grader.run_benchmark --dataset ... --grader replay \
      --replay benchmarks/grader/results/<run>/gradings.jsonl
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from benchmarks.grader import metrics
from benchmarks.grader.dataset import BenchmarkItem, dataset_fingerprint, load_dataset
from benchmarks.grader.graders import (
    FooledModelGrader,
    KeywordBaselineGrader,
    ProductionGrader,
    ReplayGrader,
)

SYNTHETIC_BANNER = (
    "SYNTHETIC DATA: target scores were written by the developer to exercise the pipeline. "
    "These numbers are NOT a measurement of agreement with human graders."
)


def verdict_for(score: float) -> str:
    return "STRONG" if score >= 8 else ("PARTIAL" if score >= 5 else "WEAK")


async def collect_gradings(items, grader, repeats: int, concurrency: int = 4) -> list[dict]:
    semaphore = asyncio.Semaphore(concurrency)

    async def one(item: BenchmarkItem, repeat: int):
        async with semaphore:
            started = time.perf_counter()
            graded = await grader.grade(item, repeat)
            graded["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
            return {"item_id": item.id, "repeat": repeat, **graded}

    tasks = [one(item, r) for item in items for r in range(repeats)]
    return await asyncio.gather(*tasks)


def compute_report(items: list[BenchmarkItem], gradings: list[dict], meta: dict) -> dict:
    by_item: dict[str, list[dict]] = {}
    for record in gradings:
        by_item.setdefault(record["item_id"], []).append(record)

    graded_items, unavailable = [], 0
    for item in items:
        if item.adversarial:
            continue
        scores = [g["score"] for g in by_item.get(item.id, []) if g.get("status") == "completed"
                  and g.get("score") is not None]
        unavailable += sum(1 for g in by_item.get(item.id, []) if g.get("status") != "completed")
        if scores and item.target is not None:
            graded_items.append((item, scores))

    targets = [item.target for item, _ in graded_items]
    predicted = [mean(scores) for _, scores in graded_items]
    agreement = {"items": len(graded_items)}
    if graded_items:
        agreement.update({
            "mae": metrics.mae(targets, predicted),
            "mae_ci95": metrics.bootstrap_ci(targets, predicted),
            "rmse": metrics.rmse(targets, predicted),
            "pearson": metrics.pearson(targets, predicted),
            "spearman": metrics.spearman(targets, predicted),
            "within_1": metrics.within(targets, predicted, 1.0),
            "verdict_kappa": metrics.cohen_kappa([verdict_for(t) for t in targets],
                                                 [verdict_for(p) for p in predicted]),
        })

    human_ceiling = None
    multi = [item for item in items if item.source == "human" and len(item.human_scores) >= 2]
    if multi:
        first = [item.human_scores[0] for item in multi]
        second = [item.human_scores[1] for item in multi]
        human_ceiling = {
            "items": len(multi),
            "labeler_mae": metrics.mae(first, second),
            "labeler_pearson": metrics.pearson(first, second),
        }

    adversarial = [item for item in items if item.adversarial]
    attack = {"items": len(adversarial)}
    if adversarial:
        outcomes = []
        for item in adversarial:
            for g in by_item.get(item.id, []):
                if g.get("status") == "completed" and g.get("score") is not None:
                    outcomes.append({
                        "item_id": item.id,
                        "score": g["score"],
                        "max_allowed": item.max_allowed_score,
                        "succeeded": g["score"] > item.max_allowed_score,
                        "flagged": bool(g.get("integrity_flags")),
                    })
        if outcomes:
            attack.update({
                "gradings": len(outcomes),
                "attack_success_rate": mean(1.0 if o["succeeded"] else 0.0 for o in outcomes),
                "flag_rate": mean(1.0 if o["flagged"] else 0.0 for o in outcomes),
                "successful_attacks": [o for o in outcomes if o["succeeded"]],
            })

    honest = [g for item in items if not item.adversarial for g in by_item.get(item.id, [])
              if g.get("status") == "completed"]
    false_positives = {
        "gradings": len(honest),
        "capped_rate": mean(1.0 if g.get("score_capped") else 0.0 for g in honest) if honest else None,
        "flagged_rate": mean(1.0 if g.get("integrity_flags") else 0.0 for g in honest) if honest else None,
    }

    sources = sorted({item.source for item in items})
    return {
        "meta": {**meta, "sources": sources, "synthetic": "synthetic" in sources},
        "agreement": agreement,
        "repeatability": metrics.repeatability([s for _, s in graded_items]),
        "human_ceiling": human_ceiling,
        "adversarial": attack,
        "false_positives": false_positives,
        "unavailable_gradings": unavailable,
        "total_gradings": len(gradings),
    }


def _fmt(value, digits=2):
    if value is None:
        return "n/a"
    if isinstance(value, tuple):
        return f"[{value[0]:.{digits}f}, {value[1]:.{digits}f}]"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_markdown(report: dict) -> str:
    meta, agreement = report["meta"], report["agreement"]
    lines = []
    if meta["synthetic"]:
        lines += [f"> **{SYNTHETIC_BANNER}**", ""]
    lines += [
        f"# Grader benchmark: {meta['grader']} on `{meta['dataset']}`",
        "",
        f"- Run at: {meta['run_at']}",
        f"- Dataset fingerprint: `{meta['dataset_fingerprint']}` ({meta['items']} items, sources: {', '.join(meta['sources'])})",
        f"- Prompt version(s): {', '.join(meta['prompt_versions']) or 'n/a'}; model(s): {', '.join(meta['models']) or 'n/a'}",
        f"- Repeats per item: {meta['repeats']}",
        f"- Unavailable gradings: {report['unavailable_gradings']} / {report['total_gradings']}",
        "",
        "## Agreement with target scores",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Items scored | {agreement['items']} |",
        f"| MAE (0-10 scale) | {_fmt(agreement.get('mae'))} |",
        f"| MAE 95% bootstrap CI | {_fmt(agreement.get('mae_ci95'))} |",
        f"| RMSE | {_fmt(agreement.get('rmse'))} |",
        f"| Pearson r | {_fmt(agreement.get('pearson'))} |",
        f"| Spearman rho | {_fmt(agreement.get('spearman'))} |",
        f"| Within +/-1 point | {_fmt(agreement.get('within_1'))} |",
        f"| Verdict Cohen's kappa | {_fmt(agreement.get('verdict_kappa'))} |",
        "",
        "## Repeatability (same answer graded repeatedly)",
        "",
    ]
    rep = report["repeatability"]
    if rep.get("items"):
        lines += [
            "| Metric | Value |", "|---|---|",
            f"| Items with >= 2 runs | {rep['items']} |",
            f"| Mean per-item std | {_fmt(rep['mean_std'])} |",
            f"| Max per-item std | {_fmt(rep['max_std'])} |",
            f"| Identical across runs | {_fmt(rep['identical_rate'])} |",
            f"| Range within 1 point | {_fmt(rep['within_1_rate'])} |",
        ]
    else:
        lines.append("Run with `--repeats 2` or more to measure repeatability.")

    lines += ["", "## Human inter-rater ceiling", ""]
    ceiling = report["human_ceiling"]
    lines.append(
        f"Labeler 1 vs labeler 2 on {ceiling['items']} items: MAE {_fmt(ceiling['labeler_mae'])}, "
        f"Pearson {_fmt(ceiling['labeler_pearson'])}." if ceiling else
        "Not available (needs human rows with at least two labelers)."
    )

    lines += ["", "## Adversarial prompt-injection suite", ""]
    attack = report["adversarial"]
    if attack.get("gradings"):
        lines += [
            f"- Gradings: {attack['gradings']} over {attack['items']} attack items",
            f"- Attack success rate (score above allowed maximum): {_fmt(attack['attack_success_rate'])}",
            f"- Flag rate (integrity flag raised): {_fmt(attack['flag_rate'])}",
        ]
        for success in attack["successful_attacks"][:10]:
            lines.append(f"  - `{success['item_id']}` scored {success['score']} (allowed {success['max_allowed']})")
    else:
        lines.append("No adversarial items in this dataset.")

    fp = report["false_positives"]
    lines += ["", "## False positives on honest answers", ""]
    lines.append(
        f"- Honest gradings: {fp['gradings']}; score capped: {_fmt(fp['capped_rate'])}; "
        f"integrity flag raised: {_fmt(fp['flagged_rate'])}"
    )
    return "\n".join(lines) + "\n"


def build_grader(args):
    if args.grader == "keyword_baseline":
        return KeywordBaselineGrader()
    if args.grader == "fooled_model":
        return FooledModelGrader()
    if args.grader == "replay":
        if not args.replay:
            raise SystemExit("--replay <gradings.jsonl> is required for the replay grader")
        return ReplayGrader(Path(args.replay))
    if not args.allow_api_calls:
        raise SystemExit(
            "The production grader makes real Gemini calls (items x repeats). "
            "Re-run with --allow-api-calls once you accept the cost."
        )
    from config import settings

    if not settings.gemini_api_key:
        raise SystemExit("GEMINI_API_KEY is not configured.")
    return ProductionGrader()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--grader", choices=["production", "keyword_baseline", "fooled_model", "replay"], default="keyword_baseline")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--replay")
    parser.add_argument("--allow-api-calls", action="store_true")
    parser.add_argument("--out-dir", default=str(Path(__file__).parent / "results"))
    args = parser.parse_args(argv)

    dataset_path = Path(args.dataset)
    items = load_dataset(dataset_path)
    if args.limit:
        items = items[: args.limit]
    grader = build_grader(args)

    gradings = asyncio.run(collect_gradings(items, grader, max(1, args.repeats), args.concurrency))
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    meta = {
        "grader": grader.name,
        "dataset": dataset_path.name,
        "dataset_fingerprint": dataset_fingerprint(dataset_path),
        "items": len(items),
        "repeats": max(1, args.repeats),
        "run_at": run_at,
        "prompt_versions": sorted({g.get("prompt_version") for g in gradings if g.get("prompt_version")}),
        "models": sorted({g.get("model") for g in gradings if g.get("model")}),
    }
    report = compute_report(items, gradings, meta)

    out_dir = Path(args.out_dir) / f"{run_at}_{grader.name}_{dataset_path.stem}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "gradings.jsonl").write_text("\n".join(json.dumps(g) for g in gradings) + "\n", encoding="utf-8")
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=list), encoding="utf-8")
    markdown = render_markdown(report)
    (out_dir / "report.md").write_text(markdown, encoding="utf-8")
    sys.stdout.write(markdown)
    sys.stdout.write(f"\nWrote {out_dir}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
