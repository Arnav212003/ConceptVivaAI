import { expect, test } from "@playwright/test";
import { TWO_SUM_PROBLEM, mockApi } from "./fixtures";

async function expectNoHorizontalScroll(page) {
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
}

test("home page loads with navigation and fits the viewport", async ({ page, isMobile }) => {
  await mockApi(page);
  await page.goto("/");
  await expect(page.getByText("ConceptVivaAI").first()).toBeVisible();
  if (isMobile) {
    await page.getByRole("button", { name: "Menu" }).click();
    await expect(page.locator("#mobile-menu").getByRole("link", { name: "Dashboard" })).toBeVisible();
  } else {
    await expect(page.getByRole("navigation").getByRole("link", { name: "DSA Practice", exact: true })).toBeVisible();
  }
  await expectNoHorizontalScroll(page);
});

test("ML practice: server-chosen topic, rubric score, and unavailable state", async ({ page }) => {
  let evaluations = 0;
  await mockApi(page, {
    handlers: {
      "/api/interview": (body) => {
        if (body.action === "question") {
          expect(body.auto_topic).toBe(true);
          return { question: "Explain the bias-variance tradeoff.", topic: "Bias-Variance Tradeoff", source: "ai" };
        }
        evaluations += 1;
        if (evaluations === 1) {
          return {
            evaluation_status: "completed", score: 7, verdict: "PARTIAL", feedback: "Mostly right.",
            missing_points: "Mention irreducible error.", corrected_answer: "Bias is...", follow_up_question: "Why?",
            rubric: { technical_correctness: { points: 3, max_points: 4, rationale: "ok" } },
          };
        }
        return { evaluation_status: "unavailable", score: null, verdict: "UNAVAILABLE", feedback: "Unavailable." };
      },
    },
  });

  await page.goto("/ml/practice");
  await page.getByRole("button", { name: "Generate AI Question" }).click();
  await expect(page.getByTestId("question")).toHaveText("Explain the bias-variance tradeoff.");

  await page.getByLabel("Your Answer").fill("Bias is underfitting, variance is overfitting.");
  await page.getByRole("button", { name: "Submit Answer" }).click();
  await expect(page.getByTestId("ml-result")).toContainText("7/10");

  await page.getByRole("button", { name: "Submit Answer" }).click();
  await expect(page.getByTestId("ml-result")).toContainText("Not scored");
  await expect(page.getByTestId("ml-result")).not.toContainText("0/10");
});

test("DSA practice: hidden-test run and verified submission", async ({ page }) => {
  await mockApi(page, {
    handlers: {
      "/api/dsa": (body) => {
        if (!body) return undefined;
        if (body.action === "generate") {
          return { problem: "Question ID: arr_001", problem_json: TWO_SUM_PROBLEM, tier: "verified" };
        }
        if (body.action === "run") {
          expect(body.question_id).toBe("arr_001");
          return {
            status: "finished", verdict: "Wrong Answer", passed: 2, total: 3,
            test_cases: [
              { status: "Passed", input: "[[2,7,11,15],9]", expected_output: "[0,1]", actual_output: "[0,1]", hidden: false },
              { status: "Failed", input: "[[3,2,4],6]", expected_output: "[1,2]", actual_output: "[0,1]", hidden: false },
              { status: "Passed", input: "Hidden test #3", expected_output: "hidden", actual_output: "hidden", hidden: true },
            ],
          };
        }
        if (body.action === "evaluate") {
          expect(body.save_attempt).toBe(true);
          return {
            evaluation_status: "completed", score: 10, status: "Passed", tier: "verified", scoring_method: "hidden_tests",
            judge: { status: "finished", verdict: "Accepted", passed: 3, total: 3 },
            test_cases: [{ status: "Passed", input: "[[2,7,11,15],9]", expected_output: "[0,1]", actual_output: "[0,1]" }],
            feedback: "Clean hash-map solution.", optimized_approach: "Hash map.", optimized_code: "class Solution: ...",
            explanation: "One pass.", time_complexity: "O(n)", space_complexity: "O(n)",
          };
        }
        return undefined;
      },
    },
  });

  await page.goto("/dsa/practice");
  await page.getByRole("button", { name: "Generate Problem" }).click();
  await expect(page.getByRole("heading", { name: "Two Sum" })).toBeVisible();
  await expect(page.getByText("✅ Verified", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "▶ Run Code" }).click();
  await expect(page.getByTestId("verdict")).toHaveText("Wrong Answer");
  await expect(page.getByText("2 / 3 testcases passed")).toBeVisible();
  await expect(page.getByText("Hidden test #3")).toHaveCount(0);

  await page.getByRole("tab", { name: /Code/ }).click();
  await page.getByRole("button", { name: "Submit", exact: true }).click();
  await expect(page.getByTestId("verdict")).toHaveText("Accepted");
  await expect(page.getByTestId("dsa-score")).toHaveText("10/10");
  await expect(page.getByText("Scored by hidden tests in the isolated judge")).toBeVisible();
});

