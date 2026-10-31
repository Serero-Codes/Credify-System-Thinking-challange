"""
Tests for github_service.py — all HTTP calls are mocked.
No real network requests are made.
"""
import base64
import json
import pytest
from unittest.mock import patch, MagicMock
import requests

from services.github_service import (
    get_repository_metadata,
    get_file_tree,
    fetch_file_content,
    select_files_to_inspect,
    GitHubError,
)


def mock_response(status_code: int, data=None, headers=None):
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = headers or {}
    if data is not None:
        resp.json.return_value = data
    if status_code >= 400:
        http_error = requests.exceptions.HTTPError(response=resp)
        resp.raise_for_status.side_effect = http_error
    else:
        resp.raise_for_status.return_value = None
    return resp


def b64(text: str) -> str:
    return base64.b64encode(text.encode()).decode()


# ── Repository metadata ────────────────────────────────────────────────────────

class TestGetRepositoryMetadata:
    def test_success(self):
        data = {
            "name": "Hello-World",
            "owner": {"login": "octocat"},
            "full_name": "octocat/Hello-World",
            "description": "My first repo",
            "html_url": "https://github.com/octocat/Hello-World",
            "default_branch": "main",
            "language": "Python",
            "size": 42,
            "private": False,
        }
        with patch("requests.get", return_value=mock_response(200, data)):
            meta = get_repository_metadata("octocat", "Hello-World")
        assert meta["name"] == "Hello-World"
        assert meta["owner"] == "octocat"
        assert meta["primary_language"] == "Python"
        assert meta["default_branch"] == "main"

    def test_repository_not_found(self):
        with patch("requests.get", return_value=mock_response(404)):
            with pytest.raises(GitHubError) as exc:
                get_repository_metadata("nobody", "does-not-exist")
        assert exc.value.status_code == 404

    def test_rate_limited(self):
        with patch("requests.get", return_value=mock_response(403, headers={"X-RateLimit-Remaining": "0"})):
            with pytest.raises(GitHubError) as exc:
                get_repository_metadata("octocat", "Hello-World")
        assert exc.value.status_code == 403

    def test_timeout(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout):
            with pytest.raises(GitHubError) as exc:
                get_repository_metadata("octocat", "Hello-World")
        assert exc.value.status_code == 504

    def test_connection_error(self):
        with patch("requests.get", side_effect=requests.exceptions.ConnectionError):
            with pytest.raises(GitHubError) as exc:
                get_repository_metadata("octocat", "Hello-World")
        assert exc.value.status_code == 502


# ── File tree ──────────────────────────────────────────────────────────────────

class TestGetFileTree:
    def test_success(self):
        data = {
            "truncated": False,
            "tree": [
                {"path": "app.py", "type": "blob", "size": 500, "sha": "abc"},
                {"path": "tests/test_app.py", "type": "blob", "size": 200, "sha": "def"},
                {"path": "src", "type": "tree", "size": 0, "sha": "ghi"},
            ]
        }
        with patch("requests.get", return_value=mock_response(200, data)):
            tree = get_file_tree("octocat", "Hello-World", "main")
        # Only blobs returned
        assert len(tree) == 2
        paths = [f["path"] for f in tree]
        assert "app.py" in paths
        assert "tests/test_app.py" in paths

    def test_empty_repository(self):
        with patch("requests.get", return_value=mock_response(409)):
            tree = get_file_tree("octocat", "empty-repo", "main")
        assert tree == []

    def test_malformed_response(self):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = 200
        resp.raise_for_status.return_value = None
        resp.json.side_effect = ValueError("bad json")
        with patch("requests.get", return_value=resp):
            with pytest.raises(GitHubError) as exc:
                get_file_tree("octocat", "Hello-World", "main")
        assert exc.value.status_code == 502


# ── File content ───────────────────────────────────────────────────────────────

