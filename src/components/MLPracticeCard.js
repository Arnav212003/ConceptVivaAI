"use client";

import { useEffect, useState } from "react";
import { apiFetchWithSessionRetry } from "@/utils/session";

export default function MLPracticeCard() {
  const [topic, setTopic] = useState("");
  const [activeTopic, setActiveTopic] = useState("AI Selected ML Topic");
  const [level, setLevel] = useState("Easy");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [loadingQuestion, setLoadingQuestion] = useState(false);
  const [loadingEvaluation, setLoadingEvaluation] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const saved = localStorage.getItem("conceptviva_ml_practice_history");

    if (saved) {
      setHistory(JSON.parse(saved));
    }
  }, []);

  function getTopicForRequest() {
    const cleanTopic = topic.trim();

    if (cleanTopic) {
      return cleanTopic;
    }

    return `
Machine Learning interview practice.

The user did not select a fixed topic.
You must choose one useful ML interview topic yourself from areas like:
- ML basics
- supervised learning
- unsupervised learning
- regression
- classification
- Linear Regression
- Logistic Regression
- KNN
- Decision Trees
- overfitting and underfitting
- bias variance tradeoff
- train test split
- feature scaling
- model evaluation metrics
- confusion matrix
- precision, recall, F1 score

Ask only one clear interview question.
Do not reveal the answer.
`;
  }

  function getTopicForDisplay() {
    const cleanTopic = topic.trim();

    if (cleanTopic) {
      return cleanTopic;
    }

    return "AI Selected ML Topic";
  }

  function resetCurrentAttempt() {
    setQuestion("");
    setAnswer("");
    setResult(null);
  }

  async function saveAttempt(resultData) {
    const now = new Date();

    const attempt = {
      id: Date.now(),
      date: now.toLocaleDateString(),
      time: now.toLocaleTimeString(),
      topic: activeTopic,
      level,
      question,
      score: resultData.score ?? 0,
      verdict: resultData.verdict || "PARTIAL",
    };

    const updated = [attempt, ...history].slice(0, 20);

    setHistory(updated);
    localStorage.setItem(
      "conceptviva_ml_practice_history",
      JSON.stringify(updated)
    );


  }

  function clearHistory() {
    setHistory([]);
    localStorage.removeItem("conceptviva_ml_practice_history");
  }

  async function generateQuestion() {
    setLoadingQuestion(true);
    setQuestion("");
    setAnswer("");
    setResult(null);

    const topicForRequest = getTopicForRequest();
    const topicForDisplay = getTopicForDisplay();

    setActiveTopic(topicForDisplay);

    try {
      const response = await apiFetchWithSessionRetry("/api/interview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "question",
          topic: topicForRequest,
          level,
        }),
      });

      const data = await response.json();

      setQuestion(
        data.question ||
          "Can you explain one important Machine Learning concept with an example?"
      );
    } catch (error) {
      setQuestion(
        "Can you explain one important Machine Learning concept with an example?"
      );
    }

    setLoadingQuestion(false);
  }

  async function evaluateAnswer() {
    if (!question.trim()) {
      alert("Please generate a question first.");
      return;
    }

    if (!answer.trim()) {
      alert("Please write your answer first.");
      return;
    }

    setLoadingEvaluation(true);
    setResult(null);

    const topicForEvaluation =
      activeTopic === "AI Selected ML Topic"
        ? getTopicForRequest()
        : activeTopic;

    try {
      const response = await apiFetchWithSessionRetry("/api/interview", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "evaluate",
          topic: topicForEvaluation,
          level,
          question,
          answer,
          mode: "practice",
          display_topic: activeTopic,
          save_attempt: true,
        }),
      });

      const data = await response.json();

      const resultData = {
        score: data.score ?? 0,
        verdict: data.verdict || "PARTIAL",
        feedback: data.feedback || "No feedback received.",
        missing_points:
          data.missing_points || "Important points are not available.",
        corrected_answer:
          data.corrected_answer || "Corrected answer not available.",
        improvement: data.improvement || "Improve answer structure.",
        follow_up_question:
          data.follow_up_question ||
          "Can you explain this ML concept with one real-world example?",
      };

      setResult(resultData);
      await saveAttempt(resultData);
    } catch (error) {
      const resultData = {
        score: 0,
        verdict: "WEAK",
        feedback: "Something went wrong while evaluating your answer.",
        missing_points: "Could not check missing points.",
        corrected_answer: "Backend connection issue. Try again.",
        improvement: "Check API route and Python backend.",
        follow_up_question:
          "Can you explain this ML concept with one simple example?",
      };

      setResult(resultData);
      await saveAttempt(resultData);
    }

    setLoadingEvaluation(false);
  }

  const totalAttempts = history.length;

  const averageScore =
    totalAttempts > 0
      ? (
          history.reduce((sum, item) => sum + Number(item.score || 0), 0) /
          totalAttempts
        ).toFixed(1)
      : "0.0";

  return (
    <div className="mt-10 rounded-3xl border border-slate-700 bg-slate-950/70 p-5 shadow-2xl">
      <div className="mb-6 border-b border-slate-800 pb-5">
        <p className="text-sm font-semibold uppercase tracking-widest text-cyan-300">
          Practice Mode
        </p>

        <h2 className="mt-2 text-3xl font-bold text-white">
          AI ML Question Practice
        </h2>

        <p className="mt-1 text-base text-slate-400">
          Leave the topic blank and AI will choose a Machine Learning topic
          automatically. If you type a topic, AI will ask from that topic only.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Total Local Attempts</p>
          <p className="mt-1 text-3xl font-bold text-white">{totalAttempts}</p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Local Average Score</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {averageScore}/10
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Current Topic</p>
          <p className="mt-1 text-xl font-bold text-white">
            {getTopicForDisplay()}
          </p>
        </div>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        <div>
          <label className="mb-2 block text-sm text-slate-300">
            Topic Optional
          </label>

          <input
            value={topic}
            onChange={(event) => {
              setTopic(event.target.value);
              resetCurrentAttempt();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
            placeholder="Leave blank and AI will choose an ML topic automatically"
          />

          <p className="mt-2 text-xs text-slate-500">
            Example: Logistic Regression, KNN, Overfitting, Evaluation Metrics
          </p>
        </div>

        <div>
          <label className="mb-2 block text-sm text-slate-300">
            Difficulty
          </label>

          <select
            value={level}
            onChange={(event) => {
              setLevel(event.target.value);
              resetCurrentAttempt();
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

      <div className="grid gap-5 lg:grid-cols-2">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-xl font-bold text-white">AI Question</h3>
              <p className="mt-1 text-sm text-slate-400">
                Topic: {activeTopic}
              </p>
            </div>

            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
              {level}
            </span>
          </div>

          <div className="mt-4 min-h-[240px] rounded-xl border border-slate-700 bg-slate-950/60 p-5">
            {question ? (
              <p className="whitespace-pre-line text-lg leading-8 text-white">
                {question}
              </p>
            ) : (
              <p className="text-slate-400">
                You can leave the topic blank. Click Generate AI Question and
                AI will ask a Machine Learning question automatically.
              </p>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
          <h3 className="text-xl font-bold text-white">Your Answer</h3>

          <textarea
            value={answer}
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
        <div className="mt-6 rounded-2xl border border-emerald-400/30 bg-emerald-950/20 p-5">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-400">Score</p>
              <p className="mt-1 text-3xl font-bold text-white">
                {result.score}/10
              </p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-400">Verdict</p>
              <p className="mt-1 text-2xl font-bold text-white">
                {result.verdict}
              </p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="text-sm text-slate-400">Topic</p>
              <p className="mt-1 text-xl font-bold text-white">
                {activeTopic}
              </p>
            </div>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="font-semibold text-emerald-300">Feedback</p>
              <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">
                {result.feedback}
              </p>
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
              <p className="font-semibold text-yellow-300">Missing Points</p>
              <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">
                {result.missing_points}
              </p>
            </div>
          </div>

          <div className="mt-5 rounded-xl border border-cyan-400/30 bg-cyan-950/20 p-4">
            <p className="font-semibold text-cyan-300">
              Better Interview-ready Answer
            </p>
            <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">
              {result.corrected_answer}
            </p>
          </div>

          <div className="mt-5 rounded-xl border border-pink-400/30 bg-pink-950/20 p-4">
            <p className="font-semibold text-pink-300">Follow-up Question</p>
            <p className="mt-2 text-sm leading-7 text-slate-200">
              {result.follow_up_question}
            </p>
          </div>
        </div>
      )}

      <div className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-white">
              Recent ML Practice History
            </h3>
            <p className="text-sm text-slate-400">
              This section shows browser history for quick review. Open
              Dashboard to view backend database records.
            </p>
          </div>

          <button
            onClick={clearHistory}
            disabled={history.length === 0}
            className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-50"
          >
            Clear Local History
          </button>
        </div>

        {history.length > 0 ? (
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-700">
                  <th className="py-3 pr-3">Date</th>
                  <th className="py-3 pr-3">Topic</th>
                  <th className="py-3 pr-3">Difficulty</th>
                  <th className="py-3 pr-3">Score</th>
                  <th className="py-3 pr-3">Verdict</th>
                </tr>
              </thead>

              <tbody>
                {history.map((item) => (
                  <tr key={item.id} className="border-b border-slate-800">
                    <td className="py-3 pr-3 text-slate-300">
                      {item.date} {item.time}
                    </td>
                    <td className="py-3 pr-3 font-semibold text-white">
                      {item.topic}
                    </td>
                    <td className="py-3 pr-3 text-slate-300">{item.level}</td>
                    <td className="py-3 pr-3 font-bold text-white">
                      {item.score}/10
                    </td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.verdict}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
            <p className="font-semibold text-white">
              No ML practice history yet
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Submit your first answer to start tracking.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}