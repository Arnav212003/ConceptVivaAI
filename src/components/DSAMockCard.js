"use client";

import { useState } from "react";
import Link from "next/link";
import { DifficultyBadge, TierBadge } from "@/components/dsa/Badges";
import Workspace from "@/components/dsa/Workspace";
import { ErrorBanner, LoadingState } from "@/components/ui";
import useDsaWorkspace from "@/hooks/useDsaWorkspace";
import useJudgeStatus from "@/hooks/useJudgeStatus";
import useLocalHistory from "@/hooks/useLocalHistory";
import useSolutionVoice from "@/hooks/useSolutionVoice";
import { track } from "@/lib/analytics";
import { apiPost } from "@/lib/api";
import { DSA_TOPICS } from "@/lib/difficulty";

export default function DSAMockCard() {
  const [topic, setTopic] = useState("Arrays");
  const [questions, setQuestions] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loadingSet, setLoadingSet] = useState(false);
  const [setError, setSetError] = useState("");

  const workspace = useDsaWorkspace();
  const voice = useSolutionVoice(workspace.feedback);
  const judgeEnabled = useJudgeStatus();
  const history = useLocalHistory("conceptviva_dsa_history");

  const questionTopic = selected?.topic || topic;
  const questionDifficulty = selected?.difficulty || "Medium";

  async function generateMockSet() {
    setLoadingSet(true);
    setSetError("");
    setSelected(null);
    setQuestions([]);
    workspace.reset();
    try {
      const data = await apiPost("/api/dsa", { action: "generateMockSet", topic, difficulty: "Mixed", count: 10 });
      if (Array.isArray(data.questions) && data.questions.length > 0) {
        setQuestions(data.questions);
      } else {
        setSetError("No questions were returned for this topic. Try another topic.");
      }
    } catch (err) {
      setSetError(err.message);
    } finally {
      setLoadingSet(false);
    }
  }

  function openQuestion(question) {
    setSelected(question);
    workspace.loadProblem("generateFromQuestion", {
      question_id: question.id || "",
      title: question.title || "DSA Problem",
      topic: question.topic || topic,
      difficulty: question.difficulty || "Medium",
      pattern: question.pattern || "General DSA",
    });
  }

  async function submit() {
    if (!workspace.solution.trim()) {
      workspace.setError("Write your code first.");
      return;
    }
    const data = await workspace.submit({ topic: questionTopic, difficulty: questionDifficulty, mode: "Mock Interview" });
    if (data) {
      track("attempt_submitted", "dsa_mock");
      const today = new Date();
      history.add({
        date: today.toLocaleDateString(),
        time: today.toLocaleTimeString(),
        mode: "Mock Interview",
        topic: questionTopic,
        difficulty: questionDifficulty,
        problemName: workspace.problemData?.title || selected?.title || "DSA Problem",
        score: data.score,
        status: data.status || "Needs Improvement",
      });
    }
  }

  return (
    <div className="mt-10 w-full max-w-6xl rounded-3xl border border-slate-700 bg-slate-950/70 p-4 shadow-2xl">
      <div className="mb-5 border-b border-slate-800 pb-5">
        <Link href="/dsa" className="text-sm font-semibold text-emerald-300 hover:text-emerald-200">
          ← Back to DSA Home
        </Link>
        <p className="mt-3 text-sm font-semibold uppercase tracking-widest text-emerald-300">DSA Mock Interview</p>
        <h2 className="mt-2 text-3xl font-bold text-white">10-Question Mixed Set</h2>
        <p className="mt-1 text-base text-slate-400">
          Pick a topic, generate a mixed set (3 Easy, 4 Medium, 3 Hard), and attempt each question one at a time.
        </p>
      </div>

      <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div className="grid gap-4 md:grid-cols-3">
          <div className="md:col-span-2">
            <label htmlFor="mock-topic" className="mb-2 block text-sm text-slate-300">DSA Topic</label>
            <select
              id="mock-topic"
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value);
                setQuestions([]);
                setSelected(null);
                workspace.reset();
              }}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-base text-white outline-none"
            >
              {DSA_TOPICS.map((name) => (
                <option key={name}>{name}</option>
              ))}
            </select>
            <p className="mt-2 text-xs text-slate-400">Mock mode uses a mixed difficulty ratio automatically.</p>
          </div>
          <div className="flex items-end">
            <button
              onClick={generateMockSet}
              disabled={loadingSet}
              className="w-full rounded-xl bg-emerald-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
            >
              {loadingSet ? "Generating..." : "Generate Mock Set"}
            </button>
          </div>
        </div>
      </div>

      {setError && (
        <div className="mb-5">
          <ErrorBanner message={setError} onRetry={generateMockSet} />
        </div>
      )}
      {loadingSet && <LoadingState label="Building your mock set..." />}

      {questions.length > 0 && (
        <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-xl font-bold text-white">Mock Interview Question Set</h3>
              <p className="text-sm text-slate-400">Click any question to generate its full problem statement.</p>
            </div>
            <span className="rounded-full bg-slate-800 px-4 py-2 text-sm text-slate-300">
              {questions.length} Questions · 3 Easy + 4 Medium + 3 Hard
            </span>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {questions.map((question, index) => (
              <button
                key={question.id || index}
                onClick={() => openQuestion(question)}
                className={`rounded-xl border p-4 text-left transition ${
                  selected?.id === question.id
                    ? "border-emerald-400 bg-emerald-950/30"
                    : "border-slate-700 bg-slate-950/40 hover:border-slate-500"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm text-slate-400">Question {index + 1}</p>
                    <p className="mt-1 font-semibold text-white">{question.title}</p>
                    <p className="mt-1 text-xs text-slate-400">{question.pattern}</p>
                  </div>
                  <DifficultyBadge value={question.difficulty} />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {workspace.error && (
        <div className="mb-5">
          <ErrorBanner message={workspace.error} onDismiss={() => workspace.setError("")} />
        </div>
      )}

      <Workspace
        workspace={workspace}
        voice={voice}
        onRun={() => workspace.run({ topic: questionTopic, difficulty: questionDifficulty, judgeEnabled })}
        onSubmit={submit}
        emptyTitle="No question selected"
        emptyMessage="Generate a mock set, then click one question from the list."
        lockedMessage="Pick a question from the set first."
        header={
          <>
            <h3 className="text-lg font-semibold text-white">Problem Statement</h3>
            <TierBadge tier={workspace.tier} />
          </>
        }
      />

      <div className="mt-6 text-center">
        <Link href="/dsa/history" className="text-sm font-semibold text-cyan-300 hover:text-cyan-200">
          View full history →
        </Link>
      </div>
    </div>
  );
}
