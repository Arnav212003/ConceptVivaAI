import { IntegrityNotice, ScoreValue, UnavailableNotice } from "@/components/ui";
import { TestCaseList, VerdictBanner } from "@/components/dsa/TestResults";

function Block({ title, tone = "slate", children, right }) {
  const tones = {
    slate: "border-slate-700 bg-slate-950/50 text-white",
    indigo: "border-indigo-400/30 bg-indigo-950/30 text-indigo-200",
    pink: "border-pink-400/30 bg-pink-950/20 text-pink-200",
  };
  return (
    <div className={`mb-5 rounded-2xl border p-5 ${tones[tone]}`}>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
        <h4 className="text-base font-semibold">{title}</h4>
        {right}
      </div>
      {children}
    </div>
  );
}

const SCORING_LABEL = {
  hidden_tests: "Scored by hidden tests in the isolated judge",
  ai_rubric: "Scored by AI rubric review",
};

export default function SolutionPanel({ feedback, solutionOnly, voiceControls, largeVoiceControls }) {
  return (
    <div>
      {solutionOnly ? (
        <div className="mb-5 rounded-2xl border border-indigo-400/40 bg-indigo-950/30 p-5">
          <div className="flex flex-col items-center gap-3 text-center">
            <p className="text-base font-semibold text-indigo-200">
              Here's the solution. Want the AI to walk you through it out loud?
            </p>
            {largeVoiceControls}
            <p className="text-xs text-slate-400">This wasn't recorded as a scored attempt.</p>
          </div>
        </div>
      ) : (
        <>
          <VerdictBanner judge={feedback.judge} testCases={feedback.test_cases} />
          <div className="mb-5 space-y-3">
            <UnavailableNotice result={feedback} />
            <IntegrityNotice result={feedback} />
          </div>
          <div className="mb-5 rounded-2xl border border-emerald-400/30 bg-emerald-950/30 p-5">
            <p className="text-sm text-slate-400">Score</p>
            <p className="mt-1" data-testid="dsa-score">
              <ScoreValue score={feedback.score} className="text-4xl" />
            </p>
            {feedback.scoring_method && (
              <p className="mt-2 text-xs text-slate-400">{SCORING_LABEL[feedback.scoring_method]}</p>
            )}
          </div>
          <Block title="Test Cases">
            <TestCaseList testCases={feedback.test_cases} />
          </Block>
          <Block title="Feedback">
            <p className="whitespace-pre-line text-sm leading-7 text-slate-200">{feedback.feedback}</p>
          </Block>
        </>
      )}

      <Block title="Optimized Approach" tone="indigo" right={!solutionOnly ? voiceControls : null}>
        <p className="whitespace-pre-line text-sm leading-7 text-slate-200">
          {feedback.optimized_approach || "Not available."}
        </p>
      </Block>

      <Block title="Optimized Python Code" tone="pink">
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-4 font-mono text-xs leading-6 text-emerald-100">
          {feedback.optimized_code || "Not available."}
        </pre>
      </Block>

      <Block title="Explanation">
        <p className="whitespace-pre-line text-sm leading-7 text-slate-200">{feedback.explanation || "Not available."}</p>
      </Block>

      <div className="grid gap-4 md:grid-cols-2">
        {[
          ["Time Complexity", feedback.time_complexity],
          ["Space Complexity", feedback.space_complexity],
        ].map(([label, value]) => (
          <div key={label} className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
            <p className="text-sm text-slate-400">{label}</p>
            <p className="mt-1 font-mono text-base font-semibold text-white">{value || "N/A"}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
