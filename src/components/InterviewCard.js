"use client";

import { useEffect, useRef, useState } from "react";
import LocalHistoryTable from "@/components/LocalHistoryTable";
import ResultCard from "@/components/ResultCard";
import { ErrorBanner, LoadingState, StatCard } from "@/components/ui";
import useLocalHistory from "@/hooks/useLocalHistory";
import useSpeechRecognition from "@/hooks/useSpeechRecognition";
import useSpeechSynthesis from "@/hooks/useSpeechSynthesis";
import { apiPost } from "@/lib/api";
import { averageScore, formatScore, isScored } from "@/lib/scoring";

const MAX_ROUNDS = 5;
const AUTO_TOPIC_LABEL = "AI Selected Topic";
const REVISION_KEY = "conceptviva_interview_revision";

function readRevisionQueue() {
  try {
    const parsed = JSON.parse(window.localStorage.getItem(REVISION_KEY) || "[]");
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function summary(avg) {
  if (avg >= 8) {
    return {
      strongPoints: "Concept clarity, confidence, and answer structure look strong.",
      weakPoints: "Add more real-world examples and edge-case explanations to make answers stronger.",
      recommendation: "Strong interview performance. You are close to interview-ready for this topic.",
    };
  }
  if (avg >= 6) {
    return {
      strongPoints: "Basic understanding is present and you are able to attempt the questions.",
      weakPoints: "Improve depth, examples, interview keywords, and step-by-step explanation.",
      recommendation: "Good base is present, but answers need more structure, examples, and technical depth.",
    };
  }
  return {
    strongPoints: "You are practicing consistently, which is the first strong point.",
    weakPoints: "Revise definitions, working, examples, advantages, limitations, and common interview questions.",
    recommendation: "Needs focused revision. First revise core concepts, then practice short structured answers.",
  };
}

export default function InterviewCard() {
  const [topic, setTopic] = useState("");
  const [activeTopic, setActiveTopic] = useState(AUTO_TOPIC_LABEL);
  const [level, setLevel] = useState("Easy");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [loadingEvaluation, setLoadingEvaluation] = useState(false);
  const [round, setRound] = useState(0);
  const [rounds, setRounds] = useState([]);
  const [finalReport, setFinalReport] = useState(null);
  const [revisionQueue, setRevisionQueue] = useState([]);
  const [error, setError] = useState("");

  // Refs avoid stale state inside speech callbacks that fire seconds later.
  const autoModeRef = useRef(false);
  const followUpUsedRef = useRef(false);
  const [autoMode, setAutoModeState] = useState(false);

  const history = useLocalHistory("conceptviva_interview_history");
  const speech = useSpeechSynthesis();
  const mic = useSpeechRecognition({ onTranscript: setAnswer });

  useEffect(() => {
    setRevisionQueue(readRevisionQueue());
  }, []);

  function setAutoMode(value) {
    autoModeRef.current = value;
    setAutoModeState(value);
  }

  function persistRevision(updated) {
    setRevisionQueue(updated);
    try {
      window.localStorage.setItem(REVISION_KEY, JSON.stringify(updated));
    } catch {
      // ignore storage failures
    }
  }

  function addRevisionItem(item) {
    const key = `${item.topic}|${item.question}`;
    persistRevision([item, ...revisionQueue.filter((entry) => `${entry.topic}|${entry.question}` !== key)].slice(0, 20));
  }

  function askQuestion(text) {
    setQuestion(text);
    setRound((prev) => prev + 1);
    speech.speak(text, {
      onEnd: () => {
        if (autoModeRef.current) mic.start("");
      },
    });
  }

  async function generateQuestion(followUp = "") {
    setResult(null);
    setAnswer("");
    setError("");
    if (followUp) {
      askQuestion(followUp);
      return;
    }

    setLoadingQuestion(true);
    const cleanTopic = topic.trim();
    try {
      const data = await apiPost("/api/interview", {
        action: "question",
        level,
        ...(cleanTopic
          ? { topic: cleanTopic }
          : {
              auto_topic: true,
              track: "interview",
              revision_topics: revisionQueue.slice(0, 5).map((item) => item.topic),
            }),
      });
      setActiveTopic(data.topic || cleanTopic || AUTO_TOPIC_LABEL);
      askQuestion(data.question);
    } catch (err) {
      setError(err.message);
      setAutoMode(false);
    } finally {
      setLoadingQuestion(false);
    }
  }

  async function saveReport(allRounds) {
    const scored = allRounds.filter((item) => typeof item.score === "number");
    if (scored.length === 0) {
      setError("None of the rounds could be scored (AI evaluation was unavailable), so no report was saved.");
      return;
    }
    const avg = Number(averageScore(scored).toFixed(1));
    const now = new Date();
    const report = {
      date: now.toLocaleDateString(),
      time: now.toLocaleTimeString(),
      topic: activeTopic,
      level,
      rounds: scored.length,
      skippedRounds: allRounds.length - scored.length,
      averageScore: avg,
      ...summary(avg),
    };
    setFinalReport(report);
    history.add(report);

    try {
      // The backend recomputes the average from its own signed receipts.
      await apiPost("/api/interview", {
        action: "saveInterviewReport",
        topic: activeTopic,
        level,
        rounds: scored.length,
        evaluation_receipts: scored.map((item) => item.receipt).filter(Boolean),
      });
    } catch (err) {
      setError(`Report shown locally, but saving it to your dashboard failed: ${err.message}`);
    }
  }

  async function evaluateAnswer() {
    if (!question.trim()) {
      setError("Generate a question first.");
      return;
    }
    if (!answer.trim()) {
      setError("Speak or type your answer first.");
      return;
    }
    mic.stop();
    setLoadingEvaluation(true);
    setError("");
    try {
      const data = await apiPost("/api/interview", {
        action: "evaluate",
        topic: activeTopic,
        display_topic: activeTopic,
        level,
        question,
        answer,
        mode: "interview",
      });
      setResult(data);
      const scored = isScored(data);
      const updatedRounds = [
        ...rounds,
        { round, score: scored ? data.score : null, verdict: data.verdict, receipt: data.evaluation_receipt || "" },
      ];
      setRounds(updatedRounds);
      if (data.verdict === "WEAK") addRevisionItem({ topic: activeTopic, question: question.slice(0, 300) });

      const spoken = scored
        ? `Your score is ${data.score} out of 10. ${data.improvement || ""}`
        : "I could not score that answer right now. Let's continue.";

      speech.speak(spoken, {
        onEnd: () => {
          if (!autoModeRef.current) return;
          if (updatedRounds.length >= MAX_ROUNDS) {
            setAutoMode(false);
            saveReport(updatedRounds);
            return;
          }
          if (data.verdict === "PARTIAL" && !followUpUsedRef.current && data.follow_up_question) {
            followUpUsedRef.current = true;
            generateQuestion(data.follow_up_question);
            return;
          }
          // STRONG moves on, WEAK goes to revision and moves on, a second PARTIAL moves on.
          followUpUsedRef.current = false;
          generateQuestion();
        },
      });
    } catch (err) {
      setError(err.message);
      setAutoMode(false);
    } finally {
      setLoadingEvaluation(false);
    }
  }

  function resetInterview() {
    speech.stop();
    mic.stop();
    setAutoMode(false);
    followUpUsedRef.current = false;
    setQuestion("");
    setAnswer("");
    setResult(null);
    setRound(0);
    setRounds([]);
    setFinalReport(null);
    setError("");
  }

  function startAutoInterview() {
    resetInterview();
    setAutoMode(true);
    setTimeout(() => generateQuestion(), 300);
  }

  function finishInterviewNow() {
    if (rounds.length === 0) {
      setError("Answer at least one question before finishing.");
      return;
    }
    setAutoMode(false);
    speech.stop();
    mic.stop();
    saveReport(rounds);
  }

  const localAverage = averageScore(history.items, "averageScore");

  return (
    <div className="mt-10 w-full max-w-6xl rounded-3xl border border-slate-700 bg-slate-950/70 p-5 shadow-2xl">
      <div className="mb-6 flex flex-col gap-4 border-b border-slate-800 pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">Voice Interview Mode</p>
          <h2 className="mt-2 text-3xl font-bold text-white">AI Mock Interview Coach</h2>
          <p className="mt-1 text-base text-slate-400">
            Practice topic-wise interview questions with voice, evaluation, follow-ups, and a final report.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            onClick={startAutoInterview}
            disabled={loadingQuestion || loadingEvaluation}
            className="rounded-xl bg-cyan-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-cyan-600 disabled:opacity-60"
          >
            {autoMode ? "Auto Interview Running..." : "Start Auto Interview"}
          </button>
          <button onClick={finishInterviewNow} className="rounded-xl bg-emerald-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-600">
            Finish & Report
          </button>
          <button onClick={resetInterview} className="rounded-xl bg-slate-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-600">
            Reset
          </button>
        </div>
      </div>

      <div className="mb-5 grid gap-4 sm:grid-cols-2 md:grid-cols-4">
        <StatCard label="Total Local Interviews" value={history.items.length} />
        <StatCard label="Local Avg Interview Score" value={formatScore(localAverage)} />
        <StatCard label="Current Round" value={`${round}/${MAX_ROUNDS}`} />
        <StatCard label="Last Local Topic" value={history.items[0]?.topic || "N/A"} valueClassName="text-xl" />
      </div>

      {revisionQueue.length > 0 && (
        <div className="mb-5 rounded-2xl border border-amber-500/30 bg-amber-950/20 p-4">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="font-semibold text-amber-200">Revision Queue</p>
              <p className="mt-1 text-sm text-slate-400">Weak answers are prioritized in the next AI-selected interview.</p>
            </div>
            <button
              onClick={() => persistRevision([])}
              className="rounded-lg bg-slate-800 px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-700"
            >
              Clear
            </button>
          </div>
          <ul className="mt-3 space-y-2 text-sm text-slate-300">
            {revisionQueue.slice(0, 3).map((item, index) => (
              <li key={`${item.topic}-${index}`} className="line-clamp-2">
                <span className="font-semibold text-amber-200">{item.topic}:</span> {item.question}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mb-5 grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="interview-topic" className="mb-2 block text-sm text-slate-300">Interview Topic (optional)</label>
          <input
            id="interview-topic"
            value={topic}
            maxLength={200}
            onChange={(e) => {
              setTopic(e.target.value);
              setActiveTopic(e.target.value.trim() || AUTO_TOPIC_LABEL);
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
            placeholder="Example: KNN, Clustering, Arrays, URL Shortener"
          />
          <p className="mt-2 text-xs text-slate-500">Leave blank and an interview topic is chosen automatically.</p>
        </div>
        <div>
          <label htmlFor="interview-level" className="mb-2 block text-sm text-slate-300">Difficulty</label>
          <select
            id="interview-level"
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
          >
            <option>Easy</option>
            <option>Medium</option>
            <option>Hard</option>
          </select>
        </div>
      </div>

      {(error || mic.error) && (
        <div className="mb-5">
          <ErrorBanner message={error || mic.error} onDismiss={() => setError("")} />
        </div>
      )}

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold text-white">Question</h3>
              <p className="text-sm text-slate-400">Topic: {activeTopic}</p>
            </div>
            <button
              onClick={() => generateQuestion()}
              disabled={loadingQuestion}
              className="rounded-xl bg-pink-500 px-5 py-3 text-sm font-semibold text-white transition hover:bg-pink-600 disabled:opacity-60"
            >
              {loadingQuestion ? "Generating..." : "Generate Question"}
            </button>
          </div>
          <div className="min-h-[180px] rounded-xl border border-slate-700 bg-slate-950/60 p-5">
            {loadingQuestion ? (
              <LoadingState label="Preparing the next question..." />
            ) : question ? (
              <p className="whitespace-pre-line text-lg leading-8 text-white">{question}</p>
            ) : (
              <p className="text-slate-400">No question yet. Click Generate Question or Start Auto Interview.</p>
            )}
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={() => speech.speak(question)}
              disabled={!question || speech.isSpeaking}
              className="rounded-xl bg-indigo-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-indigo-600 disabled:opacity-60"
            >
              {speech.isSpeaking ? "Speaking..." : "Speak Question"}
            </button>
            <button onClick={speech.stop} className="rounded-xl bg-slate-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-600">
              Stop Voice
            </button>
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <label htmlFor="interview-answer" className="text-xl font-bold text-white">Your Answer</label>
              <p className="text-sm text-slate-400">Speak or type your answer, then submit for evaluation.</p>
            </div>
            <span
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                mic.isListening ? "bg-red-950/50 text-red-300" : "bg-slate-800 text-slate-300"
              }`}
            >
              {mic.isListening ? "Listening..." : "Mic Idle"}
            </span>
          </div>
          <textarea
            id="interview-answer"
            value={answer}
            maxLength={20000}
            onChange={(e) => setAnswer(e.target.value)}
            className="min-h-[180px] w-full rounded-xl border border-slate-700 bg-slate-950/60 p-4 text-base leading-7 text-white outline-none"
            placeholder="Your answer will appear here..."
          />
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              onClick={() => {
                speech.stop();
                mic.start(answer);
              }}
              disabled={mic.isListening}
              className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-60"
            >
              Start Mic
            </button>
            <button onClick={mic.stop} className="rounded-xl bg-slate-700 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-600">
              Stop Mic
            </button>
            <button
              onClick={evaluateAnswer}
              disabled={loadingEvaluation}
              className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
            >
              {loadingEvaluation ? "Evaluating..." : "Evaluate Answer"}
            </button>
          </div>
        </div>
      </div>

      {result && (
        <div className="mt-6">
          <ResultCard result={result} />
        </div>
      )}

      {finalReport && (
        <div className="mt-8 rounded-2xl border border-emerald-400/30 bg-emerald-950/20 p-5">
          <h3 className="text-2xl font-bold text-white">Final Interview Report</h3>
          <div className="mt-4 grid gap-4 md:grid-cols-3">
            <StatCard label="Topic" value={finalReport.topic} valueClassName="text-base" />
            <StatCard
              label="Scored Rounds"
              value={finalReport.rounds}
              subtext={finalReport.skippedRounds ? `${finalReport.skippedRounds} round(s) could not be scored` : null}
              valueClassName="text-base"
            />
            <StatCard label="Average Score" value={formatScore(finalReport.averageScore)} valueClassName="text-base" />
          </div>
          <div className="mt-5 grid gap-4 md:grid-cols-2">
            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="font-semibold text-emerald-300">Strong Points</p>
              <p className="mt-2 text-sm leading-7 text-slate-200">{finalReport.strongPoints}</p>
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="font-semibold text-yellow-300">Weak Points</p>
              <p className="mt-2 text-sm leading-7 text-slate-200">{finalReport.weakPoints}</p>
            </div>
          </div>
          <div className="mt-5 rounded-xl border border-cyan-400/30 bg-cyan-950/20 p-4">
            <p className="font-semibold text-cyan-300">Final Recommendation</p>
            <p className="mt-2 text-sm leading-7 text-slate-200">{finalReport.recommendation}</p>
          </div>
        </div>
      )}

      <LocalHistoryTable
        title="Recent Interview History"
        items={history.items}
        onClear={history.clear}
        emptyTitle="No interview history yet"
        emptyMessage="Complete an interview and click Finish & Report to save it."
        columns={[
          { label: "Date", render: (item) => `${item.date} ${item.time}` },
          { label: "Topic", key: "topic", className: "font-semibold text-white" },
          { label: "Difficulty", key: "level" },
          { label: "Rounds", key: "rounds" },
          { label: "Avg Score", render: (item) => formatScore(item.averageScore), className: "font-bold text-white" },
          { label: "Recommendation", key: "recommendation" },
        ]}
      />
    </div>
  );
}