test("DSA practice warns honestly when the judge is offline", async ({ page }) => {
  await mockApi(page, { judgeEnabled: false });
  await page.goto("/dsa/practice");
  await expect(page.getByText(/hidden-test judge is offline/i).first()).toBeVisible();
});

test("dashboard shows unscored attempts as Not scored and recovers from errors", async ({ page }) => {
  let fail = true;
  await mockApi(page, {
    handlers: {
      "/api/dashboard": () =>
        fail
          ? { status: 502, json: { error: "Backend unavailable.", detail: "The API server could not be reached." } }
          : {
              ml_practice: { total_attempts: 2, scored_attempts: 1, unavailable_attempts: 1, average_score: 8 },
              dsa_practice: {
                total_attempts: 0, scored_attempts: 0, unavailable_attempts: 0, average_score: 0,
                verified: { total_attempts: 0, scored_attempts: 0, average_score: 0 },
                ai_generated: { total_attempts: 0, scored_attempts: 0, average_score: 0 },
              },
              project_challenge: { total_attempts: 0, scored_attempts: 0, unavailable_attempts: 0, average_score: 0 },
              voice_interview: { total_interviews: 0, average_score: 0 },
              overall: { total_activity: 2, unavailable_attempts: 1 },
            },
      "/api/history?limit=50&offset=0": () => ({
        ml_practice: [
          { id: 1, topic: "KNN", score: 8, verdict: "STRONG", created_at: "2026-10-20T10:00:00Z" },
          { id: 2, topic: "KNN", score: null, verdict: "UNAVAILABLE", created_at: "2026-10-21T10:00:00Z" },
        ],
        dsa_practice: [], project_challenge: [], voice_interview: [],
      }),
    },
  });

  await page.goto("/dashboard");
  // Next.js also renders an empty role="alert" route announcer, so filter by text.
  await expect(page.getByRole("alert").filter({ hasText: "could not be reached" })).toBeVisible();

  fail = false;
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByTestId("overall-readiness")).toHaveText("80%");
  await expect(page.getByText("1 not scored (AI was unavailable)")).toBeVisible();
  await expect(page.getByText("Not scored").first()).toBeVisible();
});

test("Google sign-in button starts the OAuth flow when enabled", async ({ page, isMobile }) => {
  await mockApi(page, { auth: { google_oauth_enabled: true } });
  await page.route("**/api/auth/google/login**", (route) =>
    route.fulfill({ status: 200, contentType: "text/html", body: "<p>redirecting to google</p>" })
  );
  await page.goto("/dsa");
  if (isMobile) await page.getByRole("button", { name: "Menu" }).click();
  const loginRequest = page.waitForRequest("**/api/auth/google/login**");
  await page.getByRole("button", { name: "Sign in with Google" }).first().click();
  const request = await loginRequest;
  expect(new URL(request.url()).searchParams.get("return_to")).toBe("/dsa");
});
