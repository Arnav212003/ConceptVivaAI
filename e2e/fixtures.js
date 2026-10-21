// Network-level mocks for the Next.js /api routes, so E2E tests are deterministic
// and need neither the FastAPI backend nor a Gemini key.
export const TWO_SUM_PROBLEM = {
  question_id: "arr_001",
  title: "Two Sum",
  topic: "Arrays",
  difficulty: "Easy",
  pattern: "Hash Map",
  description: "Given an array of integers nums and an integer target, return indices of the two numbers.",
  examples: [{ input: "nums = [2,7,11,15], target = 9", output: "[0,1]", explanation: "2 + 7 = 9" }],
  constraints: ["2 <= nums.length <= 10^4"],
  follow_up: "",
  starter_code: "class Solution:\n    def twoSum(self, nums, target):\n        pass",
  generated_by: "ai",
};

export async function mockApi(page, { auth = {}, judgeEnabled = true, handlers = {} } = {}) {
  await page.route("**/api/session", (route) =>
    route.fulfill({ json: { session_id: "cv_e2e", session_token: "1.sig", expires_in_seconds: 3600 } })
  );
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({ json: { authenticated: false, user: null, google_oauth_enabled: false, ...auth } })
  );
  await page.route("**/api/analytics", (route) => route.fulfill({ status: 202, json: { recorded: true } }));
  await page.route("**/api/progress", (route) =>
    route.fulfill({
      json: {
        current_streak_days: 2,
        active_days_last_30: 4,
        weeks: [{ week_start: "2026-10-19", attempts: 2, average_score: 8 }],
      },
    })
  );
  await page.route("**/api/dsa?resource=bank-stats", (route) =>
    route.fulfill({ json: { total: 90, hidden_tests_enabled: judgeEnabled } })
  );

  for (const [path, handler] of Object.entries(handlers)) {
    await page.route(`**${path}`, async (route) => {
      const request = route.request();
      const body = request.method() === "POST" ? request.postDataJSON() : null;
      const result = await handler(body, request);
      if (result === undefined) return route.continue();
      const { status = 200, json } = result.json !== undefined ? result : { json: result };
      return route.fulfill({ status, json });
    });
  }
}
