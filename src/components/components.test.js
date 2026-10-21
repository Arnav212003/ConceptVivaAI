import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ResultCard from "@/components/ResultCard";
import { TierBadge } from "@/components/dsa/Badges";
import { TestCaseList, VerdictBanner, deriveVerdict } from "@/components/dsa/TestResults";
import { isReadableProjectFile } from "@/components/project/ProjectFolderPicker";
import { EmptyState, ErrorBanner, ScoreValue } from "@/components/ui";
import { buildTimeline, buildTopicReadiness } from "@/components/dashboard/widgets";

describe("score and result display", () => {
  it("shows Not scored instead of 0/10 for unavailable evaluations", () => {
    render(
      <ResultCard
        result={{ evaluation_status: "unavailable", score: null, feedback: "AI evaluation is temporarily unavailable." }}
      />
    );
    expect(screen.getByText("Not scored")).toBeInTheDocument();
    expect(screen.queryByText("0/10")).not.toBeInTheDocument();
    expect(screen.getByText(/was/)).toHaveTextContent("not scored");
  });

  it("explains capped scores", () => {
    render(<ResultCard result={{ evaluation_status: "completed", score: 3, score_capped: true, feedback: "x" }} />);
    expect(screen.getByText(/tried to instruct the grader/)).toBeInTheDocument();
  });

  it("renders a numeric score", () => {
    render(<ScoreValue score={8.5} />);
    expect(screen.getByText("8.5/10")).toBeInTheDocument();
  });
});

describe("judge results", () => {
  it("prefers the judge verdict and shows pass counts", () => {
    render(<VerdictBanner judge={{ verdict: "Time Limit Exceeded", passed: 0, total: 3 }} testCases={[]} />);
    expect(screen.getByTestId("verdict")).toHaveTextContent("Time Limit Exceeded");
    expect(screen.getByText("0 / 3 testcases passed")).toBeInTheDocument();
  });

  it("infers a verdict from test cases when no judge ran", () => {
    expect(deriveVerdict(null, [{ status: "Passed" }, { status: "Passed" }])).toBe("Accepted");
    expect(deriveVerdict(null, [{ status: "Passed" }, { status: "Failed" }])).toBe("Wrong Answer");
    expect(deriveVerdict(null, [])).toBeNull();
  });

  it("never shows inputs of hidden tests", () => {
    render(
      <TestCaseList
        testCases={[
          { status: "Passed", input: "[2,7]", expected_output: "[0,1]", actual_output: "[0,1]", hidden: false },
          { status: "Passed", input: "Hidden test #2", expected_output: "hidden", actual_output: "hidden", hidden: true },
        ]}
      />
    );
    expect(screen.getByText("[2,7]")).toBeInTheDocument();
    expect(screen.queryByText("Hidden test #2")).not.toBeInTheDocument();
    expect(screen.getByText(/Inputs stay private/)).toBeInTheDocument();
  });

  it("labels tiers honestly", () => {
    const { rerender } = render(<TierBadge tier="verified" />);
    expect(screen.getByText("✅ Verified")).toBeInTheDocument();
    rerender(<TierBadge tier="ai_generated" />);
    expect(screen.getByText("🤖 AI Generated")).toBeInTheDocument();
  });
});

describe("states", () => {
  it("renders empty and error states", () => {
    render(
      <>
        <EmptyState title="Nothing here" message="Try again" />
        <ErrorBanner message="Backend unavailable." />
      </>
    );
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Backend unavailable.");
  });
});

describe("project folder filtering", () => {
  const file = (path) => ({ name: path.split("/").pop(), webkitRelativePath: path, size: 10 });

  it("keeps source files and drops secrets, dependencies and lock files", () => {
    expect(isReadableProjectFile(file("app/main.py"))).toBe(true);
    expect(isReadableProjectFile(file("app/.env.example"))).toBe(true);
    expect(isReadableProjectFile(file("app/.env"))).toBe(false);
    expect(isReadableProjectFile(file("app/.env.local"))).toBe(false);
    expect(isReadableProjectFile(file("app/node_modules/react/index.js"))).toBe(false);
    expect(isReadableProjectFile(file("app/package-lock.json"))).toBe(false);
    expect(isReadableProjectFile(file("app/logo.png"))).toBe(false);
  });
});

describe("dashboard aggregation", () => {
  it("excludes unscored attempts from topic readiness", () => {
    const timeline = buildTimeline({
      ml_practice: [
        { id: 1, topic: "KNN", score: 8, verdict: "STRONG", created_at: "2026-10-01T00:00:00Z" },
        { id: 2, topic: "KNN", score: null, verdict: "UNAVAILABLE", created_at: "2026-10-02T00:00:00Z" },
      ],
    });
    expect(timeline[0].subtitle).toContain("Not scored");
    const readiness = buildTopicReadiness(timeline);
    expect(readiness).toEqual([expect.objectContaining({ topic: "KNN", attempts: 1, readiness: 80 })]);
  });
});

describe("progress panel", () => {
  it("renders streak and one bar per week", async () => {
    const { ProgressPanel } = await import("@/components/dashboard/widgets");
    render(
      <ProgressPanel
        progress={{
          current_streak_days: 3,
          active_days_last_30: 5,
          weeks: [
            { week_start: "2026-10-12", attempts: 2, average_score: 6 },
            { week_start: "2026-10-19", attempts: 4, average_score: null },
          ],
        }}
      />
    );
    expect(screen.getByTestId("streak")).toHaveTextContent("3 days");
    expect(screen.getByRole("img")).toBeInTheDocument();
    expect(screen.getByTitle(/Week of 2026-10-19: 4 attempt\(s\), average Not scored/)).toBeInTheDocument();
  });
});

describe("analytics client", () => {
  it("sends nothing when Do Not Track is on", async () => {
    const { track } = await import("@/lib/analytics");
    const beacon = vi.fn();
    Object.defineProperty(navigator, "sendBeacon", { value: beacon, configurable: true });
    Object.defineProperty(navigator, "doNotTrack", { value: "1", configurable: true });
    track("page_view", "/");
    expect(beacon).not.toHaveBeenCalled();
    Object.defineProperty(navigator, "doNotTrack", { value: "0", configurable: true });
    track("page_view", "/");
    expect(beacon).toHaveBeenCalledTimes(1);
  });
});
