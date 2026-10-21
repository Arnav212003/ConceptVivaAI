import { formatScore, scoreTone } from "@/lib/scoring";

export function formatDate(value) {
  if (!value) return "N/A";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function readinessLabel(value) {
  if (value >= 80) return "Interview Ready";
  if (value >= 60) return "Good Progress";
  if (value >= 40) return "Needs Practice";
  if (value > 0) return "Revision Needed";
  return "No Data Yet";
}

export function ProgressBar({ value }) {
  const safe = Math.max(0, Math.min(100, Number(value || 0)));
  return (
    <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-800" role="progressbar" aria-valuenow={safe} aria-valuemin={0} aria-valuemax={100}>
      <div className={`h-full rounded-full ${scoreTone(safe / 10).bar}`} style={{ width: `${safe}%` }} />
    </div>
  );
}

export function OverviewCard({ label, value, subtext }) {
  return (
    <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
      <p className="text-sm text-slate-400">{label}</p>
      <p className="mt-2 text-4xl font-bold text-white">{value}</p>
      <p className="mt-2 text-sm text-slate-500">{subtext}</p>
    </div>
  );
}

export function ModuleCard({ title, stats, description, tierBreakdown }) {
  const scored = stats?.scored_attempts ?? stats?.total_attempts ?? stats?.total_interviews ?? 0;
  const total = stats?.total_attempts ?? stats?.total_interviews ?? 0;
  const average = scored > 0 ? Number(stats?.average_score || 0) : null;
  const readiness = average === null ? 0 : Math.round(average * 10);
  const tone = scoreTone(average);

  return (
    <div className={`rounded-2xl border ${tone.border} ${tone.bg} p-5 shadow-xl`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-bold text-white">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-400">{description}</p>
        </div>
        <span className={`whitespace-nowrap rounded-full border ${tone.border} px-3 py-1 text-xs font-semibold ${tone.text}`}>
          {readinessLabel(readiness)}
        </span>
      </div>

      <div className="mt-5 grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
          <p className="text-xs text-slate-400">Total</p>
          <p className="mt-1 text-2xl font-bold text-white">{total}</p>
          {stats?.unavailable_attempts > 0 && (
            <p className="mt-1 text-[11px] text-amber-300">{stats.unavailable_attempts} not scored</p>
          )}
        </div>
        <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
          <p className="text-xs text-slate-400">Average</p>
          <p className="mt-1 text-2xl font-bold text-white">{formatScore(average)}</p>
        </div>
      </div>

      {tierBreakdown && (
        <div className="mt-3 grid grid-cols-2 gap-4">
          {[
            ["✅ Verified", tierBreakdown.verified, "Hidden-test scored", "border-emerald-800/60 bg-emerald-950/20 text-emerald-300"],
            ["🤖 AI Generated", tierBreakdown.ai_generated, "AI-reviewed scoring", "border-indigo-800/60 bg-indigo-950/20 text-indigo-300"],
          ].map(([label, tier, note, style]) => (
            <div key={label} className={`rounded-xl border p-4 ${style}`}>
              <p className="text-xs font-semibold">{label} ({tier.total_attempts})</p>
              <p className="mt-1 text-lg font-bold text-white">
                {formatScore(tier.scored_attempts > 0 ? tier.average_score : null)}
              </p>
              <p className="mt-1 text-[11px] text-slate-500">{note}</p>
            </div>
          ))}
        </div>
      )}

      <ProgressBar value={readiness} />
      <p className="mt-2 text-xs text-slate-500">Readiness: {readiness}%</p>
    </div>
  );
}

export function SectionCard({ title, children }) {
  return (
    <div className="min-w-0 rounded-2xl border border-slate-700 bg-slate-900/70 p-5 shadow-xl">
      <h2 className="mb-4 text-xl font-bold text-white">{title}</h2>
      {children}
    </div>
  );
}

export function CompactRecord({ title, subtitle, date }) {
  return (
    <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
      <p className="break-words font-semibold text-white">{title}</p>
      <p className="mt-1 text-sm leading-6 text-slate-400">{subtitle}</p>
      <p className="mt-1 text-xs text-slate-500">{formatDate(date)}</p>
    </div>
  );
}

export function SkeletonGrid() {
  return (
    <div className="mb-8 grid gap-4 md:grid-cols-4" aria-hidden>
      {Array.from({ length: 4 }).map((_, index) => (
        <div key={index} className="h-32 animate-pulse rounded-2xl border border-slate-800 bg-slate-900/60" />
      ))}
    </div>
  );
}

// Flattens backend history into one timeline. Unscored attempts keep score null.
export function buildTimeline(history) {
  const items = [
    ...(history?.ml_practice || []).map((item) => ({
      id: `ml-${item.id}`, type: "ML Practice", title: item.topic || "ML Practice",
      subtitle: `Score: ${formatScore(item.score)} · Verdict: ${item.verdict || "N/A"}`,
      score: item.score, topic: item.topic, created_at: item.created_at,
    })),
    ...(history?.dsa_practice || []).map((item) => ({
      id: `dsa-${item.id}`, type: item.tier === "verified" ? "DSA Attempt · Verified" : "DSA Attempt",
      title: item.problem_name || "DSA Problem",
      subtitle: `Topic: ${item.topic || "DSA"} · Score: ${formatScore(item.score)} · ${item.judge_verdict || item.status || ""}`,
      score: item.score, topic: item.topic, created_at: item.created_at,
    })),
    ...(history?.project_challenge || []).map((item) => ({
      id: `project-${item.id}`, type: "Project Challenge", title: item.project_title || "Project Challenge",
      subtitle: `Topic: ${item.topic || "Project"} · Score: ${formatScore(item.score)} · Verdict: ${item.verdict || "N/A"}`,
      score: item.score, topic: item.topic, created_at: item.created_at,
    })),
    ...(history?.voice_interview || []).map((item) => ({
      id: `voice-${item.id}`, type: "Voice Interview", title: item.topic || "Voice Interview",
      subtitle: `Rounds: ${item.rounds || 0} · Average Score: ${formatScore(item.average_score)}`,
      score: item.average_score, topic: item.topic, created_at: item.created_at,
    })),
  ];
  return items.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
}

export function buildTopicReadiness(timeline) {
  const topics = new Map();
  for (const item of timeline) {
    if (typeof item.score !== "number") continue;
    const key = item.topic || "Unknown Topic";
    const entry = topics.get(key) || { topic: key, total: 0, count: 0, types: new Set() };
    entry.total += item.score;
    entry.count += 1;
    entry.types.add(item.type.split(" · ")[0]);
    topics.set(key, entry);
  }
  return [...topics.values()]
    .map((entry) => ({
      topic: entry.topic,
      attempts: entry.count,
      averageScore: entry.total / entry.count,
      readiness: Math.round((entry.total / entry.count) * 10),
      types: [...entry.types].join(", "),
    }))
    .sort((a, b) => b.readiness - a.readiness)
    .slice(0, 10);
}
