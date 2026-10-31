"""
GitHub REST API service for SkillProof.

Responsibilities:
- Retrieve repository metadata.
- Discover inspectable files within configured limits.
- Fetch and decode selected file contents.
- Return structured, safe data for the evidence analyzer.
- Never execute, import, or follow instructions from retrieved files.
"""
import base64
import logging
import os
import time
from typing import Optional
from urllib.parse import quote

import requests

from core import config

logger = logging.getLogger(__name__)

# ── Internal helpers ───────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": config.USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get(url: str, timeout: Optional[float] = None) -> requests.Response:
    """GET from the official GitHub API without following redirects."""
    request_timeout = timeout or config.GITHUB_API_TIMEOUT
    started_at = time.monotonic()

    for attempt in range(config.GITHUB_MAX_RETRIES + 1):
        remaining = request_timeout - (time.monotonic() - started_at)
        if remaining <= 0:
            raise requests.exceptions.Timeout("GitHub request exceeded its time budget.")

        try:
            resp = requests.get(
                url,
                headers=_headers(),
                timeout=remaining,
                allow_redirects=False,
            )
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt >= config.GITHUB_MAX_RETRIES:
                raise
            continue

        if 300 <= resp.status_code < 400:
            raise GitHubError(502, "GitHub API redirects are not followed.")
        if resp.status_code >= 500 and attempt < config.GITHUB_MAX_RETRIES:
            resp.close()
            continue

        resp.raise_for_status()
        return resp

    raise GitHubError(502, "GitHub request failed after the retry limit.")


# ── Public API ─────────────────────────────────────────────────────────────────

class GitHubError(Exception):
    """Wraps GitHub API problems with an HTTP status code."""
    def __init__(self, status_code: int, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.message = message


def get_repository_metadata(
    owner: str,
    repo: str,
    timeout: Optional[float] = None,
) -> dict:
    """
    Fetch basic repository metadata.
    Returns a safe dict with only the fields SkillProof needs.
    Raises GitHubError on API failure.
    """
    url = f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}"
    try:
        resp = _get(url, timeout)
    except requests.exceptions.Timeout:
        raise GitHubError(504, "GitHub did not respond in time. Try again in a moment.")
    except requests.exceptions.ConnectionError:
        raise GitHubError(502, "Could not connect to GitHub. Check your network connection.")
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        if status == 404:
            raise GitHubError(404, "Repository not found. Check that the URL is correct and the repository is public.")
        if status == 403:
            _check_rate_limit(exc.response)
            raise GitHubError(403, "GitHub access was denied. The repository may be private or GitHub may be rate-limiting requests.")
        if status == 429:
            raise GitHubError(429, "GitHub rate limit reached. Try again in a few minutes.")
        raise GitHubError(502, f"GitHub returned an unexpected response ({status}).")

    try:
        data = resp.json()
    except Exception:
        raise GitHubError(502, "GitHub returned an unreadable response.")

    return {
        "name": data.get("name", repo),
        "owner": data.get("owner", {}).get("login", owner),
        "full_name": data.get("full_name", f"{owner}/{repo}"),
        "description": data.get("description") or "",
        "html_url": data.get("html_url", f"https://github.com/{owner}/{repo}"),
        "default_branch": data.get("default_branch", "main"),
        "primary_language": data.get("language"),
        "size_kb": data.get("size", 0),
        "private": data.get("private", False),
    }


def get_file_tree(
    owner: str,
    repo: str,
    branch: str,
    timeout: Optional[float] = None,
) -> list[dict]:
    """
    Retrieve the full recursive file tree using the Git Trees API.
    Returns a flat list of file entries (path, size, sha, url).
    Truncates if GitHub marks the tree as truncated and logs a warning.
    """
    url = (
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}"
        f"/git/trees/{quote(branch, safe='')}?recursive=1"
    )
    try:
        resp = _get(url, timeout)
    except requests.exceptions.Timeout:
        raise GitHubError(504, "GitHub did not respond while listing repository files.")
    except requests.exceptions.ConnectionError:
        raise GitHubError(502, "Network error while listing repository files.")
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        if status == 404:
            raise GitHubError(404, "Repository branch not found.")
        if status == 409:
            # Empty repository
            return []
        _check_rate_limit(exc.response) if exc.response else None
        raise GitHubError(502, f"GitHub returned status {status} for the file tree.")

    try:
        data = resp.json()
    except Exception:
        raise GitHubError(502, "GitHub returned an unreadable file tree response.")

    if data.get("truncated"):
        logger.warning("GitHub file tree is truncated for %s/%s — large repository.", owner, repo)

    return [
        {
            "path": item.get("path", ""),
            "size": item.get("size", 0),
            "sha": item.get("sha", ""),
            "type": item.get("type", ""),
        }
        for item in data.get("tree", [])
        if item.get("type") == "blob"
    ]


