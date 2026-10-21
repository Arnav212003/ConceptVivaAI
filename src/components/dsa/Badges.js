import { difficultyStyle } from "@/lib/difficulty";

export function DifficultyBadge({ value }) {
  if (!value) return null;
  return (
    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${difficultyStyle(value).badge}`}>{value}</span>
  );
}

export function TierBadge({ tier }) {
  if (!tier) {
    return <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">Practice</span>;
  }
  const verified = tier === "verified";
  return (
    <span
      className={`rounded-full px-3 py-1 text-xs font-semibold ${
        verified ? "bg-emerald-500/20 text-emerald-300" : "bg-indigo-500/20 text-indigo-300"
      }`}
      title={verified ? "Scored by hidden tests in the isolated judge" : "Scored by AI review, no hidden tests"}
    >
      {verified ? "✅ Verified" : "🤖 AI Generated"}
    </span>
  );
}
