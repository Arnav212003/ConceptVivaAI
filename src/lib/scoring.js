// A result is "scored" only when the backend completed the evaluation and returned
// a number. Unavailable evaluations have score null and must never display as 0.
export function isScored(result) {
  if (!result) return false;
  if (result.evaluation_status && result.evaluation_status !== "completed") return false;
  return typeof result.score === "number" && Number.isFinite(result.score);
}

export function formatScore(score) {
  if (typeof score !== "number" || !Number.isFinite(score)) return "Not scored";
  return `${Number(score.toFixed(1))}/10`;
}

export function averageScore(items, key = "score") {
  const scores = items
    .map((item) => item?.[key])
    .filter((value) => typeof value === "number" && Number.isFinite(value));
  if (!scores.length) return null;
  return scores.reduce((sum, value) => sum + value, 0) / scores.length;
}

export function scoreTone(score) {
  if (typeof score !== "number") {
    return { text: "text-slate-300", border: "border-slate-700", bg: "bg-slate-950/40", bar: "bg-slate-600" };
  }
  if (score >= 8) {
    return { text: "text-emerald-300", border: "border-emerald-400/30", bg: "bg-emerald-950/20", bar: "bg-emerald-500" };
  }
  if (score >= 6) {
    return { text: "text-yellow-300", border: "border-yellow-400/30", bg: "bg-yellow-950/20", bar: "bg-yellow-500" };
  }
  return { text: "text-red-300", border: "border-red-400/30", bg: "bg-red-950/20", bar: "bg-red-500" };
}
