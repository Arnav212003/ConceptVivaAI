export default function ResultCard({ result }) {
  if (!result) return null;

  const score = Number(result.score || 0);

  function getScoreTone(value) {
    if (value >= 8) {
      return {
        text: "text-emerald-300",
        border: "border-emerald-400/30",
        bg: "bg-emerald-950/20",
      };
    }

    if (value >= 6) {
      return {
        text: "text-yellow-300",
        border: "border-yellow-400/30",
        bg: "bg-yellow-950/20",
      };
    }

    return {
      text: "text-red-300",
      border: "border-red-400/30",
      bg: "bg-red-950/20",
    };
  }

  const tone = getScoreTone(score);

  return (
    <div className={`rounded-2xl border ${tone.border} ${tone.bg} p-5`}>
      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
          <p className="text-sm text-slate-400">Score</p>
          <p className={`mt-1 text-3xl font-bold ${tone.text}`}>
            {score}/10
          </p>
        </div>

        <div className="md:col-span-2 rounded-xl border border-slate-700 bg-slate-950/50 p-4">
          <p className="font-semibold text-white">Feedback</p>
          <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">
            {result.feedback}
          </p>
        </div>
      </div>

      <div className="mt-5 rounded-xl border border-cyan-400/30 bg-cyan-950/20 p-4">
        <p className="font-semibold text-cyan-300">Improvement Tip</p>
        <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">
          {result.improvement}
        </p>
      </div>

      {result.follow_up_question && (
        <div className="mt-5 rounded-xl border border-pink-400/30 bg-pink-950/20 p-4">
          <p className="font-semibold text-pink-300">Follow-up Question</p>
          <p className="mt-2 text-sm leading-7 text-slate-200">
            {result.follow_up_question}
          </p>
        </div>
      )}
    </div>
  );
}
