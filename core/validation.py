"""
Input validation for the SkillProof API.
All URL and skill validation happens here — never in frontend components.
"""
import re
from urllib.parse import urlparse
from typing import Tuple

from core.config import MAX_SKILLS_PER_REQUEST
from core.skills_catalogue import VALID_SKILL_IDS

# Only allow standard github.com (not lookalikes, not GitHub Enterprise)
_ALLOWED_HOSTNAME = "github.com"

# Owner and repo names follow GitHub's own rules
_SEGMENT_RE = re.compile(r'^[A-Za-z0-9_.\-]+$')


class ValidationError(Exception):
    """Raised when user-supplied input fails validation."""
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_repository_url(raw_url: str) -> Tuple[str, str]:
    """
    Validate a GitHub repository URL.
    Returns (owner, repo) on success.
    Raises ValidationError on any problem.

    Rules:
    - Must be a non-empty string.
    - Must use https scheme only.
    - Must use github.com hostname exactly.
    - Must not carry user-info credentials.
    - Must not specify a non-standard port.
    - Must have exactly two path segments: /owner/repo.
    - Owner and repo must match GitHub naming rules.
    - Strips an optional trailing .git suffix from the repo name.
    """
    if not raw_url or not isinstance(raw_url, str):
        raise ValidationError(
            "EMPTY_URL",
            "Enter a GitHub repository URL."
        )

    url = raw_url.strip()

    try:
        parsed = urlparse(url)
    except Exception:
        raise ValidationError("MALFORMED_URL", "The URL could not be parsed.")

    # Scheme
    if parsed.scheme != "https":
        raise ValidationError(
            "INVALID_SCHEME",
            "The repository URL must use HTTPS (e.g. https://github.com/owner/repo)."
        )

    # No credentials embedded in the URL
    if "@" in parsed.netloc:
        raise ValidationError(
            "URL_CREDENTIALS",
            "The URL must not contain login credentials."
        )

    # Hostname — exact match only
    hostname = (parsed.hostname or "").lower()
    if hostname != _ALLOWED_HOSTNAME:
        raise ValidationError(
            "INVALID_HOST",
            "Enter a public GitHub repository URL (github.com)."
        )

    # No non-standard port
    try:
        port = parsed.port
    except ValueError:
        raise ValidationError(
            "UNEXPECTED_PORT",
            "The URL must not specify a port number."
        )
    if port is not None:
        raise ValidationError(
            "UNEXPECTED_PORT",
            "The URL must not specify a port number."
        )

    # Path: /owner/repo or /owner/repo.git — nothing else
    path = parsed.path.rstrip("/")
    # Strip .git suffix if present
    if path.endswith(".git"):
        path = path[:-4]

    parts = [p for p in path.split("/") if p]

    if len(parts) < 2:
        raise ValidationError(
            "MISSING_REPOSITORY",
            "The URL looks like a GitHub profile. Add a repository name: "
            "https://github.com/username/repository"
        )

    if len(parts) > 2:
        raise ValidationError(
            "INVALID_REPOSITORY_PATH",
            "Enter a top-level repository URL: https://github.com/owner/repo"
        )

    owner, repo = parts[0], parts[1]

    if owner in {".", ".."} or not _SEGMENT_RE.match(owner):
        raise ValidationError("INVALID_OWNER", "The repository owner name is not valid.")

    if repo in {".", ".."} or not _SEGMENT_RE.match(repo):
        raise ValidationError("INVALID_REPO", "The repository name is not valid.")

    return owner, repo


def validate_skills(skills: object) -> list:
    """
    Validate the skills list from the request body.
    Returns a list of valid skill IDs.
    Raises ValidationError on any problem.
    """
    if not isinstance(skills, list):
        raise ValidationError("INVALID_SKILLS_TYPE", "Skills must be a list.")

    if len(skills) == 0:
        raise ValidationError("NO_SKILLS", "Select at least one skill to analyse.")

    if len(skills) > MAX_SKILLS_PER_REQUEST:
        raise ValidationError(
            "TOO_MANY_SKILLS",
            f"Select up to {MAX_SKILLS_PER_REQUEST} skills per analysis."
        )

    for item in skills:
        if not isinstance(item, str):
            raise ValidationError("INVALID_SKILL_ID", "Each skill must be a string identifier.")
        if item not in VALID_SKILL_IDS:
            raise ValidationError(
                "UNSUPPORTED_SKILL",
                f"'{item}' is not a supported skill. Fetch the skill list from /api/skills."
            )

    # Deduplicate while preserving order
    seen = set()
    result = []
    for s in skills:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result
