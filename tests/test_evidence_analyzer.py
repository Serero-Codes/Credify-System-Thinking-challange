"""
Tests for the evidence analyzer using synthetic fixture content.
No real repositories or network requests are used.
"""
import pytest
from services.evidence_analyzer import (
    analyze,
    STATUS_FOUND,
    STATUS_NOT_FOUND,
    STATUS_NEEDS_ASSESSMENT,
    STATUS_INCOMPLETE,
)


def make_file(path: str, content: str) -> dict:
    return {
        "path": path,
        "github_url": f"https://github.com/test/repo/blob/main/{path}",
        "content": content,
    }


META = {
    "name": "test-repo",
    "owner": "test-user",
    "full_name": "test-user/test-repo",
    "html_url": "https://github.com/test-user/test-repo",
    "description": "Test repository",
    "primary_language": "Python",
    "default_branch": "main",
}

INSPECTION_META = {
    "files_considered": 10,
    "files_selected": 5,
    "files_inspected": 5,
    "files_skipped": 0,
    "limited_by_file_budget": False,
}


def run(files, skills):
    return analyze(META, files, INSPECTION_META, skills)


# ── Python ─────────────────────────────────────────────────────────────────────

def test_python_evidence_found():
    files = [make_file("app.py", "import flask\nfrom flask import Flask\n\ndef create_app():\n    app = Flask(__name__)\n    return app\n")]
    result = run(files, ["python"])
    skill = result["skills"][0]
    assert skill["status"] == STATUS_FOUND
    assert skill["evidence"]
    assert skill["evidence"][0]["file_path"] == "app.py"


def test_python_not_found():
    files = [make_file("readme.md", "This project uses Python.")]
    result = run(files, ["python"])
    skill = result["skills"][0]
    assert skill["status"] == STATUS_NOT_FOUND
    assert not skill["evidence"]


def test_python_readme_mention_not_equal_to_source_code():
    """A README mentioning Python should NOT receive evidence_found status."""
    files = [
        make_file("README.md", "# My Project\n\nBuilt with Python 3.11."),
    ]
    result = run(files, ["python"])
    assert result["skills"][0]["status"] == STATUS_NOT_FOUND


# ── SQL ────────────────────────────────────────────────────────────────────────

