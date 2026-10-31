"""
API endpoint tests — all GitHub calls mocked so no network is needed.
"""
import json
import pytest
from unittest.mock import patch, MagicMock

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


MOCK_REPORT = {
    "repository": {"name": "Hello-World", "owner": "octocat", "full_name": "octocat/Hello-World",
                   "url": "https://github.com/octocat/Hello-World", "description": "",
                   "primary_language": "Python", "default_branch": "main"},
    "inspection": {"files_considered": 5, "files_selected": 3, "files_inspected": 3,
                   "files_skipped": 0, "limited_by_file_budget": False},
    "summary": {"selected_skills": 1, "skills_with_evidence": 1, "skills_needing_further_assessment": 0},
    "skills": [{"id": "python", "name": "Python", "status": "evidence_found",
                "explanation": "Evidence found.", "evidence": [], "recommended_next_steps": [],
                "limitations": [], "category": "Programming"}],
    "limitations": ["Only selected files were inspected."],
    "analysed_at": "2026-10-31T10:00:00+00:00",
}


# ── Health ─────────────────────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] == "ok"
    assert "service" in data


# ── Skills ─────────────────────────────────────────────────────────────────────

def test_skills_returns_catalogue(client):
    r = client.get("/api/skills")
    assert r.status_code == 200
    data = r.get_json()
    assert "skills" in data
    assert len(data["skills"]) > 0
    ids = [s["id"] for s in data["skills"]]
    assert "python" in ids
    assert "docker" in ids


def test_skills_have_required_fields(client):
    r = client.get("/api/skills")
    for skill in r.get_json()["skills"]:
        assert "id" in skill
        assert "name" in skill
        assert "category" in skill
        assert "description" in skill


def test_skills_returns_backend_selection_limit(client):
    r = client.get("/api/skills")
    assert r.get_json()["max_per_request"] == 8


# ── Analyze ────────────────────────────────────────────────────────────────────

def test_analyze_valid_request(client):
    with patch("services.report_builder.build_report", return_value=MOCK_REPORT):
        r = client.post("/api/analyze",
                        data=json.dumps({"repository_url": "https://github.com/octocat/Hello-World",
                                         "skills": ["python"]}),
                        content_type="application/json")
    assert r.status_code == 200
    data = r.get_json()
    assert "skills" in data
    assert "summary" in data
    assert "repository" in data


def test_analyze_invalid_url(client):
    r = client.post("/api/analyze",
                    data=json.dumps({"repository_url": "not-a-url", "skills": ["python"]}),
                    content_type="application/json")
    assert r.status_code == 400
    data = r.get_json()
    assert "error" in data
    assert "code" in data["error"]


def test_analyze_profile_url_rejected(client):
    r = client.post("/api/analyze",
                    data=json.dumps({"repository_url": "https://github.com/octocat",
                                     "skills": ["python"]}),
                    content_type="application/json")
    assert r.status_code == 400


def test_analyze_no_skills(client):
    r = client.post("/api/analyze",
                    data=json.dumps({"repository_url": "https://github.com/octocat/Hello-World",
                                     "skills": []}),
                    content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "NO_SKILLS"


def test_analyze_unsupported_skill(client):
    r = client.post("/api/analyze",
                    data=json.dumps({"repository_url": "https://github.com/octocat/Hello-World",
                                     "skills": ["blockchain_magic"]}),
                    content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "UNSUPPORTED_SKILL"


def test_analyze_too_many_skills(client):
    skills = ["python", "javascript", "sql", "docker", "flask", "html", "css", "vuejs", "aws"]
    r = client.post("/api/analyze",
                    data=json.dumps({"repository_url": "https://github.com/octocat/Hello-World",
                                     "skills": skills}),
                    content_type="application/json")
    assert r.status_code == 400
    assert r.get_json()["error"]["code"] == "TOO_MANY_SKILLS"


def test_analyze_not_json(client):
    r = client.post("/api/analyze", data="not json", content_type="text/plain")
    assert r.status_code == 400


def test_analyze_repo_not_found(client):
    from services.github_service import GitHubError
    with patch("services.report_builder.build_report",
               side_effect=GitHubError(404, "Repository not found.")):
        r = client.post("/api/analyze",
                        data=json.dumps({"repository_url": "https://github.com/nobody/norepo",
                                         "skills": ["python"]}),
                        content_type="application/json")
    assert r.status_code == 404
    assert r.get_json()["error"]["code"] == "REPOSITORY_NOT_FOUND"


def test_analyze_rate_limited(client):
    from services.github_service import GitHubError
    with patch("services.report_builder.build_report",
               side_effect=GitHubError(429, "Rate limit reached.")):
        r = client.post("/api/analyze",
                        data=json.dumps({"repository_url": "https://github.com/octocat/Hello-World",
                                         "skills": ["python"]}),
                        content_type="application/json")
    assert r.status_code == 429


def test_analyze_response_structure(client):
    with patch("services.report_builder.build_report", return_value=MOCK_REPORT):
        r = client.post("/api/analyze",
                        data=json.dumps({"repository_url": "https://github.com/octocat/Hello-World",
                                         "skills": ["python"]}),
                        content_type="application/json")
    data = r.get_json()
    assert "repository" in data
    assert "inspection" in data
    assert "summary" in data
    assert "skills" in data
    assert "limitations" in data
