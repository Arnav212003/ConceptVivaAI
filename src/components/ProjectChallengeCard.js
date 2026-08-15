"use client";

import { useEffect, useState } from "react";
import { apiFetchWithSessionRetry } from "@/utils/session";

const MAX_PROJECT_SOURCE_CHARS = 2_200_000;
const MAX_PROJECT_FILES = 250;
const MAX_SINGLE_FILE_BYTES = 300_000;

const IGNORED_PROJECT_DIRS = new Set([
  "node_modules", ".git", ".next", "dist", "build", "coverage",
  "venv", ".venv", "env", "__pycache__", ".idea", ".vscode",
  "target", "out", ".pytest_cache", ".mypy_cache",
]);

const SOURCE_EXTENSIONS = new Set([
  ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".cpp", ".cc", ".c",
  ".h", ".hpp", ".cs", ".go", ".rs", ".php", ".rb", ".swift", ".kt",
  ".kts", ".scala", ".sql", ".html", ".css", ".scss", ".sass", ".less",
  ".vue", ".svelte", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
  ".conf", ".xml", ".md", ".txt", ".sh", ".bash", ".ps1", ".bat",
  ".gradle", ".properties", ".graphql", ".gql", ".proto", ".env.example",
]);

const SOURCE_FILENAMES = new Set([
  "dockerfile", "makefile", "procfile", "requirements.txt", "package.json",
  "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "pyproject.toml",
  "poetry.lock", "pom.xml", "build.gradle", "settings.gradle", "readme.md",
]);