def test_sql_evidence_found_in_sql_file():
    files = [make_file("schema.sql", "CREATE TABLE users (\n  id INT PRIMARY KEY,\n  name VARCHAR(100)\n);\nSELECT * FROM users WHERE id = 1;\n")]
    result = run(files, ["sql"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_sql_evidence_found_in_python_file():
    files = [make_file("db.py", 'conn.execute("SELECT id, name FROM products WHERE active = 1")\n')]
    result = run(files, ["sql"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_sql_not_found():
    files = [make_file("models.py", "class User:\n    pass\n")]
    result = run(files, ["sql"])
    assert result["skills"][0]["status"] == STATUS_NOT_FOUND


# ── REST APIs ──────────────────────────────────────────────────────────────────

def test_rest_api_flask_route():
    files = [make_file("routes.py", "@app.route('/api/users', methods=['GET'])\ndef get_users():\n    return jsonify(users)\n")]
    result = run(files, ["rest_apis"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_rest_api_express():
    files = [make_file("server.js", "app.get('/api/health', (req, res) => { res.json({ status: 'ok' }); });\n")]
    result = run(files, ["rest_apis"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_rest_api_not_found():
    files = [make_file("utils.py", "def add(a, b):\n    return a + b\n")]
    result = run(files, ["rest_apis"])
    assert result["skills"][0]["status"] == STATUS_NOT_FOUND


# ── Docker ─────────────────────────────────────────────────────────────────────

def test_docker_evidence_found():
    files = [make_file("Dockerfile", "FROM python:3.12-slim\nWORKDIR /app\nCOPY . .\nRUN pip install -r requirements.txt\nCMD [\"python\", \"app.py\"]\n")]
    result = run(files, ["docker"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_docker_compose_evidence_found():
    files = [make_file("docker-compose.yml", "version: '3'\nservices:\n  web:\n    build: .\n    ports:\n      - '5000:5000'\n")]
    result = run(files, ["docker"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_docker_not_found():
    files = [make_file("app.py", "print('hello')\n")]
    result = run(files, ["docker"])
    assert result["skills"][0]["status"] == STATUS_NOT_FOUND


# ── Terraform ──────────────────────────────────────────────────────────────────

def test_terraform_evidence_found():
    files = [make_file("main.tf", 'provider "aws" {\n  region = "us-east-1"\n}\n\nresource "aws_s3_bucket" "data" {\n  bucket = "my-bucket"\n}\n')]
    result = run(files, ["terraform"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_terraform_not_found():
    files = [make_file("README.md", "This project uses Terraform.")]
    result = run(files, ["terraform"])
    assert result["skills"][0]["status"] == STATUS_NOT_FOUND


# ── Vue.js ─────────────────────────────────────────────────────────────────────

def test_vue_evidence_found():
    files = [make_file("src/App.vue", "<template>\n  <div>Hello</div>\n</template>\n<script setup>\nimport { ref } from 'vue';\n</script>\n")]
    result = run(files, ["vuejs"])
    assert result["skills"][0]["status"] == STATUS_FOUND


# ── Automated testing ──────────────────────────────────────────────────────────

def test_automated_testing_evidence_found():
    files = [make_file("tests/test_app.py", "import pytest\n\ndef test_health():\n    assert True\n\ndef test_add():\n    assert 1 + 1 == 2\n")]
    result = run(files, ["automated_testing"])
    assert result["skills"][0]["status"] == STATUS_FOUND


def test_automated_testing_not_found():
    files = [make_file("app.py", "def main():\n    pass\n")]
    result = run(files, ["automated_testing"])
    assert result["skills"][0]["status"] == STATUS_NOT_FOUND


# ── CI/CD ──────────────────────────────────────────────────────────────────────

def test_cicd_github_actions_found():
    files = [make_file(".github/workflows/ci.yml",
        "name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - run: pytest\n")]
    result = run(files, ["cicd"])
    assert result["skills"][0]["status"] == STATUS_FOUND


# ── Summary consistency ────────────────────────────────────────────────────────

def test_summary_counts_match_skill_results():
    files = [
        make_file("app.py", "import flask\ndef run():\n    pass\n"),
        make_file("Dockerfile", "FROM python:3.12\nCMD python app.py\n"),
    ]
    result = run(files, ["python", "docker", "sql"])
    summary = result["summary"]
    skills = result["skills"]
    found = sum(1 for s in skills if s["status"] == STATUS_FOUND)
    assert summary["skills_with_evidence"] == found
    assert summary["selected_skills"] == 3
    assert summary["skills_needing_further_assessment"] == 3 - found


def test_failed_inspection_not_treated_as_missing_evidence():
    """If no files were inspected, status should be incomplete, not not_found."""
    empty_meta = {**INSPECTION_META, "files_inspected": 0}
    result = analyze(META, [], empty_meta, ["python"])
    skill = result["skills"][0]
    assert skill["status"] == STATUS_INCOMPLETE


def test_limited_inspection_does_not_report_missing_evidence():
    limited_meta = {
        **INSPECTION_META,
        "files_skipped": 1,
        "limited_by_time_budget": True,
    }
    result = analyze(META, [make_file("utils.py", "def add(a, b): return a + b")],
                     limited_meta, ["docker"])
    assert result["skills"][0]["status"] == STATUS_INCOMPLETE


def test_evidence_items_have_required_fields():
    files = [make_file("app.py", "import flask\napp = Flask(__name__)\n@app.route('/')\ndef index(): pass\n")]
    result = run(files, ["python"])
    skill = result["skills"][0]
    if skill["evidence"]:
        for ev in skill["evidence"]:
            assert "file_path" in ev
            assert "file_url" in ev
            assert "evidence_type" in ev
            assert "description" in ev


def test_global_limitations_always_present():
    result = run([], ["python"])
    assert isinstance(result["limitations"], list)
    assert len(result["limitations"]) > 0
