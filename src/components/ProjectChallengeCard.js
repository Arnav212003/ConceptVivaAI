"use client";

import { useState } from "react";
import LocalHistoryTable from "@/components/LocalHistoryTable";
import ProjectFolderPicker, { readProjectFolder } from "@/components/project/ProjectFolderPicker";
import ProjectReview from "@/components/project/ProjectReview";
import ValueList from "@/components/project/ValueList";
import { EmptyState, ErrorBanner, LoadingState, StatCard } from "@/components/ui";
import useLocalHistory from "@/hooks/useLocalHistory";
import { apiPost } from "@/lib/api";
import { averageScore, formatScore } from "@/lib/scoring";

const CHALLENGE_SECTIONS = [
  ["Problem", "problem_statement"],
  ["Dataset / Table Schema", "dataset_columns"],
  ["Tasks", "tasks"],
  ["Evaluation Metrics", "evaluation_metrics"],
  ["Hints", "hints"],
  ["Submission Checklist", "submission_checklist"],
];

export default function ProjectChallengeCard() {
  const [domain, setDomain] = useState("Machine Learning");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("Beginner");
  const [challenge, setChallenge] = useState(null);
  const [challengeId, setChallengeId] = useState("");
  const [projectFiles, setProjectFiles] = useState([]);
  const [fileInfo, setFileInfo] = useState(null);
  const [fileError, setFileError] = useState("");
  const [review, setReview] = useState(null);
  const [loadingChallenge, setLoadingChallenge] = useState(false);
  const [loadingReview, setLoadingReview] = useState(false);
  const [error, setError] = useState("");
  const history = useLocalHistory("conceptviva_project_history");

  function resetChallenge() {
    setChallenge(null);
    setChallengeId("");
    setProjectFiles([]);
    setFileInfo(null);
    setFileError("");
    setReview(null);
    setError("");
  }

  async function handleFolder(event) {
    setProjectFiles([]);
    setFileInfo(null);
    setFileError("");
    setReview(null);
    if (!event.target.files?.length) return;
    try {
      const { files, info } = await readProjectFolder(event.target.files);
      setProjectFiles(files);
      setFileInfo(info);
    } catch (err) {
      setFileError(err.message);
    }
  }

  async function generateChallenge() {
    resetChallenge();
    setLoadingChallenge(true);
    const cleanTopic = topic.trim();
    try {
      const data = await apiPost("/api/project", {
        action: "generate",
        domain,
        difficulty,
        ...(cleanTopic ? { topic: cleanTopic } : { topic: "AI Selected Topic", auto_topic: true }),
      });
      setChallenge(data.challenge);
      setChallengeId(data.challenge_id || "");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingChallenge(false);
    }
  }

  async function evaluateSubmission() {
    if (!challengeId) {
      setError("Challenge ID missing. Generate a fresh project challenge before submitting.");
      return;
    }
    if (projectFiles.length === 0) {
      setError("Select your complete project source folder first.");
      return;
    }
    setLoadingReview(true);
    setReview(null);
    setError("");
    try {
      const data = await apiPost("/api/project", {
        action: "evaluate",
        challenge_id: challengeId,
        files: projectFiles,
        project_notes: "Full source-folder submission",
      });
      setReview(data);
      const now = new Date();
      history.add({
        date: now.toLocaleDateString(),
        time: now.toLocaleTimeString(),
        domain,
        topic: challenge?.topic || topic || "AI Selected Topic",
        difficulty,
        title: challenge?.project_title || "Project Challenge",
        score: typeof data.score === "number" ? data.score : null,
        verdict: data.verdict,
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoadingReview(false);
    }
  }

  return (
    <div className="mt-10 rounded-3xl border border-slate-700 bg-slate-950/70 p-5 shadow-2xl">
      <div className="mb-6 border-b border-slate-800 pb-5">
        <p className="text-sm font-semibold uppercase tracking-widest text-emerald-300">Project Challenge Mode</p>
        <h2 className="mt-2 text-3xl font-bold text-white">AI Hackathon-style Project Practice</h2>
        <p className="mt-1 text-base text-slate-400">
          Choose a domain and enter any topic. Leave the topic blank and a useful project topic is chosen for you.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        <StatCard label="Total Local Project Attempts" value={history.items.length} />
        <StatCard label="Local Average Score" value={formatScore(averageScore(history.items))} />
        <StatCard label="Current Topic" value={challenge?.topic || topic.trim() || "AI Selected Topic"} valueClassName="text-xl" />
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-4">
        <div>
          <label htmlFor="project-domain" className="mb-2 block text-sm text-slate-300">Domain</label>
          <select
            id="project-domain"
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
            <option>System Design</option>
          </select>
        </div>
        <div>
          <label htmlFor="project-topic" className="mb-2 block text-sm text-slate-300">Topic (optional)</label>
          <input
            id="project-topic"
            value={topic}
            maxLength={200}
            onChange={(event) => {
              setTopic(event.target.value);
              resetChallenge();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
            placeholder="Example: KNN, URL Shortener"
          />
        </div>
        <div>
          <label htmlFor="project-level" className="mb-2 block text-sm text-slate-300">Level</label>
          <select
            id="project-level"
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

      {error && (
        <div className="mb-5">
          <ErrorBanner message={error} onDismiss={() => setError("")} />
        </div>
      )}

      {loadingChallenge ? (
        <LoadingState label="Designing your project challenge..." />
      ) : challenge ? (
        <div className="grid gap-5 lg:grid-cols-2">
          <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <p className="text-sm font-semibold uppercase tracking-widest text-emerald-300">Verified Problem Statement</p>
            <h3 className="mt-2 text-2xl font-bold text-white">{challenge.project_title || "Project Challenge"}</h3>
            {challengeId && (
              <p className="mt-2 break-all rounded-lg border border-emerald-400/30 bg-emerald-950/20 px-3 py-2 text-xs text-emerald-200">
                Verified Challenge ID: {challengeId}
              </p>
            )}
            {challenge.generated_by === "fallback" && (
              <p className="mt-2 rounded-lg border border-amber-700/50 bg-amber-950/30 px-3 py-2 text-xs text-amber-200">
                The AI challenge writer is unavailable, so a generic template challenge is shown.
              </p>
            )}
            <div className="mt-4 space-y-5">
              {CHALLENGE_SECTIONS.map(([title, key]) => (
                <section key={key} className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                  <p className="font-semibold text-white">{title}</p>
                  <ValueList value={challenge[key]} />
                </section>
              ))}
            </div>
          </div>

          <div className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
            <h3 className="text-xl font-bold text-white">Submit Full Project Source Code</h3>
            <p className="mt-1 text-sm text-slate-400">
              Select your complete project folder. The source files are reviewed together so architecture,
              cross-file logic, bugs, missing requirements and security issues can be checked.
            </p>
            <ProjectFolderPicker files={projectFiles} info={fileInfo} error={fileError} onChange={handleFolder} />
            <button
              onClick={evaluateSubmission}
              disabled={loadingReview || !challengeId || projectFiles.length === 0}
              className="mt-4 rounded-xl bg-pink-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-pink-600 disabled:opacity-60"
            >
              {loadingReview ? "Reviewing Full Project..." : "Submit Full Project for AI Review"}
            </button>
            {loadingReview && <LoadingState label="Reviewing every file, this can take a minute..." />}
            {review && <ProjectReview review={review} />}
          </div>
        </div>
      ) : (
        <EmptyState
          title="No project challenge generated yet"
          message="Select a domain, optionally enter a topic, then click Generate Challenge."
        />
      )}

      <LocalHistoryTable
        title="Recent Project Challenge History"
        items={history.items}
        onClear={history.clear}
        emptyTitle="No project history yet"
        emptyMessage="Submit your first project to start tracking."
        columns={[
          { label: "Date", render: (item) => `${item.date} ${item.time}` },
          { label: "Project", key: "title", className: "font-semibold text-white" },
          { label: "Domain", key: "domain" },
          { label: "Topic", key: "topic" },
          { label: "Level", key: "difficulty" },
          { label: "Score", render: (item) => formatScore(item.score), className: "font-bold text-white" },
          { label: "Verdict", key: "verdict" },
        ]}
      />
    </div>
  );
}
