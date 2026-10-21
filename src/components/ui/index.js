import { formatScore, scoreTone } from "@/lib/scoring";

export function StatCard({ label, value, subtext, valueClassName = "text-3xl" }) {
  return (
    <div className="min-w-0 rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
      <p className="text-sm text-slate-400">{label}</p>
      <p className={`mt-1 break-words font-bold text-white ${valueClassName}`}>{value}</p>
      {subtext && <p className="mt-1 text-sm text-slate-500">{subtext}</p>}
    </div>
  );
}

export function EmptyState({ title, message, className = "" }) {
  return (
    <div
      className={`flex items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center ${className}`}
    >
      <div>
        <p className="text-lg font-semibold text-white">{title}</p>
        {message && <p className="mt-2 text-sm text-slate-400">{message}</p>}
      </div>
    </div>
  );
}

export function ErrorBanner({ message, onRetry, onDismiss }) {
  if (!message) return null;
  return (
    <div
      role="alert"
      className="flex flex-col gap-3 rounded-xl border border-red-400/40 bg-red-950/30 p-4 text-sm text-red-200 sm:flex-row sm:items-center sm:justify-between"
    >
      <p>{message}</p>
      <div className="flex gap-2">
        {onRetry && (
          <button onClick={onRetry} className="rounded-lg bg-red-500/20 px-3 py-1.5 font-semibold hover:bg-red-500/30">
            Retry
          </button>
        )}
        {onDismiss && (
          <button onClick={onDismiss} aria-label="Dismiss" className="rounded-lg px-3 py-1.5 hover:bg-red-500/20">
            Dismiss
          </button>
        )}
      </div>
    </div>
  );
}

export function Notice({ tone = "info", children }) {
  const tones = {
    info: "border-cyan-400/30 bg-cyan-950/20 text-cyan-100",
    warn: "border-amber-700/50 bg-amber-950/30 text-amber-200",
    success: "border-emerald-400/30 bg-emerald-950/20 text-emerald-100",
  };
  return <div className={`rounded-xl border px-4 py-3 text-sm ${tones[tone]}`}>{children}</div>;
}

export function LoadingState({ label = "Loading..." }) {
  return (
    <div role="status" className="flex min-h-[160px] items-center justify-center gap-3 text-sm text-slate-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-slate-600 border-t-cyan-400" aria-hidden />
      {label}
    </div>
  );
}

// Shows "Not scored" for unavailable evaluations instead of a misleading 0/10.
export function ScoreValue({ score, className = "text-3xl" }) {
  const tone = scoreTone(score);
  return <span className={`font-bold ${tone.text} ${className}`}>{formatScore(score)}</span>;
}

export function UnavailableNotice({ result }) {
  if (!result || result.evaluation_status !== "unavailable") return null;
  return (
    <Notice tone="warn">
      AI evaluation was unavailable, so this attempt was <strong>not scored</strong> and does not affect your
      averages. Please try again in a moment.
    </Notice>
  );
}

export function IntegrityNotice({ result }) {
  if (!result?.score_capped) return null;
  return (
    <Notice tone="warn">
      Part of this answer tried to instruct the grader, so the score was capped. Answer the question directly
      to get full credit.
    </Notice>
  );
}
