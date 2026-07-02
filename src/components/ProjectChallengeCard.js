"use client";

import { useEffect, useState } from "react";

export default function ProjectChallengeCard() {
  const [domain, setDomain] = useState("Machine Learning");
  const [topic, setTopic] = useState("Linear Regression");
  const [difficulty, setDifficulty] = useState("Beginner");
  const [challenge, setChallenge] = useState(null);
  const [submission, setSubmission] = useState("");
  const [review, setReview] = useState(null);
  const [loadingChallenge, setLoadingChallenge] = useState(false);
  const [loadingReview, setLoadingReview] = useState(false);
  const [history, setHistory] = useState([]);

  useEffect(() => {
    const saved = localStorage.getItem("conceptviva_project_history");

    if (saved) {
      setHistory(JSON.parse(saved));
    }
  }, []);

  function saveProjectAttempt(reviewData) {
    const now = new Date();

    const attempt = {
      id: Date.now(),
      date: now.toLocaleDateString(),
      time: now.toLocaleTimeString(),
      domain,
      topic,
      difficulty,
      title: challenge?.project_title || "Project Challenge",
      score: reviewData.score ?? 0,
      verdict: reviewData.verdict || "PARTIAL",
    };

    const updated = [attempt, ...history].slice(0, 20);

    setHistory(updated);
    localStorage.setItem(
      "conceptviva_project_history",
      JSON.stringify(updated)
    );
  }

  function clearHistory() {
    setHistory([]);
    localStorage.removeItem("conceptviva_project_history");
  }

  function resetChallenge() {
    setChallenge(null);
    setSubmission("");
    setReview(null);
  }

  function renderList(value) {
    if (!value) return null;

    if (Array.isArray(value)) {
      return (
        <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-7 text-slate-200">
          {value.map((item, index) => {
            if (typeof item === "object") {
              return (
                <li key={index}>
                  {Object.entries(item)
                    .map(([key, val]) => `${key}: ${val}`)
                    .join(" | ")}
                </li>
              );
            }

            return <li key={index}>{item}</li>;
          })}
        </ul>
      );
    }

    return (
      <p className="mt-2 whitespace-pre-line text-sm leading-7 text-slate-200">
        {value}
      </p>
    );
  }

  async function generateChallenge() {
    setLoadingChallenge(true);
    resetChallenge();

    try {
      const response = await fetch("/api/project", {
        method: "POST",
        body: JSON.stringify({
          action: "generate",
          domain,
          topic,
          difficulty,
        }),
      });

      const data = await response.json();

      setChallenge(data.challenge || data);
    } catch (error) {
      setChallenge({
        project_title: `${topic} Project Challenge`,
        problem_statement:
          "Backend connection failed. Please check project API route and FastAPI backend.",
        dataset_columns: [],
        tasks: [],
        evaluation_metrics: [],
        hints: [],
        submission_checklist: [],
      });
    }

    setLoadingChallenge(false);
  }

  async function evaluateSubmission() {
    if (!challenge) {
      alert("Please generate a project challenge first.");
      return;
    }

    if (!submission.trim()) {
      alert("Please write your approach/code/report first.");
      return;
    }

    setLoadingReview(true);
    setReview(null);

    try {
      const response = await fetch("/api/project", {
        method: "POST",
        body: JSON.stringify({
          action: "evaluate",
          domain,
          topic,
          difficulty,
          challenge,
          submission,
        }),
      });

      const data = await response.json();

      const reviewData = {
        score: data.score ?? 0,
        verdict: data.verdict || "PARTIAL",
        feedback: data.feedback || "No feedback received.",
        missing_points: data.missing_points || "Missing points not available.",
        improved_approach:
          data.improved_approach || "Improved approach not available.",
        next_steps: data.next_steps || "Next steps not available.",
        suggested_resources: data.suggested_resources || [],
      };

      setReview(reviewData);
      saveProjectAttempt(reviewData);
    } catch (error) {
      const reviewData = {
        score: 0,
        verdict: "WEAK",
        feedback: "Something went wrong while evaluating your project.",
        missing_points: "Could not evaluate missing points.",
        improved_approach: "Check backend project endpoint.",
        next_steps: "Fix API route and try again.",
        suggested_resources: [],
      };

      setReview(reviewData);
      saveProjectAttempt(reviewData);
    }

    setLoadingReview(false);
  }

  const totalProjects = history.length;

  const averageScore =
    totalProjects > 0
      ? (
          history.reduce((sum, item) => sum + Number(item.score || 0), 0) /
          totalProjects
        ).toFixed(1)
      : "0.0";

  return (
    <div className="mt-10 rounded-3xl border border-slate-700 bg-slate-950/70 p-5 shadow-2xl">
      <div className="mb-6 border-b border-slate-800 pb-5">
        <p className="text-sm font-semibold uppercase tracking-widest text-emerald-300">
          Project Challenge Mode
        </p>

        <h2 className="mt-2 text-3xl font-bold text-white">
          AI Hackathon-style Project Practice
        </h2>

        <p className="mt-1 text-base text-slate-400">
          Choose a topic and let AI generate a project problem statement,
          dataset schema, tasks, metrics, and final review.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Total Project Attempts</p>
          <p className="mt-1 text-3xl font-bold text-white">{totalProjects}</p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Average Score</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {averageScore}/10
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Current Topic</p>
          <p className="mt-1 text-xl font-bold text-white">{topic}</p>
        </div>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-4">
        <div>
          <label className="mb-2 block text-sm text-slate-300">Domain</label>

          <select
            value={domain}
            onChange={(event) => {
              setDomain(event.target.value);
              resetChallenge();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
          >
            <option>Machine Learning</option>
            <option>Data Analytics</option>
            <option>DSA</option>
          </select>
        </div>

        <div>
          <label className="mb-2 block text-sm text-slate-300">Topic</label>

          <input
            value={topic}
            onChange={(event) => {
              setTopic(event.target.value);
              resetChallenge();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
            placeholder="Example: Linear Regression"
          />
        </div>

        <div>
          <label className="mb-2 block text-sm text-slate-300">Level</label>

          <select
            value={difficulty}
            onChange={(event) => {
              setDifficulty(event.target.value);
              resetChallenge();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
          >
            <option>Beginner</option>
            <option>Intermediate</option>
            <option>Advanced</option>
          </select>
        </div>

        <div className="flex items-end">
          <button
            onClick={generateChallenge}
            disabled={loadingChallenge}
            className="w-full rounded-xl bg-emerald-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
          >
            {loadingChallenge ? "Generating..." : "Generate Challenge"}
          </button>
        </div>
      </div>

      {challenge ? (
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <div className="mb-4">
              <p className="text-sm font-semibold uppercase tracking-widest text-emerald-300">
                Problem Statement
              </p>

              <h3 className="mt-2 text-2xl font-bold text-white">
                {challenge.project_title || `${topic} Project Challenge`}
              </h3>
            </div>

            <div className="space-y-5">
              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">Problem</p>
                {renderList(challenge.problem_statement)}
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">Dataset / Table Schema</p>
                {renderList(challenge.dataset_columns)}
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">Tasks</p>
                {renderList(challenge.tasks)}
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">Evaluation Metrics</p>
                {renderList(challenge.evaluation_metrics)}
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">Hints</p>
                {renderList(challenge.hints)}
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">Submission Checklist</p>
                {renderList(challenge.submission_checklist)}
              </section>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <h3 className="text-xl font-bold text-white">
              Submit Your Project Approach
            </h3>

            <p className="mt-1 text-sm text-slate-400">
              Paste your approach, Python code, model steps, evaluation result,
              or explanation here.
            </p>

            <textarea
              value={submission}
              onChange={(event) => setSubmission(event.target.value)}
              className="mt-4 min-h-[420px] w-full rounded-xl border border-slate-700 bg-slate-950/60 p-4 font-mono text-sm leading-7 text-white outline-none"
              placeholder={`Example:
1. I will load the dataset.
2. I will clean missing values.
3. I will split train/test.
4. I will train Linear Regression.
5. I will evaluate using MAE, MSE, and R2 Score.

Paste your code or approach here...`}
            />

            <button
              onClick={evaluateSubmission}
              disabled={loadingReview}
              className="mt-4 rounded-xl bg-pink-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-pink-600 disabled:opacity-60"
            >
              {loadingReview ? "Reviewing..." : "Submit for AI Review"}
            </button>

            {review && (
              <div className="mt-6 rounded-2xl border border-pink-400/30 bg-pink-950/20 p-5">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                    <p className="text-sm text-slate-400">Score</p>
                    <p className="mt-1 text-3xl font-bold text-white">
                      {review.score}/10
                    </p>
                  </div>

                  <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                    <p className="text-sm text-slate-400">Verdict</p>
                    <p className="mt-1 text-2xl font-bold text-white">
                      {review.verdict}
                    </p>
                  </div>
                </div>

                <div className="mt-5 space-y-4">
                  <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                    <p className="font-semibold text-emerald-300">Feedback</p>
                    {renderList(review.feedback)}
                  </section>

                  <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                    <p className="font-semibold text-yellow-300">
                      Missing Points
                    </p>
                    {renderList(review.missing_points)}
                  </section>

                  <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                    <p className="font-semibold text-cyan-300">
                      Improved Approach
                    </p>
                    {renderList(review.improved_approach)}
                  </section>

                  <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                    <p className="font-semibold text-pink-300">Next Steps</p>
                    {renderList(review.next_steps)}
                  </section>
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-900/60 p-8 text-center">
          <p className="text-lg font-semibold text-white">
            No project challenge generated yet
          </p>
          <p className="mt-2 text-sm text-slate-400">
            Select domain, topic, and level, then click Generate Challenge.
          </p>
        </div>
      )}

      <div className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-white">
              Recent Project Challenge History
            </h3>
            <p className="text-sm text-slate-400">
              Your latest project reviews are saved in this browser.
            </p>
          </div>

          <button
            onClick={clearHistory}
            disabled={history.length === 0}
            className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-50"
          >
            Clear History
          </button>
        </div>

        {history.length > 0 ? (
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-700">
                  <th className="py-3 pr-3">Date</th>
                  <th className="py-3 pr-3">Project</th>
                  <th className="py-3 pr-3">Topic</th>
                  <th className="py-3 pr-3">Level</th>
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
                      {item.title}
                    </td>
                    <td className="py-3 pr-3 text-slate-300">{item.topic}</td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.difficulty}
                    </td>
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
              No project history yet
            </p>
            <p className="mt-2 text-sm text-slate-400">
              Submit your first project approach to start tracking.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}