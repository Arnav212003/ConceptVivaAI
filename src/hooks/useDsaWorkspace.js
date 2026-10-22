"use client";

import { useCallback, useState } from "react";
import { apiPost } from "@/lib/api";

const DEFAULT_STARTER = `class Solution:
    def solve(self):
        # Write your code here
        pass`;

function normalizeFeedback(data) {
  return {
    ...data,
    score: typeof data.score === "number" ? data.score : null,
    test_cases: Array.isArray(data.test_cases) ? data.test_cases : [],
  };
}

// State and actions shared by DSA practice and mock mode.
export default function useDsaWorkspace() {
  const [problem, setProblem] = useState("");
  const [problemData, setProblemData] = useState(null);
  const [tier, setTier] = useState(null);
  // Execution info for AI practice problems: { available, test_count, cross_check, reason }.
  const [execution, setExecution] = useState(null);
  const [solution, setSolution] = useState("");
  const [runResult, setRunResult] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [solutionOnly, setSolutionOnly] = useState(false);
  const [activeTab, setActiveTab] = useState("code");
  const [loading, setLoading] = useState({ problem: false, run: false, submit: false, solution: false });
  const [error, setError] = useState("");

  const busy = loading.run || loading.submit || loading.solution;
  const starterCode = problemData?.starter_code || DEFAULT_STARTER;

  const setFlag = (name, value) => setLoading((current) => ({ ...current, [name]: value }));

  const reset = useCallback(() => {
    setProblem("");
    setProblemData(null);
    setTier(null);
    setExecution(null);
    setSolution("");
    setRunResult(null);
    setFeedback(null);
    setSolutionOnly(false);
    setActiveTab("code");
    setError("");
  }, []);

  const loadProblem = useCallback(
    async (action, payload, fallbackTier) => {
      reset();
      setFlag("problem", true);
      try {
        const data = await apiPost("/api/dsa", { action, ...payload });
        setProblem(data.problem || "");
        setProblemData(data.problem_json || null);
        setTier(data.tier || fallbackTier || null);
        setExecution(data.execution || null);
        setSolution(data.problem_json?.starter_code || data.starter_code || DEFAULT_STARTER);
        return data;
      } catch (err) {
        setError(err.message);
        return null;
      } finally {
        setFlag("problem", false);
      }
    },
    [reset]
  );

  const practiceProblemId = problemData?.practice_problem_id || "";

  // "Run" never saves. Bank questions run hidden tests and AI practice problems run
  // their server-stored sample tests in the isolated judge; without either it is a
  // quick AI check.
  const run = useCallback(
    async ({ topic, difficulty, judgeEnabled }) => {
      setFlag("run", true);
      setRunResult(null);
      setError("");
      try {
        if (judgeEnabled && practiceProblemId && execution?.available) {
          // Only the opaque id is sent; the server loads the tests itself.
          const judge = await apiPost("/api/dsa", {
            action: "run",
            practice_problem_id: practiceProblemId,
            solution,
          });
          setRunResult({
            source: "ai_samples",
            judge,
            test_cases: judge.test_cases || [],
            cross_check: judge.cross_check,
          });
        } else if (judgeEnabled && problemData?.question_id) {
          const judge = await apiPost("/api/dsa", {
            action: "run",
            question_id: problemData.question_id,
            problem,
            solution,
          });
          setRunResult({ source: "judge", judge, test_cases: judge.test_cases || [] });
        } else {
          const data = await apiPost("/api/dsa", { action: "evaluate", topic, difficulty, problem, solution });
          setRunResult({ source: "ai", ...normalizeFeedback(data) });
          if (data.tier) setTier(data.tier);
        }
      } catch (err) {
        setRunResult({ error: err.message, test_cases: [] });
      } finally {
        setFlag("run", false);
        setActiveTab("testcase");
      }
    },
    [execution, practiceProblemId, problem, problemData, solution]
  );

  const submit = useCallback(
    async ({ topic, difficulty, mode }) => {
      setFlag("submit", true);
      setFeedback(null);
      setSolutionOnly(false);
      setError("");
      try {
        const data = normalizeFeedback(
          await apiPost("/api/dsa", {
            action: "evaluate",
            topic,
            difficulty,
            problem,
            solution,
            mode,
            save_attempt: true,
            ...(practiceProblemId ? { practice_problem_id: practiceProblemId } : {}),
          })
        );
        setFeedback(data);
        const source = data.execution ? "ai_samples" : data.judge ? "judge" : "ai";
        setRunResult({ source, judge: data.judge, test_cases: data.test_cases, cross_check: data.execution?.cross_check });
        if (data.tier) setTier(data.tier);
        setActiveTab("result");
        return data;
      } catch (err) {
        setError(err.message);
        return null;
      } finally {
        setFlag("submit", false);
      }
    },
    [practiceProblemId, problem, solution]
  );

  const revealSolution = useCallback(
    async ({ topic, difficulty }) => {
      setFlag("solution", true);
      setFeedback(null);
      setSolutionOnly(true);
      setError("");
      try {
        const data = normalizeFeedback(
          await apiPost("/api/dsa", {
            action: "evaluate",
            topic,
            difficulty,
            problem,
            solution: solution.trim() || starterCode,
          })
        );
        setFeedback(data);
        setActiveTab("result");
        return data;
      } catch (err) {
        setError(err.message);
        setSolutionOnly(false);
        return null;
      } finally {
        setFlag("solution", false);
      }
    },
    [problem, solution, starterCode]
  );

  return {
    problem,
    problemData,
    tier,
    execution,
    solution,
    setSolution,
    starterCode,
    runResult,
    feedback,
    solutionOnly,
    activeTab,
    setActiveTab,
    loading,
    busy,
    error,
    setError,
    reset,
    loadProblem,
    run,
    submit,
    revealSolution,
  };
}