class TestFetchFileContent:
    def test_successful_decode(self):
        text = "import flask\napp = Flask(__name__)\n"
        data = {"encoding": "base64", "content": b64(text) + "\n"}
        with patch("requests.get", return_value=mock_response(200, data)):
            content = fetch_file_content("octocat", "Hello-World", "app.py")
        assert content == text

    def test_missing_file_returns_none(self):
        with patch("requests.get", return_value=mock_response(404)):
            content = fetch_file_content("octocat", "Hello-World", "missing.py")
        assert content is None

    def test_timeout_returns_none(self):
        with patch("requests.get", side_effect=requests.exceptions.Timeout):
            content = fetch_file_content("octocat", "Hello-World", "app.py")
        assert content is None

    def test_encoding_none_returns_none(self):
        """Files too large for the contents API return encoding: none."""
        data = {"encoding": "none", "content": ""}
        with patch("requests.get", return_value=mock_response(200, data)):
            content = fetch_file_content("octocat", "Hello-World", "huge.py")
        assert content is None

    def test_invalid_base64_returns_none(self):
        data = {"encoding": "base64", "content": "!!!not valid base64!!!"}
        with patch("requests.get", return_value=mock_response(200, data)):
            content = fetch_file_content("octocat", "Hello-World", "app.py")
        assert content is None


# ── File selection ─────────────────────────────────────────────────────────────

class TestSelectFilesToInspect:
    def _tree(self, entries):
        return [{"path": p, "size": s, "sha": "x", "type": "blob"} for p, s in entries]

    def test_excludes_node_modules(self):
        tree = self._tree([("node_modules/lodash/index.js", 100), ("src/app.js", 200)])
        selected, _ = select_files_to_inspect(tree, "u", "r", "main")
        paths = [f["path"] for f in selected]
        assert "node_modules/lodash/index.js" not in paths
        assert "src/app.js" in paths

    def test_excludes_oversized_files(self):
        tree = self._tree([("huge.py", 200_000), ("small.py", 100)])
        selected, _ = select_files_to_inspect(tree, "u", "r", "main")
        paths = [f["path"] for f in selected]
        assert "huge.py" not in paths
        assert "small.py" in paths

    def test_excludes_env_files(self):
        tree = self._tree([(".env", 50), ("app.py", 100)])
        selected, _ = select_files_to_inspect(tree, "u", "r", "main")
        paths = [f["path"] for f in selected]
        assert ".env" not in paths

    def test_includes_dockerfile(self):
        tree = self._tree([("Dockerfile", 500)])
        selected, _ = select_files_to_inspect(tree, "u", "r", "main")
        assert len(selected) == 1
        assert selected[0]["path"] == "Dockerfile"

    def test_includes_github_workflows(self):
        tree = self._tree([(".github/workflows/ci.yml", 300)])
        selected, _ = select_files_to_inspect(tree, "u", "r", "main")
        assert len(selected) == 1

    def test_excludes_pfx_files(self):
        tree = self._tree([("certificates/signing.pfx", 100), ("app.py", 100)])
        selected, _ = select_files_to_inspect(tree, "u", "r", "main")
        assert [entry["path"] for entry in selected] == ["app.py"]

    def test_github_requests_do_not_follow_redirects(self):
        from services.github_service import _get

        with patch("requests.get", return_value=mock_response(302)):
            with pytest.raises(GitHubError) as exc:
                _get("https://api.github.com/repos/octocat/Hello-World")
        assert exc.value.status_code == 502

    def test_jsx_files_are_inspectable(self):
        tree = self._tree([("src/App.jsx", 100)])
        selected, _ = select_files_to_inspect(tree, "u", "r", "main")
        assert [entry["path"] for entry in selected] == ["src/App.jsx"]

    def test_fetch_respects_overall_time_budget(self):
        from services.github_service import fetch_inspectable_files

        tree = self._tree([("one.py", 100), ("two.py", 100)])
        with patch("services.github_service.time.monotonic", side_effect=[99, 101]):
            with patch(
                "services.github_service.fetch_file_content",
                return_value="def found(): pass",
            ) as fetch_content:
                inspected, metadata = fetch_inspectable_files(
                    "u", "r", "main", tree, deadline=100
                )

        assert len(inspected) == 1
        assert fetch_content.call_count == 1
        assert metadata["files_skipped"] == 1
        assert metadata["limited_by_time_budget"] is True

    def test_file_budget_enforced(self):
        from core import config
        tree = self._tree([(f"file{i}.py", 100) for i in range(50)])
        selected, budget_reached = select_files_to_inspect(tree, "u", "r", "main")
        assert len(selected) <= config.MAX_FILES_TO_INSPECT
        assert budget_reached is True
