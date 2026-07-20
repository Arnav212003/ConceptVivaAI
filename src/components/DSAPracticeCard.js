"use client";

import { useState } from "react";
import Link from "next/link";
import Editor from "@monaco-editor/react";
import {
  apiFetchWithSessionRetry,
  ensureConceptVivaSession,
} from "@/utils/session";

export default function DSAPracticeCard() {
  const [topic, setTopic] = useState("Arrays");
  const [difficulty, setDifficulty] = useState("Easy");
  const [problem, setProblem] = useState("");
  const [problemData, setProblemData] = useState(null);
  const [solution, setSolution] = useState("");
  const [runResult, setRunResult] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [loadingProblem, setLoadingProblem] = useState(false);
  const [loadingRun, setLoadingRun] = useState(false);
  const [loadingFeedback, setLoadingFeedback] = useState(false);
  const [activeTab, setActiveTab] = useState("code");

  const limitedExecutionTopics = [
    "Linked List",
    "Queue",
    "Trees",
    "Graphs",
    "Dynamic Programming",
  ];

  function isLimitedExecutionTopic() {
    return limitedExecutionTopics.includes(topic);
  }

  function getDefaultStarterCode() {
    return `class Solution:
    def solve(self):
        # Write your code here
        pass`;
  }

  function getStarterCode() {
    return problemData?.starter_code || getDefaultStarterCode();
  }

  function getProblemName(problemText) {
    if (problemData?.title) {
      return problemData.title;
    }

    const titleLine = problemText
      .split("\n")
      .find(
        (line) =>
          line.trim().startsWith("Problem:") ||
          line.trim().startsWith("Question Title:")
      );

    if (!titleLine) return "DSA Problem";

    return titleLine
      .replace("Problem:", "")
      .replace("Question Title:", "")
      .trim();
  }

  async function saveDsaAttempt(resultData) {
    const today = new Date();

    const attempt = {
      id: Date.now(),
      date: today.toLocaleDateString(),
      time: today.toLocaleTimeString(),
      mode: "Practice",
      topic,
      difficulty,
      problemName: getProblemName(problem),
      score: resultData.score ?? 0,
      status:
        Number(resultData.score ?? 0) >= 7 ? "Good" : "Needs Improvement",
    };

    try {
      const savedHistory = localStorage.getItem("conceptviva_dsa_history");
      const history = savedHistory ? JSON.parse(savedHistory) : [];
      const updatedHistory = [attempt, ...history].slice(0, 20);
      localStorage.setItem(
        "conceptviva_dsa_history",
        JSON.stringify(updatedHistory)
      );
    } catch (error) {
      console.error("Local history update failed:", error);
    }

    try {
      const session = await ensureConceptVivaSession();

      await apiFetchWithSessionRetry("/api/dsa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "save",
          session_id: session.sessionId,
          mode: "Practice",
          topic,
          difficulty,
          problem_name: getProblemName(problem),
          problem,
          solution,
          score: resultData.score ?? 0,
          status:
            Number(resultData.score ?? 0) >= 7
              ? "Good"
              : "Needs Improvement",
          feedback: resultData.feedback || "",
        }),
      });
    } catch (error) {
      console.error("DSA attempt backend save failed:", error);
    }
  }

  function resetWorkspace() {
    setProblem("");
    setProblemData(null);
    setSolution("");
    setRunResult(null);
    setFeedback(null);
    setActiveTab("code");
  }

  function handleTopicChange(value) {
    setTopic(value);
    resetWorkspace();
  }

  function handleDifficultyChange(value) {
    setDifficulty(value);
    resetWorkspace();
  }

  async function generatePracticeProblem() {
    setLoadingProblem(true);
    resetWorkspace();

    try {
      const response = await apiFetchWithSessionRetry("/api/dsa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "generate",
          topic,
          difficulty,
        }),
      });

      const data = await response.json();

      if (data.problem || data.problem_json) {
        setProblem(data.problem || "");
        setProblemData(data.problem_json || null);
        setSolution(
          data.problem_json?.starter_code ||
            data.starter_code ||
            getDefaultStarterCode()
        );
      } else {
        setProblem("DSA problem generation failed. Please check backend.");
        setSolution("");
      }
    } catch (error) {
      setProblem("Something went wrong while generating the DSA problem.");
      setSolution("");
    }

    setLoadingProblem(false);
  }

  async function runCode() {
    if (!problem.trim()) {
      alert("Please generate a problem first.");
      return;
    }

    if (!solution.trim()) {
      alert("Please write your code first.");
      return;
    }

    setLoadingRun(true);
    setRunResult(null);

    try {
      const response = await apiFetchWithSessionRetry("/api/dsa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "evaluate",
          topic,
          difficulty,
          problem,
          solution,
        }),
      });

      const data = await response.json();

      setRunResult({
        score: data.score ?? 0,
        test_cases: Array.isArray(data.test_cases) ? data.test_cases : [],
      });
      setActiveTab("testcase");
    } catch (error) {
      setRunResult({
        score: 0,
        test_cases: [],
        error: "Something went wrong while running your code.",
      });
      setActiveTab("testcase");
    }

    setLoadingRun(false);
  }

  async function evaluateSolution() {
    if (!problem.trim()) {
      alert("Please generate a problem first.");
      return;
    }

    if (!solution.trim()) {
      alert("Please write your code first.");
      return;
    }

    setLoadingFeedback(true);
    setFeedback(null);

    try {
      const response = await apiFetchWithSessionRetry("/api/dsa", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          action: "evaluate",
          topic,
          difficulty,
          problem,
          solution,
        }),
      });

      const data = await response.json();

      const resultData = {
        score: data.score ?? 0,
        feedback: data.feedback || "No feedback received from AI.",
        optimized_approach:
          data.optimized_approach || "No optimized approach received.",
        optimized_code: data.optimized_code || "Optimized code not available.",
        explanation: data.explanation || "Explanation not available.",
        time_complexity: data.time_complexity || "N/A",
        space_complexity: data.space_complexity || "N/A",
        test_cases: Array.isArray(data.test_cases) ? data.test_cases : [],
      };

      setFeedback(resultData);
      setRunResult({
        score: resultData.score,
        test_cases: resultData.test_cases,
      });
      await saveDsaAttempt(resultData);
      setActiveTab("result");
    } catch (error) {
      const resultData = {
        score: 0,
        feedback: "Something went wrong while evaluating your solution.",
        optimized_approach:
          "Check the DSA API route and Python backend connection.",
        optimized_code: "Optimized code not available.",
        explanation: "Explanation not available.",
        time_complexity: "N/A",
        space_complexity: "N/A",
        test_cases: [],
      };

      setFeedback(resultData);
      await saveDsaAttempt(resultData);
      setActiveTab("result");
    }

    setLoadingFeedback(false);
  }

  function getDifficultyColor(value = difficulty) {
    if (value === "Easy") return "text-emerald-300";
    if (value === "Medium") return "text-yellow-300";
    if (value === "Hard") return "text-red-300";
    return "text-sky-300";
  }

  function getDifficultyBadge(value) {
    if (value === "Easy") return "bg-emerald-950/50 text-emerald-300";
    if (value === "Medium") return "bg-yellow-950/50 text-yellow-300";
    if (value === "Hard") return "bg-red-950/50 text-red-300";
    return "bg-sky-950/50 text-sky-300";
  }

  function getDifficultyBorder(value = difficulty) {
    if (value === "Easy") return "border-l-emerald-400";
    if (value === "Medium") return "border-l-yellow-400";
    if (value === "Hard") return "border-l-red-400";
    return "border-l-sky-400";
  }

  function getStatusColor(status) {
    const value = String(status || "").toLowerCase();

    if (value.includes("pass")) {
      return "text-emerald-300 bg-emerald-950/40";
    }

    if (value.includes("fail")) {
      return "text-red-300 bg-red-950/40";
    }

    return "text-yellow-300 bg-yellow-950/40";
  }

  function handleEditorMount(editor, monaco) {
    monaco.editor.defineTheme("conceptviva-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [
        { token: "", foreground: "E5E7EB", background: "0B1020" },
        { token: "comment", foreground: "94A3B8" },
        { token: "keyword", foreground: "C084FC" },
        { token: "number", foreground: "FBBF24" },
        { token: "string", foreground: "86EFAC" },
      ],
      colors: {
        "editor.background": "#0B1020",
        "editor.foreground": "#E5E7EB",
        "editorLineNumber.foreground": "#64748B",
        "editorCursor.foreground": "#FFFFFF",
        "editor.selectionBackground": "#334155",
        "editorIndentGuide.background": "#334155",
        "editorIndentGuide.activeBackground": "#64748B",
      },
    });

    monaco.editor.setTheme("conceptviva-dark");
  }

  function renderLeetCodeProblem() {
    const examples = Array.isArray(problemData.examples)
      ? problemData.examples
      : [];

    const constraints = Array.isArray(problemData.constraints)
      ? problemData.constraints
      : [];

    return (
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <h3 className="text-2xl font-bold text-white">
            {problemData.title}
          </h3>

          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${getDifficultyBadge(
              problemData.difficulty
            )}`}
          >
            {problemData.difficulty}
          </span>
        </div>

        <div className="mt-3 flex flex-wrap gap-2">
          {problemData.topic && (
            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
              {problemData.topic}
            </span>
          )}

          {problemData.pattern && (
            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
              {problemData.pattern}
            </span>
          )}
        </div>

        <div className="mt-5 whitespace-pre-line text-[14px] leading-7 text-slate-100">
          {problemData.description}
        </div>

        {examples.map((example, index) => (
          <div key={index} className="mt-5">
            <p className="font-semibold text-white">Example {index + 1}:</p>

            <div className="mt-2 rounded-xl border border-slate-700 bg-slate-950 p-4 font-mono text-[13px] leading-6">
              {typeof example === "object" ? (
                <>
                  <p>
                    <span className="font-semibold text-slate-400">
                      Input:{" "}
                    </span>
                    <span className="text-slate-100">{example.input}</span>
                  </p>

                  <p className="mt-1">
                    <span className="font-semibold text-slate-400">
                      Output:{" "}
                    </span>
                    <span className="text-slate-100">{example.output}</span>
                  </p>

                  {example.explanation && (
                    <p className="mt-1">
                      <span className="font-semibold text-slate-400">
                        Explanation:{" "}
                      </span>
                      <span className="text-slate-300">
                        {example.explanation}
                      </span>
                    </p>
                  )}
                </>
              ) : (
                <p className="text-slate-100">{String(example)}</p>
              )}
            </div>
          </div>
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

  function renderResultBanner(testCases) {
    if (!Array.isArray(testCases) || testCases.length === 0) return null;

    const passedCount = testCases.filter((item) =>
      String(item.status || "").toLowerCase().includes("pass")
    ).length;

    const allPassed = passedCount === testCases.length;

    return (
      <div
        className={`mb-5 flex items-center justify-between rounded-xl border px-5 py-4 ${
          allPassed
            ? "border-emerald-400/40 bg-emerald-950/30"
            : "border-red-400/40 bg-red-950/30"
        }`}
      >
        <div>
          <p
            className={`text-lg font-bold ${
              allPassed ? "text-emerald-300" : "text-red-300"
            }`}
          >
            {allPassed ? "Accepted" : "Wrong Answer"}
          </p>
          <p className="mt-1 text-xs text-slate-400">
            {passedCount} / {testCases.length} testcases passed
          </p>
        </div>

        <span
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            allPassed
              ? "bg-emerald-950/60 text-emerald-300"
              : "bg-red-950/60 text-red-300"
          }`}
        >
          {allPassed ? "✓ Passed" : "✕ Failed"}
        </span>
      </div>
    );
  }

  function renderTestCaseList(testCases) {
    if (!Array.isArray(testCases) || testCases.length === 0) {
      return (
        <p className="text-sm text-slate-400">No test cases returned.</p>
      );
    }

    return (
      <div className="space-y-3">
        {testCases.map((item, index) => (
          <div
            key={index}
            className="rounded-xl border border-slate-700 bg-slate-900/70 p-4"
          >
            <div className="mb-2 flex items-center justify-between gap-3">
              <p className="font-semibold text-white">Case {index + 1}</p>

              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusColor(
                  item.status
                )}`}
              >
                {item.status || "Not Executed"}
              </span>
            </div>

            <p className="text-xs text-slate-400">Input</p>
            <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-200">
              {item.input}
            </pre>

            <p className="mt-3 text-xs text-slate-400">Expected Output</p>
            <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-200">
              {item.expected_output}
            </pre>

            <p className="mt-3 text-xs text-slate-400">Actual Output</p>
            <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-950 p-3 font-mono text-xs text-slate-200">
              {item.actual_output || "N/A"}
            </pre>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="mt-10 w-full max-w-6xl rounded-3xl border border-slate-700 bg-slate-950/70 p-4 shadow-2xl">
      <div className="mb-5 border-b border-slate-800 pb-5">
        <Link
          href="/dsa"
          className="text-sm font-semibold text-pink-300 hover:text-pink-200"
        >
          ← Back to DSA Home
        </Link>

        <p className="mt-3 text-sm font-semibold uppercase tracking-widest text-pink-300">
          DSA Practice Mode
        </p>

        <h2 className="mt-2 text-3xl font-bold text-white">
          LeetCode-style AI Practice
        </h2>

        <p className="mt-1 text-base text-slate-400">
          Select topic and difficulty, generate one question, and submit for
          AI evaluation.
        </p>
      </div>

      {isLimitedExecutionTopic() && (
        <div className="mb-5 rounded-2xl border border-yellow-400/30 bg-yellow-950/20 p-4">
          <p className="font-semibold text-yellow-300">
            Evaluation note for {topic}
          </p>
          <p className="mt-2 text-sm leading-7 text-slate-200">
            This topic can involve complex structures. Current evaluation is
            AI-assisted and focuses on logic, approach, complexity, and
            explanation.
          </p>
        </div>
      )}

      <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="mb-2 block text-sm text-slate-300">
              DSA Topic
            </label>

            <select
              value={topic}
              onChange={(e) => handleTopicChange(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-base text-white outline-none"
            >
              <option>Arrays</option>
              <option>Strings</option>
              <option>Linked List</option>
              <option>Stack</option>
              <option>Queue</option>
              <option>Binary Search</option>
              <option>Trees</option>
              <option>Graphs</option>
              <option>Dynamic Programming</option>
            </select>
          </div>

          <div>
            <label className="mb-2 block text-sm text-slate-300">
              Difficulty
            </label>

            <select
              value={difficulty}
              onChange={(e) => handleDifficultyChange(e.target.value)}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-base text-white outline-none"
            >
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
            </select>
          </div>

          <div className="flex items-end">
            <button
              onClick={generatePracticeProblem}
              disabled={loadingProblem}
              className="w-full rounded-xl bg-pink-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-pink-600 disabled:opacity-60"
            >
              {loadingProblem ? "Generating..." : "Generate Problem"}
            </button>
          </div>
        </div>
      </div>

      <div
        className={`grid min-h-[680px] gap-4 lg:grid-cols-2 ${
          problemData
            ? `border-l-4 ${getDifficultyBorder(problemData.difficulty)} rounded-l-2xl`
            : ""
        }`}
      >
        <div className="rounded-2xl border border-slate-800 bg-slate-900/80">
          <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
            <div>
              <h3 className="text-lg font-semibold text-white">
                Problem Statement
              </h3>

              <p className="mt-1 text-sm text-slate-400">
                Topic: {topic} ·{" "}
                <span className={getDifficultyColor()}>{difficulty}</span>
              </p>
            </div>

            <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
              Practice
            </span>
          </div>

          <div className="max-h-[600px] overflow-y-auto p-5">
            {problemData ? (
              renderLeetCodeProblem()
            ) : problem ? (
              <div className="whitespace-pre-line text-[14px] leading-7 text-slate-100">
                {problem}
              </div>
            ) : (
              <div className="flex min-h-[500px] items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
                <div>
                  <p className="text-lg font-semibold text-white">
                    No problem generated yet
                  </p>
                  <p className="mt-2 text-sm text-slate-400">
                    Select topic and difficulty, then click Generate Problem.
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="rounded-2xl border border-slate-800 bg-slate-900/80">
          <div className="flex border-b border-slate-800">
            <button
              onClick={() => setActiveTab("code")}
              className={`px-5 py-4 text-sm font-semibold transition ${
                activeTab === "code"
                  ? "border-b-2 border-pink-400 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {"</>"} Code
            </button>

            <button
              onClick={() => setActiveTab("testcase")}
              className={`px-5 py-4 text-sm font-semibold transition ${
                activeTab === "testcase"
                  ? "border-b-2 border-cyan-400 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Testcase
              {runResult?.test_cases?.length > 0 && (
                <span className="ml-2 rounded-full bg-slate-800 px-2 py-0.5 text-xs">
                  {runResult.test_cases.length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("result")}
              className={`px-5 py-4 text-sm font-semibold transition ${
                activeTab === "result"
                  ? "border-b-2 border-emerald-400 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              Result
            </button>
          </div>

          {activeTab === "code" && (
            <div className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm text-slate-400">Language</p>

                <span className="rounded-lg bg-slate-800 px-3 py-1 font-mono text-sm text-slate-200">
                  Python3
                </span>
              </div>

              {problem ? (
                <div className="overflow-hidden rounded-xl border border-slate-700 bg-[#0B1020]">
                  <Editor
                    height="470px"
                    defaultLanguage="python"
                    language="python"
                    value={solution}
                    onChange={(value) => setSolution(value || "")}
                    onMount={handleEditorMount}
                    options={{
                      fontSize: 14,
                      fontFamily: "Consolas, 'Courier New', monospace",
                      minimap: { enabled: false },
                      tabSize: 4,
                      insertSpaces: true,
                      detectIndentation: false,
                      automaticLayout: true,
                      scrollBeyondLastLine: false,
                      wordWrap: "on",
                      lineNumbers: "on",
                      cursorBlinking: "smooth",
                      cursorSmoothCaretAnimation: "on",
                      formatOnType: true,
                      formatOnPaste: true,
                      autoIndent: "full",
                      bracketPairColorization: { enabled: true },
                      guides: {
                        indentation: true,
                        bracketPairs: true,
                      },
                      padding: {
                        top: 16,
                        bottom: 16,
                      },
                    }}
                  />
                </div>
              ) : (
                <div className="flex min-h-[470px] items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
                  <div>
                    <p className="text-lg font-semibold text-white">
                      Code editor locked
                    </p>
                    <p className="mt-2 text-sm text-slate-400">
                      Generate a problem first. Starter code will appear here.
                    </p>
                  </div>
                </div>
              )}

              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  onClick={runCode}
                  disabled={loadingRun || loadingFeedback || !problem}
                  className="rounded-xl bg-slate-700 px-6 py-3 text-base font-semibold text-white transition hover:bg-slate-600 disabled:opacity-60"
                >
                  {loadingRun ? "Running..." : "▶ Run Code"}
                </button>

                <button
                  onClick={evaluateSolution}
                  disabled={loadingFeedback || loadingRun || !problem}
                  className="rounded-xl bg-emerald-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
                >
                  {loadingFeedback ? "Submitting..." : "Submit"}
                </button>

                <button
                  onClick={() => setSolution(problem ? getStarterCode() : "")}
                  disabled={!problem}
                  className="rounded-xl border border-slate-700 bg-transparent px-6 py-3 text-base font-semibold text-slate-300 transition hover:bg-slate-800 disabled:opacity-60"
                >
                  Reset to Starter Code
                </button>
              </div>
            </div>
          )}

          {activeTab === "testcase" && (
            <div className="max-h-[600px] overflow-y-auto p-5">
              {loadingRun ? (
                <div className="flex min-h-[300px] items-center justify-center">
                  <p className="text-sm text-slate-400">
                    Running your code against test cases...
                  </p>
                </div>
              ) : runResult ? (
                <div>
                  {runResult.error ? (
                    <div className="rounded-xl border border-red-400/40 bg-red-950/30 p-5 text-red-200">
                      {runResult.error}
                    </div>
                  ) : (
                    <>
                      {renderResultBanner(runResult.test_cases)}
                      {renderTestCaseList(runResult.test_cases)}
                    </>
                  )}
                </div>
              ) : (
                <div className="flex min-h-[500px] items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
                  <div>
                    <p className="text-lg font-semibold text-white">
                      No run yet
                    </p>
                    <p className="mt-2 text-sm text-slate-400">
                      Click "Run Code" to check your solution against the
                      test cases without saving an attempt.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {activeTab === "result" && (
            <div className="max-h-[600px] overflow-y-auto p-5">
              {feedback ? (
                <div>
                  {renderResultBanner(feedback.test_cases)}

                  <div className="mb-5 rounded-2xl border border-emerald-400/30 bg-emerald-950/30 p-5">
                    <p className="text-sm text-slate-400">Score</p>

                    <p className="mt-1 text-4xl font-bold text-white">
                      {feedback.score}/10
                    </p>
                  </div>

                  <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-950/50 p-5">
                    <h4 className="mb-3 text-base font-semibold text-white">
                      Test Cases
                    </h4>
                    {renderTestCaseList(feedback.test_cases)}
                  </div>

                  <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-950/50 p-5">
                    <h4 className="mb-2 text-base font-semibold text-white">
                      Feedback
                    </h4>
                    <p className="whitespace-pre-line text-sm leading-7 text-slate-200">
                      {feedback.feedback}
                    </p>
                  </div>

                  <div className="mb-5 rounded-2xl border border-indigo-400/30 bg-indigo-950/30 p-5">
                    <h4 className="mb-2 text-base font-semibold text-indigo-200">
                      Optimized Approach
                    </h4>
                    <p className="whitespace-pre-line text-sm leading-7 text-slate-200">
                      {feedback.optimized_approach}
                    </p>
                  </div>

                  <div className="mb-5 rounded-2xl border border-pink-400/30 bg-pink-950/20 p-5">
                    <h4 className="mb-3 text-base font-semibold text-pink-200">
                      Optimized Python Code
                    </h4>

                    <pre className="max-h-80 overflow-y-auto whitespace-pre-wrap rounded-xl bg-slate-950 p-4 font-mono text-xs leading-6 text-emerald-100">
                      {feedback.optimized_code}
                    </pre>
                  </div>

                  <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-950/50 p-5">
                    <h4 className="mb-2 text-base font-semibold text-white">
                      Explanation
                    </h4>
                    <p className="whitespace-pre-line text-sm leading-7 text-slate-200">
                      {feedback.explanation}
                    </p>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                      <p className="text-sm text-slate-400">Time Complexity</p>
                      <p className="mt-1 font-mono text-base font-semibold text-white">
                        {feedback.time_complexity}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                      <p className="text-sm text-slate-400">Space Complexity</p>
                      <p className="mt-1 font-mono text-base font-semibold text-white">
                        {feedback.space_complexity}
                      </p>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex min-h-[500px] items-center justify-center rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
                  <div>
                    <p className="text-lg font-semibold text-white">
                      No result yet
                    </p>
                    <p className="mt-2 text-sm text-slate-400">
                      Write your solution and click Submit for full AI
                      evaluation and to save this attempt.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 text-center">
        <Link
          href="/dsa/history"
          className="text-sm font-semibold text-cyan-300 hover:text-cyan-200"
        >
          View full practice history →
        </Link>
      </div>
    </div>
  );
}