export default function ProjectChallengeCard() {
  const [domain, setDomain] = useState("Machine Learning");
  const [topic, setTopic] = useState("");
  const [difficulty, setDifficulty] = useState("Beginner");
  const [challenge, setChallenge] = useState(null);
  const [challengeId, setChallengeId] = useState("");
  const [projectFiles, setProjectFiles] = useState([]);
  const [projectFileInfo, setProjectFileInfo] = useState(null);
  const [projectFileError, setProjectFileError] = useState("");
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

  function getTopicForRequest() {
    const cleanTopic = topic.trim();

    if (cleanTopic) {
      return cleanTopic;
    }

    if (domain === "Machine Learning") {
      return "AI should choose one useful Machine Learning project topic such as KNN, clustering, regression, classification, recommendation system, or model evaluation.";
    }

    if (domain === "Data Analytics") {
      return "AI should choose one useful Data Analytics project topic such as sales dashboard, customer analysis, churn analysis, SQL analytics, or business KPI analysis.";
    }

    if (domain === "DSA") {
      return "AI should choose one useful DSA project topic such as path finding visualizer, sorting visualizer, graph traversal, stack queue simulator, or algorithm analyzer.";
    }

    if (domain === "System Design") {
      return "AI should choose one useful System Design topic such as URL shortener, Instagram news feed, notification system, rate limiter, chat system, or file storage system.";
    }

    return "AI selected project topic";
  }

  function getTopicForDisplay() {
    const cleanTopic = topic.trim();

    if (cleanTopic) {
      return cleanTopic;
    }

    return "AI Selected Topic";
  }

  function getChallengeTopicForDisplay() {
    return challenge?.topic || getTopicForDisplay();
  }

  function getChallengeTitle() {
    return challenge?.project_title || "Project Challenge";
  }

  async function saveProjectAttempt(reviewData) {
    const now = new Date();

    const attempt = {
      id: Date.now(),
      date: now.toLocaleDateString(),
      time: now.toLocaleTimeString(),
      domain,
      topic: getChallengeTopicForDisplay(),
      difficulty,
      title: getChallengeTitle(),
      challengeId: challengeId || "N/A",
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
    setChallengeId("");
    setProjectFiles([]);
    setProjectFileInfo(null);
    setProjectFileError("");
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
                    .map(([key, val]) =>
                      `${key}: ${
                        typeof val === "object" ? JSON.stringify(val) : val
                      }`
                    )
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


  function isReadableProjectFile(file) {
    const relativePath = file.webkitRelativePath || file.name;
    const parts = relativePath.split("/").map((part) => part.toLowerCase());

    if (parts.some((part) => IGNORED_PROJECT_DIRS.has(part))) {
      return false;
    }

    const lowerName = file.name.toLowerCase();
    if (lowerName === ".env" || lowerName.startsWith(".env.")) {
      return lowerName === ".env.example";
    }

    if (SOURCE_FILENAMES.has(lowerName)) return true;

    const dotIndex = lowerName.lastIndexOf(".");
    const extension = dotIndex >= 0 ? lowerName.slice(dotIndex) : "";
    return SOURCE_EXTENSIONS.has(extension);
  }

  async function handleProjectFolder(event) {
    const selected = Array.from(event.target.files || []);
    setProjectFiles([]);
    setProjectFileInfo(null);
    setProjectFileError("");
    setReview(null);

    if (!selected.length) return;

    const readable = selected
      .filter(isReadableProjectFile)
      .filter((file) => file.size <= MAX_SINGLE_FILE_BYTES)
      .slice(0, MAX_PROJECT_FILES);

    if (!readable.length) {
      setProjectFileError(
        "No readable source files found. Select the project source folder, not a build/dependency folder."
      );
      return;
    }

    const loaded = [];
    let totalChars = 0;

    for (const file of readable) {
      const content = await file.text();
      if (totalChars + content.length > MAX_PROJECT_SOURCE_CHARS) {
        setProjectFileError(
          "Project source is too large for one AI review. Remove generated/data files and keep the complete application source under 2.2M characters."
        );
        setProjectFiles([]);
        return;
      }

      loaded.push({
        path: file.webkitRelativePath || file.name,
        content,
      });
      totalChars += content.length;
    }

    setProjectFiles(loaded);
    setProjectFileInfo({
      files: loaded.length,
      totalChars,
      skipped: selected.length - loaded.length,
    });
  }

  async function generateChallenge() {
    setLoadingChallenge(true);
    resetChallenge();

    const topicForRequest = getTopicForRequest();

    try {
      const response = await apiFetchWithSessionRetry("/api/project", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "generate",
          domain,
          topic: topicForRequest,
          difficulty,
        }),
      });

      const data = await response.json();

      const generatedChallenge = data.challenge || data;
      const generatedChallengeId =
        data.challenge_id || generatedChallenge.challenge_id || "";

      setChallenge({
        ...generatedChallenge,
        challenge_id: generatedChallengeId,
      });

      setChallengeId(generatedChallengeId);
    } catch (error) {
      setChallenge({
        project_title: `${getTopicForDisplay()} Project Challenge`,
        problem_statement:
          "Backend connection failed. Please check project API route and FastAPI backend.",
        dataset_columns: [],
        tasks: [],
        evaluation_metrics: [],
        hints: [],
        submission_checklist: [],
      });

      setChallengeId("");
    }

    setLoadingChallenge(false);
  }

  async function evaluateSubmission() {
    if (!challenge) {
      alert("Please generate a project challenge first.");
      return;
    }

    if (!challengeId) {
      alert(
        "Challenge ID missing. Please generate a fresh project challenge before submitting."
      );
      return;
    }

    if (projectFiles.length === 0) {
      alert("Please select your complete project source folder first.");
      return;
    }

    setLoadingReview(true);
    setReview(null);

    try {
      const response = await apiFetchWithSessionRetry("/api/project", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "evaluate",
          challenge_id: challengeId,
          domain,
          topic: getChallengeTopicForDisplay(),
          difficulty,
          files: projectFiles,
          project_notes: "Full source-folder submission",
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Project review failed.");
      }

      const reviewData = {
        score: data.score ?? 0,
        verdict: data.verdict || "PARTIAL",
        feedback: data.feedback || "No feedback received.",
        missing_points: data.missing_points || "Missing points not available.",
        improved_approach:
          data.improved_approach || "Improved approach not available.",
        next_steps: data.next_steps || "Next steps not available.",
        suggested_resources: data.suggested_resources || [],
        architecture_review:
          data.architecture_review || "Architecture review not available.",
        file_findings: data.file_findings || [],
        bugs: data.bugs || [],
        security_issues: data.security_issues || [],
        missing_requirements: data.missing_requirements || [],
        files_reviewed: data.files_reviewed ?? projectFiles.length,
      };

      setReview(reviewData);
      await saveProjectAttempt(reviewData);
    } catch (error) {
      // even when the backend call itself fails, we still record the attempt
      // (matching how DSAPracticeCard and InterviewCard handle their errors)
      // so a failed submission doesn't just silently disappear
      const reviewData = {
        score: 0,
        verdict: "WEAK",
        feedback:
          "Something went wrong while evaluating your project. Please check backend project endpoint and challenge_id verification.",
        missing_points: "Could not evaluate missing points.",
        improved_approach: "Check backend project endpoint.",
        next_steps: "Fix API route and try again.",
        suggested_resources: [],
        architecture_review: "Could not review architecture.",
        file_findings: [],
        bugs: [],
        security_issues: [],
        missing_requirements: [],
        files_reviewed: 0,
      };

      setReview(reviewData);
      await saveProjectAttempt(reviewData);
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
          Choose a domain and enter any topic. Leave topic blank and AI will
          select a useful project topic automatically.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Total Local Project Attempts</p>
          <p className="mt-1 text-3xl font-bold text-white">{totalProjects}</p>
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
            {challenge ? getChallengeTopicForDisplay() : getTopicForDisplay()}
          </p>
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
            <option>System Design</option>
          </select>
        </div>

        <div>
          <label className="mb-2 block text-sm text-slate-300">
            Topic Optional
          </label>

          <input
            value={topic}
            onChange={(event) => {
              setTopic(event.target.value);
              resetChallenge();
            }}
            className="w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-base text-white outline-none"
            placeholder="Example: KNN, Clustering, URL Shortener, Instagram News Feed"
          />

          <p className="mt-2 text-xs text-slate-500">
            Leave blank and AI will choose a project topic automatically.
          </p>
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
                Verified Problem Statement
              </p>

              <h3 className="mt-2 text-2xl font-bold text-white">
                {getChallengeTitle()}
              </h3>

              {challengeId ? (
                <p className="mt-2 rounded-lg border border-emerald-400/30 bg-emerald-950/20 px-3 py-2 text-xs text-emerald-200">
                  Verified Challenge ID: {challengeId}
                </p>
              ) : (
                <p className="mt-2 rounded-lg border border-red-400/30 bg-red-950/20 px-3 py-2 text-xs text-red-200">
                  Challenge ID missing. Generate a fresh challenge before
                  submitting.
                </p>
              )}
            </div>

            <div className="space-y-5">
              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">Problem</p>
                {renderList(challenge.problem_statement)}
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                <p className="font-semibold text-white">
                  Dataset / Table Schema
                </p>
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
              Submit Full Project Source Code
            </h3>

            <p className="mt-1 text-sm text-slate-400">
              Select your complete project folder. ConceptVivaAI reads the
              source files together so Gemini can review architecture,
              cross-file logic, bugs, missing requirements, and security issues.
            </p>

            <div className="mt-4 rounded-2xl border border-dashed border-emerald-400/40 bg-emerald-950/10 p-5">
              <label className="block text-sm font-semibold text-emerald-200">
                Full Project Folder
              </label>
              <input
                type="file"
                multiple
                webkitdirectory=""
                directory=""
                onChange={handleProjectFolder}
                className="mt-3 block w-full text-sm text-slate-300 file:mr-4 file:rounded-lg file:border-0 file:bg-emerald-500 file:px-4 file:py-2 file:font-semibold file:text-white hover:file:bg-emerald-600"
              />
              <p className="mt-3 text-xs leading-5 text-slate-400">
                Dependencies/build output such as node_modules, .git, .next,
                venv, dist and binary files are ignored automatically. Secret
                .env files are never included.
              </p>

              {projectFileInfo && (
                <div className="mt-4 rounded-xl border border-emerald-400/30 bg-slate-950/50 p-3 text-sm text-emerald-100">
                  Ready for full review: <strong>{projectFileInfo.files}</strong>{" "}
                  source files · {projectFileInfo.totalChars.toLocaleString()}
                  {" "}characters
                  {projectFileInfo.skipped > 0
                    ? ` · ${projectFileInfo.skipped} dependency/binary/large files skipped`
                    : ""}
                </div>
              )}

              {projectFileError && (
                <p className="mt-4 rounded-xl border border-red-400/30 bg-red-950/20 p-3 text-sm text-red-200">
                  {projectFileError}
                </p>
              )}
            </div>

            {projectFiles.length > 0 && (
              <div className="mt-4 max-h-48 overflow-y-auto rounded-xl border border-slate-700 bg-slate-950/50 p-3">
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Included source files
                </p>
                {projectFiles.map((file) => (
                  <p key={file.path} className="truncate py-1 font-mono text-xs text-slate-300">
                    {file.path}
                  </p>
                ))}
              </div>
            )}

            <button
              onClick={evaluateSubmission}
              disabled={loadingReview || !challengeId || projectFiles.length === 0}
              className="mt-4 rounded-xl bg-pink-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-pink-600 disabled:opacity-60"
            >
              {loadingReview ? "Reviewing Full Project..." : "Submit Full Project for AI Review"}
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
                    <p className="font-semibold text-blue-300">
                      Architecture Review
                    </p>
                    {renderList(review.architecture_review)}
                  </section>

                  {review.bugs?.length > 0 && (
                    <section className="rounded-xl border border-red-400/30 bg-red-950/10 p-4">
                      <p className="font-semibold text-red-300">Code Bugs</p>
                      {renderList(review.bugs)}
                    </section>
                  )}

                  {review.file_findings?.length > 0 && (
                    <section className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                      <p className="font-semibold text-violet-300">
                        File-by-file Findings ({review.files_reviewed} reviewed)
                      </p>
                      {renderList(review.file_findings)}
                    </section>
                  )}

                  {review.security_issues?.length > 0 && (
                    <section className="rounded-xl border border-orange-400/30 bg-orange-950/10 p-4">
                      <p className="font-semibold text-orange-300">
                        Security Findings
                      </p>
                      {renderList(review.security_issues)}
                    </section>
                  )}

                  {review.missing_requirements?.length > 0 && (
                    <section className="rounded-xl border border-yellow-400/30 bg-yellow-950/10 p-4">
                      <p className="font-semibold text-yellow-300">
                        Missing Project Requirements
                      </p>
                      {renderList(review.missing_requirements)}
                    </section>
                  )}

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
            Select domain, optionally enter a topic, then click Generate
            Challenge.
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
                  <th className="py-3 pr-3">Project</th>
                  <th className="py-3 pr-3">Domain</th>
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
                    <td className="py-3 pr-3 text-slate-300">
                      {item.domain}
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
            <p className="font-semibold text-white">No project history yet</p>
            <p className="mt-2 text-sm text-slate-400">
              Submit your first project approach to start tracking.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