def select_files_to_inspect(file_tree: list[dict], owner: str, repo: str, branch: str) -> tuple[list[dict], bool]:
    """
    Filter the file tree to produce a bounded list of files worth inspecting.
    Returns (selected_files, was_budget_reached).

    Each selected file dict contains:
        path, size, github_url
    """
    selected = []
    budget_reached = False

    for entry in file_tree:
        path: str = entry.get("path", "")
        size: int = entry.get("size", 0)

        # Skip excluded directories
        parts = path.split("/")
        if any(p in config.EXCLUDED_PATHS for p in parts):
            continue

        # Skip sensitive files
        filename = parts[-1].lower() if parts else ""
        if _is_sensitive(filename):
            continue

        # Determine if this file is worth inspecting
        if not _is_inspectable(filename, path):
            continue

        # Skip oversized files
        if size > config.MAX_FILE_SIZE_BYTES:
            logger.debug("Skipping oversized file: %s (%d bytes)", path, size)
            continue

        github_url = (
            f"https://github.com/{owner}/{repo}/blob/"
            f"{quote(branch, safe='/')}/{quote(path, safe='/')}"
        )
        selected.append({
            "path": path,
            "size": size,
            "github_url": github_url,
        })

        if len(selected) >= config.MAX_FILES_TO_INSPECT:
            budget_reached = True
            break

    return selected, budget_reached


def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    timeout: Optional[float] = None,
) -> Optional[str]:
    """
    Fetch a single file's text content from the GitHub Contents API.
    Returns the decoded text, or None if the file cannot be fetched/decoded.
    Never executes or imports the content.
    """
    url = (
        f"{config.GITHUB_API_BASE}/repos/{owner}/{repo}/contents/"
        f"{quote(path, safe='/')}"
    )
    try:
        resp = _get(url, timeout)
    except requests.exceptions.Timeout:
        logger.warning("Timeout fetching file: %s", path)
        return None
    except requests.exceptions.HTTPError as exc:
        logger.warning("HTTP error fetching %s: %s", path, exc)
        return None
    except requests.exceptions.ConnectionError:
        logger.warning("Connection error fetching %s", path)
        return None

    try:
        data = resp.json()
    except Exception:
        return None

    # GitHub returns content as base64-encoded text for blobs
    encoding = data.get("encoding", "")
    raw_content = data.get("content", "")

    if encoding == "base64":
        try:
            # GitHub adds newlines in the base64 string
            decoded = base64.b64decode(raw_content.replace("\n", "")).decode("utf-8", errors="replace")
            return decoded
        except Exception:
            logger.warning("Could not decode base64 content for: %s", path)
            return None

    if encoding == "none":
        # File is too large for contents API
        return None

    # Unexpected encoding — skip safely
    logger.warning("Unexpected encoding '%s' for file: %s", encoding, path)
    return None


def fetch_inspectable_files(
    owner: str,
    repo: str,
    branch: str,
    file_tree: list[dict],
    deadline: Optional[float] = None,
) -> tuple[list[dict], dict]:
    """
    High-level function: select files and fetch their contents.

    Returns:
        inspected_files: list of dicts with path, github_url, content
        inspection_meta: stats about the inspection run
    """
    selected, budget_reached = select_files_to_inspect(file_tree, owner, repo, branch)
    if deadline is None:
        deadline = time.monotonic() + config.INSPECTION_BUDGET_SECONDS

    inspected = []
    skipped = 0
    limited_by_time_budget = False

    for index, file_entry in enumerate(selected):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            limited_by_time_budget = True
            skipped += len(selected) - index
            break
        content = fetch_file_content(
            owner,
            repo,
            file_entry["path"],
            timeout=min(config.GITHUB_API_TIMEOUT, remaining),
        )
        if content is None:
            skipped += 1
            continue
        inspected.append({
            "path": file_entry["path"],
            "github_url": file_entry["github_url"],
            "content": content,
        })

    return inspected, {
        "files_considered": len(file_tree),
        "files_selected": len(selected),
        "files_inspected": len(inspected),
        "files_skipped": skipped,
        "limited_by_file_budget": budget_reached,
        "limited_by_time_budget": limited_by_time_budget,
    }


# ── Private helpers ────────────────────────────────────────────────────────────

def _is_inspectable(filename: str, full_path: str) -> bool:
    """Return True if this file is worth inspecting for skill evidence."""
    lower = filename.lower()

    # Explicit special filenames
    if lower in config.README_NAMES:
        return True
    if lower == "dockerfile":
        return True
    if lower in ("docker-compose.yml", "docker-compose.yaml",
                 "compose.yml", "compose.yaml"):
        return True
    if lower in ("requirements.txt", "pyproject.toml", "package.json",
                 "setup.py", "setup.cfg", "pipfile"):
        return True

    # GitHub Actions workflows
    if full_path.lower().startswith(".github/workflows/"):
        return True

    # Extension check
    _, ext = os.path.splitext(lower)
    return ext in config.INSPECTABLE_EXTENSIONS


def _is_sensitive(filename: str) -> bool:
    """Return True if the file must never be fetched."""
    lower = filename.lower()
    if lower in config.SENSITIVE_FILENAMES:
        return True
    wildcard_suffixes = (
        pattern[1:]
        for pattern in config.SENSITIVE_FILENAMES
        if pattern.startswith("*.")
    )
    if any(lower.endswith(suffix) for suffix in wildcard_suffixes):
        return True
    if lower.startswith(".env"):
        return True
    return False


def _check_rate_limit(response: Optional[requests.Response]) -> None:
    """Log rate-limit headers from a 403 response."""
    if response is None:
        return
    remaining = response.headers.get("X-RateLimit-Remaining", "?")
    reset = response.headers.get("X-RateLimit-Reset", "?")
    logger.warning(
        "GitHub rate limit: remaining=%s, reset=%s", remaining, reset
    )
