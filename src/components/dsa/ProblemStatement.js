import { EmptyState, LoadingState } from "@/components/ui";
import { DifficultyBadge } from "@/components/dsa/Badges";

function Example({ example, index }) {
  return (
    <div className="mt-5">
      <p className="font-semibold text-white">Example {index + 1}:</p>
      <div className="mt-2 overflow-x-auto rounded-xl border border-slate-700 bg-slate-950 p-4 font-mono text-[13px] leading-6">
        {typeof example === "object" ? (
          <>
            <p>
              <span className="font-semibold text-slate-400">Input: </span>
              <span className="text-slate-100">{example.input}</span>
            </p>
            <p className="mt-1">
              <span className="font-semibold text-slate-400">Output: </span>
              <span className="text-slate-100">{example.output}</span>
            </p>
            {example.explanation && (
              <p className="mt-1">
                <span className="font-semibold text-slate-400">Explanation: </span>
                <span className="text-slate-300">{example.explanation}</span>
              </p>
            )}
          </>
        ) : (
          <p className="text-slate-100">{String(example)}</p>
        )}
      </div>
    </div>
  );
}

export default function ProblemStatement({ problemData, problemText, loading, emptyTitle, emptyMessage }) {
  if (loading) return <LoadingState label="Writing your problem statement..." />;

  if (!problemData) {
    if (problemText) {
      return <div className="whitespace-pre-line text-[14px] leading-7 text-slate-100">{problemText}</div>;
    }
    return <EmptyState className="min-h-[500px]" title={emptyTitle} message={emptyMessage} />;
  }

  const examples = Array.isArray(problemData.examples) ? problemData.examples : [];
  const constraints = Array.isArray(problemData.constraints) ? problemData.constraints : [];

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="text-2xl font-bold text-white">{problemData.title}</h3>
        <DifficultyBadge value={problemData.difficulty} />
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        {[problemData.topic, problemData.pattern].filter(Boolean).map((tag) => (
          <span key={tag} className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
            {tag}
          </span>
        ))}
      </div>

      {problemData.generated_by === "fallback" && (
        <p className="mt-4 rounded-lg border border-amber-700/50 bg-amber-950/30 px-3 py-2 text-xs text-amber-200">
          The AI problem writer is unavailable, so only the problem title is shown. Hidden tests still work.
        </p>
      )}

      <div className="mt-5 whitespace-pre-line text-[14px] leading-7 text-slate-100">{problemData.description}</div>

      {examples.map((example, index) => (
        <Example key={index} example={example} index={index} />
      ))}

      {constraints.length > 0 && (
        <div className="mt-5">
          <p className="font-semibold text-white">Constraints:</p>
          <ul className="mt-2 space-y-2 pl-1">
            {constraints.map((constraint, index) => (
              <li key={index}>
                <code className="rounded-md bg-slate-950 px-2 py-1 font-mono text-[13px] text-slate-200">
                  {constraint}
                </code>
              </li>
            ))}
          </ul>
        </div>
      )}

      {problemData.follow_up && (
        <div className="mt-5 rounded-xl border border-slate-700 bg-slate-950/60 p-4">
          <p className="text-sm leading-7 text-slate-300">
            <span className="font-semibold text-white">Follow-up: </span>
            {problemData.follow_up}
          </p>
        </div>
      )}
    </div>
  );
}
