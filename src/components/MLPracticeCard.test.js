import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import MLPracticeCard from "@/components/MLPracticeCard";

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

function mockBackend(handlers) {
  const fetchMock = vi.fn(async (url, options = {}) => {
    if (url === "/api/session") {
      return jsonResponse({ session_id: "cv_test", session_token: "1.sig", expires_in_seconds: 3600 });
    }
    const body = options.body ? JSON.parse(options.body) : {};
    return handlers[body.action](body);
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("MLPracticeCard", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("asks the server to choose a topic instead of sending instructions", async () => {
    const fetchMock = mockBackend({
      question: () => jsonResponse({ question: "What is overfitting?", topic: "Overfitting and Underfitting", source: "ai" }),
    });
    render(<MLPracticeCard />);
    await userEvent.click(screen.getByRole("button", { name: "Generate AI Question" }));

    expect(await screen.findByTestId("question")).toHaveTextContent("What is overfitting?");
    const sent = JSON.parse(fetchMock.mock.calls.find(([url]) => url === "/api/interview")[1].body);
    expect(sent).toMatchObject({ action: "question", auto_topic: true, track: "ml" });
    expect(sent.topic).toBeUndefined();
    expect(screen.getByText("Topic: Overfitting and Underfitting")).toBeInTheDocument();
  });

  it("shows a scored result with the rubric breakdown", async () => {
    mockBackend({
      question: () => jsonResponse({ question: "What is KNN?", topic: "KNN" }),
      evaluate: () =>
        jsonResponse({
          evaluation_status: "completed",
          score: 8,
          verdict: "STRONG",
          feedback: "Good.",
          missing_points: "Distance metrics.",
          corrected_answer: "KNN is...",
          follow_up_question: "How do you pick k?",
          rubric: { technical_correctness: { points: 3, max_points: 4, rationale: "Mostly right" } },
        }),
    });
    render(<MLPracticeCard />);
    await userEvent.click(screen.getByRole("button", { name: "Generate AI Question" }));
    await screen.findByTestId("question");
    await userEvent.type(screen.getByLabelText("Your Answer"), "KNN votes among neighbours.");
    await userEvent.click(screen.getByRole("button", { name: "Submit Answer" }));

    const result = await screen.findByTestId("ml-result");
    expect(result).toHaveTextContent("8/10");
    expect(result).toHaveTextContent("STRONG");
    expect(result).toHaveTextContent("3/4");
  });

  it("shows Not scored when AI evaluation is unavailable and keeps the local average honest", async () => {
    mockBackend({
      question: () => jsonResponse({ question: "What is KNN?", topic: "KNN" }),
      evaluate: () =>
        jsonResponse({ evaluation_status: "unavailable", score: null, verdict: "UNAVAILABLE", feedback: "Unavailable" }),
    });
    render(<MLPracticeCard />);
    await userEvent.click(screen.getByRole("button", { name: "Generate AI Question" }));
    await screen.findByTestId("question");
    await userEvent.type(screen.getByLabelText("Your Answer"), "answer");
    await userEvent.click(screen.getByRole("button", { name: "Submit Answer" }));

    const result = await screen.findByTestId("ml-result");
    expect(result).toHaveTextContent("Not scored");
    expect(result).not.toHaveTextContent("0/10");
    await waitFor(() => expect(screen.getAllByText("Not scored").length).toBeGreaterThan(1));
  });

  it("shows an error banner instead of a fake question when the backend fails", async () => {
    mockBackend({ question: () => jsonResponse({ detail: "Too many requests" }, 429) });
    render(<MLPracticeCard />);
    await userEvent.click(screen.getByRole("button", { name: "Generate AI Question" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("going a bit fast");
    expect(screen.queryByTestId("question")).not.toBeInTheDocument();
  });
});
