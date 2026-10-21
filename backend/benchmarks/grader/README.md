# AI grader benchmark

Measures how closely the production answer grader (`answer_eval` prompt, see
`services/grading/prompts.py`) agrees with human graders, how repeatable it is, and
how it holds up against prompt-injection attacks.

## What is in this folder

| Path | Purpose |
|---|---|
| `data/synthetic_seed.jsonl` | 41 **synthetic** rows written by the developer: 10 questions x strong/partial/wrong answers, 10 injection attacks, 1 security-topic control. Used to exercise the pipeline and the injection suite. **Not human data.** |
| `data/labeling_template.csv` | Sheet for collecting the 100 human-labelled answers. |
| `dataset.py` | Row schema + validation + CSV import. Human and synthetic rows cannot be mixed. |
| `graders.py` | `production` (real Gemini), `keyword_baseline`, `fooled_model` (server-side defenses only), `replay`. |
| `metrics.py` | MAE, RMSE, Pearson, Spearman, within-1, Cohen's kappa, bootstrap CI, repeatability. |
| `run_benchmark.py` | CLI that writes `report.md`, `report.json` and raw `gradings.jsonl` to `results/`. |

## Collecting the 100 human labels

The pipeline can evaluate 100+ human-labelled answers, but those labels must come
from real people. They are not shipped here.

1. Collect real answers (with consent) or write a range of answers yourself:
   aim for 100 answers across at least 10 topics, with a spread of quality.
2. Two or more labelers score every answer **blind**, without seeing model scores,
   using the rubric below. Each labeler writes their own row in the CSV.
3. Import and validate:
   ```bash
   python -c "from benchmarks.grader.dataset import import_labeling_csv; \
   print(import_labeling_csv('labels.csv', 'benchmarks/grader/data/human_labels.jsonl'))"
   ```
4. Run (makes `items x repeats` Gemini calls):
   ```bash
   python -m benchmarks.grader.run_benchmark --dataset benchmarks/grader/data/human_labels.jsonl \
       --grader production --repeats 3 --allow-api-calls
   ```
5. Compare with the free baseline and with the human inter-rater ceiling in the report.

### Rubric for labelers (same as the production prompt)

| Criterion | Points | Guidance |
|---|---|---|
| technical_correctness | 0-4 | 4 fully correct, 2 one real error, 0 wrong or contradictory |
| completeness | 0-3 | covers the core concepts the question asks for |
| clarity_structure | 0-2 | clear, logical; simple English is fine |
| depth_examples | 0-1 | relevant example, trade-off or edge case |

Score = total points (0-10). Write the total in the `score` column.

## Metrics reported

- **MAE / RMSE** between the grader (mean over repeats) and the human mean, plus a 95% bootstrap CI for MAE.
- **Pearson / Spearman** correlation, **within ±1** rate, and **Cohen's kappa** on STRONG/PARTIAL/WEAK verdicts.
- **Repeatability**: per-item standard deviation and the share of items with identical scores across repeats.
- **Human ceiling**: MAE and correlation between labeler 1 and labeler 2. A grader cannot be expected to agree with humans more than humans agree with each other.
- **Adversarial suite**: attack success rate (final score above the item's `max_allowed_score`) and flag rate.
- **False positives**: share of honest answers that were capped or flagged.

## Results recorded so far

Only offline runs on the synthetic seed set have been executed (`keyword_baseline`
and `fooled_model`). They validate the pipeline and the server-side injection
defenses, and say nothing about agreement with humans. No production-grader
(Gemini) run and no human-labelled run has been performed yet.

On the synthetic seed set the `fooled_model` grader (the model is assumed to be fully
taken over and gives maximum points) produced: attack success rate 0.00 over the
10 attack items, and 0 of 31 honest answers capped. These attacks were written by
the same developer who wrote the heuristics, so this measures the defenses against
known attack patterns, not against novel ones.
