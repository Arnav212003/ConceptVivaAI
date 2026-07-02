"use client";

import { useEffect, useState } from "react";
import Editor from "@monaco-editor/react";

export default function DSAPracticeCard() {
  const [mode, setMode] = useState("practice");
  const [topic, setTopic] = useState("Arrays");
  const [difficulty, setDifficulty] = useState("Easy");
  const [problem, setProblem] = useState("");
  const [solution, setSolution] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [loadingProblem, setLoadingProblem] = useState(false);
  const [loadingFeedback, setLoadingFeedback] = useState(false);
  const [activeTab, setActiveTab] = useState("code");
  const [dsaHistory, setDsaHistory] = useState([]);
  const [mockQuestions, setMockQuestions] = useState([]);
  const [selectedMockQuestion, setSelectedMockQuestion] = useState(null);

  useEffect(() => {
    const savedHistory = localStorage.getItem("conceptviva_dsa_history");

    if (savedHistory) {
      setDsaHistory(JSON.parse(savedHistory));
    }
  }, []);

  function getDefaultStarterCode() {
    return `class Solution:
    def solve(self):
        # Write your code here
        pass`;
  }

  function getProblemName(problemText) {
    const titleLine = problemText
      .split("\n")
      .find(
        (line) =>
          line.trim().startsWith("Problem:") ||
          line.trim().startsWith("Question Title:")
      );

    if (!titleLine) return selectedMockQuestion?.title || "DSA Problem";

    return titleLine
      .replace("Problem:", "")
      .replace("Question Title:", "")
      .trim();
  }

  function saveDsaAttempt(resultData) {
    const today = new Date();

    const attempt = {
      id: Date.now(),
      date: today.toLocaleDateString(),
      time: today.toLocaleTimeString(),
      mode: mode === "practice" ? "Practice" : "Mock Interview",
      topic,
      difficulty,
      problemName: getProblemName(problem),
      score: resultData.score ?? 0,
      status:
        Number(resultData.score ?? 0) >= 7 ? "Good" : "Needs Improvement",
    };

    const updatedHistory = [attempt, ...dsaHistory].slice(0, 20);

    setDsaHistory(updatedHistory);
    localStorage.setItem(
      "conceptviva_dsa_history",
      JSON.stringify(updatedHistory)
    );
  }

  function clearDsaHistory() {
    setDsaHistory([]);
    localStorage.removeItem("conceptviva_dsa_history");
  }

  function resetWorkspace() {
    setProblem("");
    setSolution("");
    setFeedback(null);
    setActiveTab("code");
    setSelectedMockQuestion(null);
  }

  function handleTopicChange(value) {
    setTopic(value);
    resetWorkspace();
    setMockQuestions([]);
  }

  function handleDifficultyChange(value) {
    setDifficulty(value);
    resetWorkspace();
    setMockQuestions([]);
  }

  function handleModeChange(value) {
    setMode(value);
    resetWorkspace();
    setMockQuestions([]);

    if (value === "mock") {
      setDifficulty("Mixed");
    } else {
      setDifficulty("Easy");
    }
  }

  async function generatePracticeProblem() {
    setLoadingProblem(true);
    resetWorkspace();

    try {
      const response = await fetch("/api/dsa", {
        method: "POST",
        body: JSON.stringify({
          action: "generate",
          topic,
          difficulty,
        }),
      });

      const data = await response.json();

      if (data.problem) {
        setProblem(data.problem);
        setSolution(data.starter_code || getDefaultStarterCode());
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

  async function generateMockSet() {
    setLoadingProblem(true);
    resetWorkspace();
    setMockQuestions([]);

    try {
      const response = await fetch("/api/dsa", {
        method: "POST",
        body: JSON.stringify({
          action: "generateMockSet",
          topic,
          difficulty: "Mixed",
          count: 10,
        }),
      });

      const data = await response.json();

      if (Array.isArray(data.questions) && data.questions.length > 0) {
        setMockQuestions(data.questions);
      } else {
        setProblem(
          "Mock set generation failed. Please check /api/dsa route and backend endpoint."
        );
      }
    } catch (error) {
      setProblem("Something went wrong while generating the mock set.");
    }

    setLoadingProblem(false);
  }

  async function openMockQuestion(question) {
    setLoadingProblem(true);
    setSelectedMockQuestion(question);
    setProblem("");
    setSolution("");
    setFeedback(null);
    setActiveTab("code");

    try {
      const response = await fetch("/api/dsa", {
        method: "POST",
        body: JSON.stringify({
          action: "generateFromQuestion",
          question,
          topic: question.topic || topic,
          difficulty: question.difficulty || difficulty,
        }),
      });

      const data = await response.json();

      if (data.problem) {
        setProblem(data.problem);
        setSolution(data.starter_code || getDefaultStarterCode());
      } else {
        setProblem("Problem generation failed for selected mock question.");
      }
    } catch (error) {
      setProblem("Something went wrong while opening this mock question.");
    }

    setLoadingProblem(false);
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
      const response = await fetch("/api/dsa", {
        method: "POST",
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
      saveDsaAttempt(resultData);
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
      saveDsaAttempt(resultData);
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

  const totalAttempts = dsaHistory.length;

  const averageScore =
    totalAttempts > 0
      ? (
          dsaHistory.reduce((sum, item) => sum + Number(item.score || 0), 0) /
          totalAttempts
        ).toFixed(1)
      : "0.0";

  const todayDate = new Date().toLocaleDateString();

  const solvedToday = dsaHistory.filter((item) => item.date === todayDate).length;

  const lastTopic = dsaHistory[0]?.topic || "N/A";

  return (
    <div className="mt-10 w-full max-w-6xl rounded-3xl border border-slate-700 bg-slate-950/70 p-4 shadow-2xl">
      <div className="mb-5 border-b border-slate-800 pb-5">
        <p className="text-sm font-semibold uppercase tracking-widest text-pink-300">
          DSA Practice Mode
        </p>

        <h2 className="mt-2 text-3xl font-bold text-white">
          LeetCode-style AI Practice
        </h2>

        <p className="mt-1 text-base text-slate-400">
          Choose practice or mock interview mode, select topic and difficulty,
          then generate questions.
        </p>
      </div>

      <div className="mb-5 grid gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Total Attempts</p>
          <p className="mt-1 text-3xl font-bold text-white">{totalAttempts}</p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Average Score</p>
          <p className="mt-1 text-3xl font-bold text-white">
            {averageScore}/10
          </p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Solved Today</p>
          <p className="mt-1 text-3xl font-bold text-white">{solvedToday}</p>
        </div>

        <div className="rounded-2xl border border-slate-700 bg-slate-900/70 p-4">
          <p className="text-sm text-slate-400">Last Topic</p>
          <p className="mt-1 text-xl font-bold text-white">{lastTopic}</p>
        </div>
      </div>

      <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <p className="mb-3 text-sm font-semibold uppercase tracking-widest text-pink-300">
          Select Mode
        </p>

        <div className="grid gap-3 md:grid-cols-2">
          <button
            onClick={() => handleModeChange("practice")}
            className={`rounded-2xl border p-4 text-left transition ${
              mode === "practice"
                ? "border-pink-400 bg-pink-950/30"
                : "border-slate-700 bg-slate-950/40 hover:border-slate-500"
            }`}
          >
            <p className="text-lg font-bold text-white">DSA Practice</p>
            <p className="mt-1 text-sm text-slate-400">
              Generate one question, solve it, and submit for AI evaluation.
            </p>
          </button>

          <button
            onClick={() => handleModeChange("mock")}
            className={`rounded-2xl border p-4 text-left transition ${
              mode === "mock"
                ? "border-emerald-400 bg-emerald-950/30"
                : "border-slate-700 bg-slate-950/40 hover:border-slate-500"
            }`}
          >
            <p className="text-lg font-bold text-white">DSA Mock Interview</p>
            <p className="mt-1 text-sm text-slate-400">
              Generate a 10-question mixed set: 3 Easy, 4 Medium, 3 Hard.
            </p>
          </button>
        </div>
      </div>

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
              disabled={mode === "mock"}
              className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-base text-white outline-none disabled:cursor-not-allowed disabled:opacity-60"
            >
              {mode === "mock" && <option>Mixed</option>}
              <option>Easy</option>
              <option>Medium</option>
              <option>Hard</option>
            </select>

            {mode === "mock" && (
              <p className="mt-2 text-xs text-slate-400">
                Mock mode uses mixed ratio automatically.
              </p>
            )}
          </div>

          <div className="flex items-end">
            {mode === "practice" ? (
              <button
                onClick={generatePracticeProblem}
                disabled={loadingProblem}
                className="w-full rounded-xl bg-pink-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-pink-600 disabled:opacity-60"
              >
                {loadingProblem ? "Generating..." : "Generate Problem"}
              </button>
            ) : (
              <button
                onClick={generateMockSet}
                disabled={loadingProblem}
                className="w-full rounded-xl bg-emerald-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
              >
                {loadingProblem ? "Generating..." : "Generate Mock Set"}
              </button>
            )}
          </div>
        </div>
      </div>

      {mode === "mock" && mockQuestions.length > 0 && (
        <div className="mb-5 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
          <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
            <div>
              <h3 className="text-xl font-bold text-white">
                Mock Interview Question Set
              </h3>
              <p className="text-sm text-slate-400">
                Click any question to generate its full problem statement.
              </p>
            </div>

            <span className="rounded-full bg-slate-800 px-4 py-2 text-sm text-slate-300">
              10 Questions · 3 Easy + 4 Medium + 3 Hard
            </span>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            {mockQuestions.map((question, index) => (
              <button
                key={question.id || index}
                onClick={() => openMockQuestion(question)}
                className={`rounded-xl border p-4 text-left transition ${
                  selectedMockQuestion?.id === question.id
                    ? "border-pink-400 bg-pink-950/30"
                    : "border-slate-700 bg-slate-950/40 hover:border-slate-500"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm text-slate-400">
                      Question {index + 1}
                    </p>
                    <p className="mt-1 font-semibold text-white">
                      {question.title}
                    </p>
                    <p className="mt-1 text-xs text-slate-400">
                      {question.pattern}
                    </p>
                  </div>

                  <span
                    className={`rounded-full px-3 py-1 text-xs font-semibold ${getDifficultyBadge(
                      question.difficulty
                    )}`}
                  >
                    {question.difficulty}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="grid min-h-[680px] gap-4 lg:grid-cols-2">
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
              {mode === "practice" ? "Practice" : "Mock"}
            </span>
          </div>

          <div className="max-h-[600px] overflow-y-auto p-5">
            {problem ? (
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
                    {mode === "practice"
                      ? "Select topic and difficulty, then click Generate Problem."
                      : "Generate a mock set, then click one question from the list."}
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
              className={`px-5 py-4 text-sm font-semibold ${
                activeTab === "code"
                  ? "border-b-2 border-pink-400 text-white"
                  : "text-slate-400"
              }`}
            >
              Code
            </button>

            <button
              onClick={() => setActiveTab("result")}
              className={`px-5 py-4 text-sm font-semibold ${
                activeTab === "result"
                  ? "border-b-2 border-emerald-400 text-white"
                  : "text-slate-400"
              }`}
            >
              Result
            </button>
          </div>

          {activeTab === "code" && (
            <div className="p-5">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm text-slate-400">Language</p>

                <span className="rounded-lg bg-slate-800 px-3 py-1 text-sm text-slate-200">
                  Python
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
                  onClick={evaluateSolution}
                  disabled={loadingFeedback || !problem}
                  className="rounded-xl bg-emerald-500 px-6 py-3 text-base font-semibold text-white transition hover:bg-emerald-600 disabled:opacity-60"
                >
                  {loadingFeedback ? "Running Tests..." : "Run & Submit"}
                </button>

                <button
                  onClick={() => setSolution(problem ? solution : "")}
                  disabled={!problem}
                  className="rounded-xl bg-slate-700 px-6 py-3 text-base font-semibold text-white transition hover:bg-slate-600 disabled:opacity-60"
                >
                  Keep Code
                </button>

                <button
                  onClick={() => setSolution(problem ? getDefaultStarterCode() : "")}
                  disabled={!problem}
                  className="rounded-xl bg-slate-700 px-6 py-3 text-base font-semibold text-white transition hover:bg-slate-600 disabled:opacity-60"
                >
                  Blank Reset
                </button>
              </div>
            </div>
          )}

          {activeTab === "result" && (
            <div className="max-h-[600px] overflow-y-auto p-5">
              {feedback ? (
                <div>
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

                    {feedback.test_cases.length > 0 ? (
                      <div className="space-y-3">
                        {feedback.test_cases.map((item, index) => (
                          <div
                            key={index}
                            className="rounded-xl border border-slate-700 bg-slate-900/70 p-4"
                          >
                            <div className="mb-2 flex items-center justify-between gap-3">
                              <p className="font-semibold text-white">
                                Test Case {index + 1}
                              </p>

                              <span
                                className={`rounded-full px-3 py-1 text-xs font-semibold ${getStatusColor(
                                  item.status
                                )}`}
                              >
                                {item.status || "Not Executed"}
                              </span>
                            </div>

                            <p className="text-xs text-slate-400">Input</p>
                            <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs text-slate-200">
                              {item.input}
                            </pre>

                            <p className="mt-3 text-xs text-slate-400">
                              Expected Output
                            </p>
                            <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs text-slate-200">
                              {item.expected_output}
                            </pre>

                            <p className="mt-3 text-xs text-slate-400">
                              Actual Output
                            </p>
                            <pre className="mt-1 whitespace-pre-wrap rounded-lg bg-slate-950 p-3 text-xs text-slate-200">
                              {item.actual_output || "N/A"}
                            </pre>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-slate-400">
                        No test cases returned.
                      </p>
                    )}
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
                      <p className="mt-1 text-base font-semibold text-white">
                        {feedback.time_complexity}
                      </p>
                    </div>

                    <div className="rounded-xl border border-slate-700 bg-slate-950/50 p-4">
                      <p className="text-sm text-slate-400">Space Complexity</p>
                      <p className="mt-1 text-base font-semibold text-white">
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
                      Generate a problem, write your solution, and click Run &
                      Submit.
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="mt-8 rounded-2xl border border-slate-700 bg-slate-900/70 p-5">
        <div className="mb-4 flex items-center justify-between gap-4">
          <div>
            <h3 className="text-xl font-bold text-white">
              Recent DSA Practice History
            </h3>
            <p className="text-sm text-slate-400">
              Your latest attempts are saved in this browser.
            </p>
          </div>

          <button
            onClick={clearDsaHistory}
            disabled={dsaHistory.length === 0}
            className="rounded-xl bg-red-500 px-4 py-2 text-sm font-semibold text-white transition hover:bg-red-600 disabled:opacity-50"
          >
            Clear History
          </button>
        </div>

        {dsaHistory.length > 0 ? (
          <div className="max-h-72 overflow-y-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-slate-400">
                <tr className="border-b border-slate-700">
                  <th className="py-3 pr-3">Date</th>
                  <th className="py-3 pr-3">Mode</th>
                  <th className="py-3 pr-3">Problem</th>
                  <th className="py-3 pr-3">Topic</th>
                  <th className="py-3 pr-3">Difficulty</th>
                  <th className="py-3 pr-3">Score</th>
                  <th className="py-3 pr-3">Status</th>
                </tr>
              </thead>

              <tbody>
                {dsaHistory.map((item) => (
                  <tr key={item.id} className="border-b border-slate-800">
                    <td className="py-3 pr-3 text-slate-300">
                      {item.date} {item.time}
                    </td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.mode || "Practice"}
                    </td>
                    <td className="py-3 pr-3 font-semibold text-white">
                      {item.problemName}
                    </td>
                    <td className="py-3 pr-3 text-slate-300">{item.topic}</td>
                    <td className="py-3 pr-3 text-slate-300">
                      {item.difficulty}
                    </td>
                    <td className="py-3 pr-3 font-bold text-white">
                      {item.score}/10
                    </td>
                    <td className="py-3 pr-3">
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          item.status === "Good"
                            ? "bg-emerald-950/40 text-emerald-300"
                            : "bg-yellow-950/40 text-yellow-300"
                        }`}
                      >
                        {item.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 p-6 text-center">
            <p className="font-semibold text-white">No DSA history yet</p>
            <p className="mt-2 text-sm text-slate-400">
              Submit your first solution to start tracking practice.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}