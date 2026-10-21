"use client";

import { useState } from "react";
import LocalHistoryTable from "@/components/LocalHistoryTable";
import { ErrorBanner, IntegrityNotice, LoadingState, ScoreValue, StatCard, UnavailableNotice } from "@/components/ui";
import useLocalHistory from "@/hooks/useLocalHistory";
import { apiPost } from "@/lib/api";
import { averageScore, formatScore } from "@/lib/scoring";

const AUTO_TOPIC_LABEL = "AI Selected ML Topic";

export default function MLPracticeCard() {
  const [topic, setTopic] = useState("");
  const [activeTopic, setActiveTopic] = useState(AUTO_TOPIC_LABEL);
  const [level, setLevel] = useState("Easy");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [loadingEvaluation, setLoadingEvaluation] = useState(false);
  const [error, setError] = useState("");
  const history = useLocalHistory("conceptviva_ml_practice_history");

  function resetAttempt() {
    setQuestion("");
    setAnswer("");
    setResult(null);
    setError("");
  }

  async function generateQuestion() {
    resetAttempt();
    setLoadingQuestion(true);
    const cleanTopic = topic.trim();
    try {
      // With no topic the server picks one from a curated ML pool.
      const data = await apiPost("/api/interview", {
        action: "question",
        level,
        ...(cleanTopic ? { topic: cleanTopic } : { auto_topic: true, track: "ml" }),
      });
      setQuestion(data.question);
      setActiveTopic(data.topic || cleanTopic || AUTO_TOPIC_LABEL);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingQuestion(false);
    }
  }

  async function evaluateAnswer() {
    if (!answer.trim()) {
      setError("Write your answer first.");
      return;
    }
    setLoadingEvaluation(true);
    setResult(null);
    setError("");
    try {
      const data = await apiPost("/api/interview", {
        action: "evaluate",
        topic: activeTopic,
        display_topic: activeTopic,
        level,
        question,
        answer,
        mode: "practice",
        save_attempt: true,
      });
      setResult(data);
      const now = new Date();
      history.add({
        date: now.toLocaleDateString(),
        time: now.toLocaleTimeString(),
        topic: activeTopic,
        level,
        question,
        score: typeof data.score === "number" ? data.score : null,
        verdict: data.verdict,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingEvaluation(false);
    }
  }

  const localAverage = averageScore(history.items);

  return (
    <div className="mt-10 rounded-3xl border border-slate-700 bg-slate-950/70 p-5 shadow-2xl">
      <div className="mb-6 border-b border-slate-800 pb-5">
        <p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">Practice Mode</p>
        <h2 className="mt-2 text-3xl font-bold text-white">AI ML Question Practice</h2>
        <p className="mt-1 text-base text-slate-400">
          Leave the topic blank and a Machine Learning topic is chosen for you. If you type a topic, questions
          come from that topic only.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        <StatCard label="Total Local Attempts" value={history.items.length} />
        <StatCard label="Local Average Score" value={formatScore(localAverage)} />
        <StatCard label="Current Topic" value={topic.trim() || activeTopic} valueClassName="text-xl" />
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        <div>
          <label htmlFor="ml-topic" className="mb-2 block text-sm text-slate-300">Topic (optional)</label>
          <input
            id="ml-topic"
            value={topic}
            maxLength={200}
            onChange={(event) => {
              setTopic(event.target.value);
              resetAttempt();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
            placeholder="Leave blank and an ML topic is chosen automatically"
          />
          <p className="mt-2 text-xs text-slate-500">Example: Logistic Regression, KNN, Overfitting, Evaluation Metrics</p>
        </div>

        <div>
          <label htmlFor="ml-level" className="mb-2 block text-sm text-slate-300">Difficulty</label>
          <select
            id="ml-level"
            value={level}
            onChange={(event) => {
              setLevel(event.target.value);
              resetAttempt();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
          >
            <option>Easy</option>
            <option>Medium</option>
            <option>Hard</option>
          </select>
        </div>

        <div className="flex items-end">
          <button
            onClick={generateQuestion}
            disabled={loadingQuestion}
            className="w-full rounded-xl bg-cyan-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-cyan-600 disabled:opacity-60"
          >
            {loadingQuestion ? "Generating..." : "Generate AI Question"}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-5">
          <ErrorBanner message={error} onDismiss={() => setError("")} />
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold text-white">AI Question</h3>
              <p className="mt-1 text-sm text-slate-400">Topic: {activeTopic}</p>
            </div>
            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">{level}</span>
          </div>
          <div className="mt-4 min-h-[240px] rounded-xl border border-slate-700 bg-slate-950/60 p-5">
            {loadingQuestion ? (
              <LoadingState label="Thinking of a good question..." />
            ) : question ? (
              <p className="whitespace-pre-line text-lg leading-8 text-white" data-testid="question">{question}</p>
            ) : (
              <p className="text-slate-400">Click Generate AI Question to start.</p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <label htmlFor="ml-answer" className="text-xl font-bold text-white">Your Answer</label>
          <textarea
            id="ml-answer"
            value={answer}
            maxLength={20000}
            onChange={(event) => setAnswer(event.target.value)}
            className="mt-4 min-h-[240px] w-full rounded-xl border border-slate-700 bg-slate-950/60 p-4 text-base leading-7 text-white outline-none"
            placeholder="Write your answer here..."
          />
          <button
            onClick={evaluateAnswer}
            disabled={loadingEvaluation || !question}
            className="mt-4 rounded-xl bg-emerald-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
          >
            {loadingEvaluation ? "Evaluating..." : "Submit Answer"}
          </button>
        </div>
      </div>

      {result && (
        <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-950/20 p-5" data-testid="ml-result">
          <div className="mb-4 space-y-3">
            <UnavailableNotice result={result} />
            <IntegrityNotice result={result} />
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-400">Score</p>
              <p className="mt-1"><ScoreValue score={result.score} /></p>
            </div>
            <StatCard label="Verdict" value={result.verdict} valueClassName="text-2xl" />
            <StatCard label="Topic" value={activeTopic} valueClassName="text-xl" />
          </div>

          {result.rubric && Object.keys(result.rubric).length > 0 && (
            <div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {Object.entries(result.rubric).map(([name, item]) => (
                <div key={name} className="rounded-xl border border-slate-700 bg-slate-950/50 p-3">
                  <p className="text-xs uppercase tracking-wide text-slate-400">{name.replaceAll("_", " ")}</p>
                  <p className="mt-1 font-bold text-white">{item.points}/{item.max_points}</p>
                  <p className="mt-1 text-xs text-slate-400">{item.rationale}</p>
                </div>
              ))}
            </div>
          )}

          {result.evaluation_status === "completed" && (
            <>
              <div className="mt-5 grid gap-4 lg:grid-cols-2">
                <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                  <p className="font-semibold text-emerald-300">Feedback</p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">{result.feedback}</p>
                </div>
                <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                  <p className="font-semibold text-yellow-300">Missing Points</p>
                  <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">{result.missing_points}</p>
                </div>
              </div>
              <div className="mt-5 rounded-xl border border-cyan-400/30 bg-cyan-950/20 p-4">
                <p className="font-semibold text-cyan-300">Better Interview-ready Answer</p>
                <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">{result.corrected_answer}</p>
              </div>
              <div className="mt-5 rounded-xl border border-pink-400/30 bg-pink-950/20 p-4">
                <p className="font-semibold text-pink-300">Follow-up Question</p>
                <p className="mt-2 text-sm leading-7 text-slate-200">{result.follow_up_question}</p>
              </div>
            </>
          )}
        </div>
      )}

      <LocalHistoryTable
        title="Recent ML Practice History"
        items={history.items}
        onClear={history.clear}
        emptyTitle="No ML practice history yet"
        emptyMessage="Submit your first answer to start tracking."
        columns={[
          { label: "Date", render: (item) => `${item.date} ${item.time}` },
          { label: "Topic", key: "topic", className: "font-semibold text-white" },
          { label: "Difficulty", key: "level" },
          { label: "Score", render: (item) => formatScore(item.score), className: "font-bold text-white" },
          { label: "Verdict", key: "verdict" },
        ]}
      />
    </div>
  );
}
