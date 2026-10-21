"""Locust load test for the ConceptVivaAI backend.

Default run (no AI calls, safe to run any time):
    locust -f loadtests/locustfile.py --host http://127.0.0.1:8000 \
        --headless -u 50 -r 10 -t 60s --csv loadtests/results/local

Include AI endpoints (billable Gemini calls when GEMINI_API_KEY is set on the server):
    locust ... --tags ai core

Start the server with DISABLE_RATE_LIMITING=true for throughput runs, otherwise
most requests are (correctly) rejected with 429 once each session hits its limit.
"""
import random

from locust import HttpUser, between, tag, task

TOPICS = ["Arrays", "Strings", "Stack", "Binary Search", "Trees", "Graphs", "Dynamic Programming"]


class GuestUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        response = self.client.post("/session/start", name="/session/start")
        data = response.json()
        self.headers = {
            "X-Session-Id": data["session_id"],
            "X-Session-Token": data["session_token"],
        }

    @tag("core")
    @task(4)
    def dashboard(self):
        self.client.get("/dashboard-stats", headers=self.headers, name="/dashboard-stats")

    @tag("core")
    @task(2)
    def history(self):
        self.client.get("/history?limit=20&offset=0", headers=self.headers, name="/history")

    @tag("core")
    @task(2)
    def bank_stats(self):
        self.client.get("/dsa-question-bank/stats", name="/dsa-question-bank/stats")

    @tag("core")
    @task(1)
    def mock_set(self):
        self.client.post(
            "/generate-dsa-mock-set",
            headers=self.headers,
            json={"topic": random.choice(TOPICS), "difficulty": "Mixed", "count": 10},
            name="/generate-dsa-mock-set",
        )

    @tag("core")
    @task(1)
    def health(self):
        self.client.get("/health", name="/health")

    @tag("ai")
    @task(1)
    def evaluate_answer(self):
        self.client.post(
            "/evaluate-answer",
            headers=self.headers,
            json={
                "topic": "KNN",
                "level": "Easy",
                "question": "What is KNN?",
                "answer": "KNN predicts using the majority label of the k nearest neighbours.",
                "mode": "practice",
                "save_attempt": True,
            },
            name="/evaluate-answer",
        )
