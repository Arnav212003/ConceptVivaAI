"use client";

import { EmptyState, ErrorBanner, LoadingState } from "@/components/ui";
import CodeEditor from "@/components/dsa/CodeEditor";
import ProblemStatement from "@/components/dsa/ProblemStatement";
import SolutionPanel from "@/components/dsa/SolutionPanel";
import { TestCaseList, VerdictBanner } from "@/components/dsa/TestResults";
import VoiceControls from "@/components/dsa/VoiceControls";
import { difficultyStyle } from "@/lib/difficulty";
import { AI_SAMPLES_NOTE, crossCheckNote } from "@/lib/testResults";

const TABS = [
  ["code", "</> Code", "border-pink-400"],
  ["testcase", "Testcase", "border-cyan-400"],
  ["result", "Result", "border-emerald-400"],
];

function RunPanel({ workspace }) {
  const { runResult, loading } = workspace;
  if (loading.run) return <LoadingState label="Running your code against the test cases..." />;
  if (!runResult) {
    return (
      <EmptyState
        className="min-h-[500px]"
        title="No run yet"
        message='Click "Run Code" to check your solution without saving an attempt.'
      />
    );
  }
  if (runResult.error) return <ErrorBanner message={runResult.error} />;
  return (
    <div>
      {runResult.source === "ai" && (
        <p className="mb-3 text-xs text-slate-400">
          Quick AI check (no executable tests are available for this question right now). Nothing was saved.
        </p>
      )}
      {runResult.source === "ai_samples" && (
        <p className="mb-3 text-xs text-amber-200/90" data-testid="ai-samples-note">
          {AI_SAMPLES_NOTE} {crossCheckNote(runResult.cross_check)} Nothing was saved.
        </p>
      )}
      <VerdictBanner judge={runResult.judge} testCases={runResult.test_cases} />
      <TestCaseList testCases={runResult.test_cases} />
    </div>
  );
}

export default function Workspace({
  workspace,
  voice,
  header,
  onRun,
  onSubmit,
  onRevealSolution,
  emptyTitle = "No problem generated yet",
  emptyMessage = "Select topic and difficulty, then click Generate Problem.",
  lockedMessage = "Generate a problem first. Starter code will appear here.",
}) {
  const { problem, problemData, activeTab, setActiveTab, loading, busy, feedback } = workspace;
  const hasProblem = Boolean(problem || problemData);
  const border = problemData ? `border-l-4 ${difficultyStyle(problemData.difficulty).border} rounded-l-2xl` : "";

  return (
    <div className={`grid min-h-[680px] gap-4 lg:grid-cols-2 ${border}`}>
      <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex items-center justify-between gap-3 border-b border-slate-800 px-5 py-4">{header}</div>
        <div className="max-h-[600px] overflow-y-auto p-5">
          <ProblemStatement
            problemData={problemData}
            problemText={problem}
            loading={loading.problem}
            emptyTitle={emptyTitle}
            emptyMessage={emptyMessage}
          />
        </div>
      </div>

      <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/80">
        <div className="flex overflow-x-auto border-b border-slate-800" role="tablist">
          {TABS.map(([id, label, accent]) => (
            <button
              key={id}
              role="tab"
              aria-selected={activeTab === id}
              onClick={() => setActiveTab(id)}
              className={`whitespace-nowrap px-5 py-4 text-sm font-semibold transition ${
                activeTab === id ? `border-b-2 ${accent} text-white` : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {label}
              {id === "testcase" && workspace.runResult?.test_cases?.length > 0 && (
                <span className="ml-2 rounded-full bg-slate-800 px-2 py-0.5 text-xs">
                  {workspace.runResult.test_cases.length}
                </span>
              )}
            </button>
          ))}
        </div>

        {activeTab === "code" && (
          <div className="p-5">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-sm text-slate-400">Language</p>
              <span className="rounded-lg bg-slate-800 px-3 py-1 font-mono text-sm text-slate-200">Python3</span>
            </div>
            <CodeEditor
              value={workspace.solution}
              onChange={workspace.setSolution}
              locked={!hasProblem}
              lockedMessage={loading.problem ? "Loading question..." : lockedMessage}
            />
            <div className="mt-4 flex flex-wrap gap-3">
              <button
                onClick={onRun}
                disabled={busy || !hasProblem}
                className="rounded-xl bg-slate-700 px-6 py-3 text-base font-semibold text-white transition hover:bg-slate-600 disabled:opacity-60"
              >
                {loading.run ? "Running..." : "▶ Run Code"}
              </button>
              <button
                onClick={onSubmit}
                disabled={busy || !hasProblem}
                className="rounded-xl bg-emerald-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
              >
                {loading.submit ? "Submitting..." : "Submit"}
              </button>
              <button
                onClick={() => workspace.setSolution(workspace.starterCode)}
                disabled={!hasProblem}
                className="rounded-xl border border-slate-700 bg-transparent px-6 py-3 text-base font-semibold text-slate-300 transition hover:bg-slate-800 disabled:opacity-60"
              >
                Reset to Starter Code
              </button>
              {onRevealSolution && (
                <button
                  onClick={onRevealSolution}
                  disabled={busy || !hasProblem}
                  className="rounded-xl border border-amber-400/40 bg-amber-950/20 px-6 py-3 text-base font-semibold text-amber-300 transition hover:bg-amber-950/40 disabled:opacity-60 sm:ml-auto"
                >
                  {loading.solution ? "Loading..." : "🔓 Stuck? Show & Explain Solution"}
                </button>
              )}
            </div>
          </div>
        )}

        {activeTab === "testcase" && (
          <div className="max-h-[600px] overflow-y-auto p-5">
            <RunPanel workspace={workspace} />
          </div>
        )}

        {activeTab === "result" && (
          <div className="max-h-[600px] overflow-y-auto p-5">
            {loading.submit || loading.solution ? (
              <LoadingState label="Reviewing your solution..." />
            ) : feedback ? (
              <SolutionPanel
                feedback={feedback}
                solutionOnly={workspace.solutionOnly}
                voiceControls={voice ? <VoiceControls voice={voice} /> : null}
                largeVoiceControls={voice ? <VoiceControls voice={voice} large /> : null}
              />
            ) : (
              <EmptyState
                className="min-h-[500px]"
                title="No result yet"
                message="Write your solution and click Submit for hidden-test and AI evaluation."
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
