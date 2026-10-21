import ValueList from "@/components/project/ValueList";
import { IntegrityNotice, ScoreValue, StatCard, UnavailableNotice } from "@/components/ui";

function Section({ title, tone = "text-white", border = "border-slate-700 bg-slate-950/50", value }) {
  if (!value || (Array.isArray(value) && value.length === 0)) return null;
  return (
    <section className={`rounded-xl border p-4 ${border}`}>
      <p className={`font-semibold ${tone}`}>{title}</p>
      <ValueList value={value} />
    </section>
  );
}

export default function ProjectReview({ review }) {
  const completed = review.evaluation_status === "completed";
  return (
    <div className="mt-6 rounded-2xl border border-pink-400/30 bg-pink-950/20 p-5" data-testid="project-review">
      <div className="mb-4 space-y-3">
        <UnavailableNotice result={review} />
        <IntegrityNotice result={review} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
          <p className="text-sm text-slate-400">Score</p>
          <p className="mt-1"><ScoreValue score={review.score} /></p>
        </div>
        <StatCard label="Verdict" value={review.verdict} valueClassName="text-2xl" />
      </div>

      {completed && (
        <div className="mt-5 space-y-4">
          <Section title="Feedback" tone="text-emerald-300" value={review.feedback} />
          <Section title="Architecture Review" tone="text-blue-300" value={review.architecture_review} />
          <Section title="Code Bugs" tone="text-red-300" border="border-red-400/30 bg-red-950/10" value={review.bugs} />
          <Section
            title={`File-by-file Findings (${review.files_reviewed} reviewed)`}
            tone="text-violet-300"
            value={review.file_findings}
          />
          <Section title="Security Findings" tone="text-orange-300" border="border-orange-400/30 bg-orange-950/10" value={review.security_issues} />
          <Section title="Missing Project Requirements" tone="text-yellow-300" border="border-yellow-400/30 bg-yellow-950/10" value={review.missing_requirements} />
          <Section title="Missing Points" tone="text-yellow-300" value={review.missing_points} />
          <Section title="Improved Approach" tone="text-cyan-300" value={review.improved_approach} />
          <Section title="Next Steps" tone="text-pink-300" value={review.next_steps} />
        </div>
      )}
      {!completed && (
        <p className="mt-4 text-sm text-slate-300">
          Your challenge is still active, so you can submit the same folder again once AI review is back.
        </p>
      )}
    </div>
  );
}
