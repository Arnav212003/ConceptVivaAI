export default function ResultCard({ result }) {
  if (!result) return null;

  return (
    <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-950/30 p-5">
      <h3 className="mb-3 text-xl font-semibold text-emerald-300">
        AI Evaluation Result
      </h3>

      <div className="mb-4">
        <p className="text-sm text-slate-400">Score</p>
        <p className="text-3xl font-bold text-white">{result.score}/10</p>
      </div>

      <div className="mb-4">
        <p className="text-sm text-slate-400">Feedback</p>
        <p className="text-slate-200">{result.feedback}</p>
      </div>

      <div className="mb-4">
        <p className="text-sm text-slate-400">Improvement Tip</p>
        <p className="text-slate-200">{result.improvement}</p>
      </div>

      {result.follow_up_question && (
        <div className="mt-5 rounded-xl border border-indigo-400/30 bg-indigo-950/40 p-4">
          <p className="text-sm text-indigo-300">Follow-up Question</p>
          <p className="mt-2 text-lg font-semibold text-white">
            {result.follow_up_question}
          </p>
        </div>
      )}
    </div>
  );
}