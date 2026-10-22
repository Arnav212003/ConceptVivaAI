import { act, render, renderHook, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import SolutionPanel from "@/components/dsa/SolutionPanel";
import { VerdictBanner } from "@/components/dsa/TestResults";
import useDsaWorkspace from "@/hooks/useDsaWorkspace";
import { testSummary } from "@/lib/testResults";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function mockFetch(handler) {
  const fetchMock = vi.fn(async (url, options = {}) => {
    if (url === "/api/session") {
      return jsonResponse({ session_id: "cv_t", session_token: "1.sig", expires_in_seconds: 3600 });
    }
    return handler(JSON.parse(options.body || "{}"));
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

const PROBLEM = {
  problem: "Problem: Max Pair Sum",
  tier: "ai_generated",
  execution: { available: true, test_count: 4, cross_check: "cross_checked", reason: "" },
  problem_json: {
    question_id: "",
    practice_problem_id: "aip_0123456789abcdef01234567",
    title: "Max Pair Sum",
    starter_code: "class Solution:\n    def maxPairSum(self, nums):\n        pass",
  },
};

describe("AI practice execution in the workspace", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("runs stored sample tests by id and never sends tests from the browser", async () => {
    const fetchMock = mockFetch((body) => {
      if (body.action === "generateAI") return jsonResponse(PROBLEM);
      return jsonResponse({ status: "finished", verdict: "Accepted", passed: 4, total: 4, test_cases: [], cross_check: "cross_checked" });
    });
    const { result } = renderHook(() => useDsaWorkspace());

    await act(() => result.current.loadProblem("generateAI", { topic: "Arrays", difficulty: "Easy" }, "ai_generated"));
    expect(result.current.execution.available).toBe(true);
    await act(() => result.current.run({ topic: "Arrays", difficulty: "Easy", judgeEnabled: true }));

    const sent = JSON.parse(fetchMock.mock.calls.at(-1)[1].body);
    expect(sent).toEqual({
      action: "run",
      practice_problem_id: "aip_0123456789abcdef01234567",
      solution: PROBLEM.problem_json.starter_code,
    });
    expect(result.current.runResult.source).toBe("ai_samples");
  });

  it("falls back to an AI check when no executable tests exist", async () => {
    const fetchMock = mockFetch((body) => {
      if (body.action === "generateAI") {
        return jsonResponse({ ...PROBLEM, execution: { available: false, test_count: 0, reason: "Not enough tests." } });
      }
      return jsonResponse({ evaluation_status: "unavailable", score: null, test_cases: [] });
    });
    const { result } = renderHook(() => useDsaWorkspace());
    await act(() => result.current.loadProblem("generateAI", { topic: "Arrays", difficulty: "Easy" }));
    await act(() => result.current.run({ topic: "Arrays", difficulty: "Easy", judgeEnabled: true }));
    expect(JSON.parse(fetchMock.mock.calls.at(-1)[1].body).action).toBe("evaluate");
    expect(result.current.runResult.source).toBe("ai");
  });

  it("submits with the problem id so the server runs its own tests", async () => {
    const fetchMock = mockFetch((body) => {
      if (body.action === "generateAI") return jsonResponse(PROBLEM);
      return jsonResponse({ evaluation_status: "completed", score: 8, test_cases: [], execution: { cross_check: "cross_checked" } });
    });
    const { result } = renderHook(() => useDsaWorkspace());
    await act(() => result.current.loadProblem("generateAI", { topic: "Arrays", difficulty: "Easy" }));
    await act(() => result.current.submit({ topic: "Arrays", difficulty: "Easy", mode: "Practice" }));
    const sent = JSON.parse(fetchMock.mock.calls.at(-1)[1].body);
    expect(sent.practice_problem_id).toBe("aip_0123456789abcdef01234567");
    expect(sent.save_attempt).toBe(true);
    expect(sent.tests).toBeUndefined();
  });
});

describe("result rendering", () => {
  it("labels syntax errors", () => {
    render(<VerdictBanner judge={{ verdict: "Compilation Error", error_kind: "syntax_error", error: "SyntaxError: x" }} testCases={[]} />);
    expect(screen.getByTestId("verdict")).toHaveTextContent("Compilation Error");
    expect(screen.getByTestId("error-kind")).toHaveTextContent("Syntax Error");
  });

  it("shows sample execution separately from the AI score and says it is not verified", () => {
    render(
      <SolutionPanel
        feedback={{
          evaluation_status: "completed", score: 9, scoring_method: "ai_rubric", test_cases: [],
          judge: { verdict: "Accepted", passed: 4, total: 4 },
          execution: { source: "ai_generated_samples", verified: false, available: true, cross_check: "cross_checked",
                       verdict: "Accepted", passed: 4, total: 4 },
        }}
      />
    );
    expect(screen.getByTestId("dsa-score")).toHaveTextContent("9/10");
    const block = screen.getByTestId("sample-execution");
    expect(block).toHaveTextContent("4/4 passed · Accepted");
    expect(block).toHaveTextContent("not independently verified");
    expect(screen.getByText("Scored by AI rubric review")).toBeInTheDocument();
  });

  it("describes test sources consistently", () => {
    expect(testSummary({ test_source: "hidden_tests", tests_passed: 3, tests_total: 3, judge_verdict: "Accepted" }))
      .toBe("Hidden tests 3/3 · Accepted");
    expect(testSummary({ test_source: "ai_generated_samples", tests_passed: 2, tests_total: 4, judge_verdict: "Wrong Answer" }))
      .toBe("AI sample tests 2/4 · Wrong Answer (not verified)");
    expect(testSummary({ test_source: "none", tests_total: 0 })).toBe("");
  });
});
