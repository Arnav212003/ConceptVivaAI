from security import create_evaluation_receipt


def start_test_session(client):
    response = client.post("/session/start")

    assert response.status_code == 200

    data = response.json()

    return data, {
        "X-Session-Id": data["session_id"],
        "X-Session-Token": data["session_token"],
    }


def test_session_start_returns_credentials(client):
    data, _ = start_test_session(client)

    assert data["session_id"].startswith("cv_")
    assert data["session_token"]
    assert data["expires_in_seconds"] > 0


def test_dashboard_requires_valid_session(client):
    response = client.get("/dashboard-stats")

    assert response.status_code == 401
    assert response.json()["detail"] == "Missing session headers."


def test_dashboard_rejects_invalid_session_headers(client):
    response = client.get(
        "/dashboard-stats",
        headers={
            "X-Session-Id": "cv_invalid",
            "X-Session-Token": "invalid.token",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid or expired session."


def test_session_start_dashboard_and_logout_flow(client):
    _, headers = start_test_session(client)

    dashboard_response = client.get("/dashboard-stats", headers=headers)
    assert dashboard_response.status_code == 200
    assert dashboard_response.json()["overall"]["total_activity"] == 0

    logout_response = client.post("/session/logout", headers=headers)
    assert logout_response.status_code == 200
    assert logout_response.json()["revoked"] is True

    revoked_response = client.get("/dashboard-stats", headers=headers)
    assert revoked_response.status_code == 403
    assert revoked_response.json()["detail"] == "Session has been logged out or revoked."


def test_interview_report_accepts_only_signed_round_scores(client):
    session_data, headers = start_test_session(client)

    invalid_response = client.post(
        "/save-interview-report",
        headers=headers,
        json={
            "topic": "KNN",
            "level": "Easy",
            "rounds": 1,
            "average_score": 10,
            "evaluation_receipts": ["fake-receipt"],
        },
    )

    assert invalid_response.status_code == 400

    receipt = create_evaluation_receipt(
        session_id=session_data["session_id"],
        kind="interview_round",
        score=8.5,
        verdict="STRONG",
    )

    valid_response = client.post(
        "/save-interview-report",
        headers=headers,
        json={
            "topic": "KNN",
            "level": "Easy",
            "rounds": 1,
            "average_score": 0,
            "evaluation_receipts": [receipt],
        },
    )

    assert valid_response.status_code == 200

    report = valid_response.json()["report"]
    assert report["topic"] == "KNN"
    assert report["rounds"] == 1
    assert report["average_score"] == 8.5


def test_project_challenge_generates_reviews_and_updates_dashboard(client, monkeypatch):
    import routes.project_routes as project_routes

    def fake_generate_project_challenge(domain, topic, difficulty):
        return {
            "project_title": "Student KNN Project",
            "domain": domain,
            "topic": topic,
            "difficulty": difficulty,
            "problem_statement": "Build a small KNN classifier.",
            "dataset_columns": [],
            "tasks": ["Load data", "Train model", "Evaluate result"],
            "evaluation_metrics": ["Accuracy"],
            "hints": [],
            "submission_checklist": ["Code", "Result"],
        }

    def fake_evaluate_project_submission(**kwargs):
        return {
            "score": 8,
            "verdict": "STRONG",
            "feedback": "The submitted project covers the main flow.",
            "missing_points": "Add a confusion matrix.",
            "improved_approach": "Keep preprocessing and training separate.",
            "next_steps": "Add one more evaluation metric.",
            "suggested_resources": [],
            "architecture_review": "Simple and understandable.",
            "file_findings": [],
            "bugs": [],
            "security_issues": [],
            "missing_requirements": [],
            "files_reviewed": len(kwargs.get("project_files") or []),
        }

    monkeypatch.setattr(
        project_routes,
        "generate_project_challenge_with_gemini",
        fake_generate_project_challenge,
    )
    monkeypatch.setattr(
        project_routes,
        "evaluate_project_submission_with_gemini",
        fake_evaluate_project_submission,
    )

    _, headers = start_test_session(client)

    challenge_response = client.post(
        "/generate-project-challenge",
        headers=headers,
        json={
            "domain": "Machine Learning",
            "topic": "KNN",
            "difficulty": "Beginner",
        },
    )

    assert challenge_response.status_code == 200

    challenge_id = challenge_response.json()["challenge_id"]
    assert challenge_id.startswith("pch_")

    review_response = client.post(
        "/evaluate-project-submission",
        headers=headers,
        json={
            "challenge_id": challenge_id,
            "files": [
                {
                    "path": "main.py",
                    "content": "print('knn project')",
                }
            ],
            "project_notes": "Small demo project",
        },
    )

    assert review_response.status_code == 200

    review = review_response.json()
    assert review["score"] == 8.0
    assert review["saved_attempt"]["challenge_id"] == challenge_id
    assert review["saved_attempt"]["files_reviewed"] == 1

    dashboard_response = client.get("/dashboard-stats", headers=headers)
    project_stats = dashboard_response.json()["project_challenge"]

    assert project_stats["total_attempts"] == 1
    assert project_stats["active_challenges"] == 0
    assert project_stats["average_score"] == 8.0
