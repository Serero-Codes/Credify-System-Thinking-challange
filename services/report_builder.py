"""
Thin layer that calls the GitHub service and evidence analyzer
and packages the final report for the API response.
"""
import logging
import time
from datetime import datetime, timezone

from core import config
from services.github_service import (
    GitHubError,
    fetch_inspectable_files,
    get_file_tree,
    get_repository_metadata,
)
from services.evidence_analyzer import analyze

logger = logging.getLogger(__name__)


def _request_timeout(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise GitHubError(504, "The repository inspection time budget was exceeded.")
    return min(config.GITHUB_API_TIMEOUT, remaining)


def build_report(
    owner: str,
    repo: str,
    selected_skill_ids: list,
) -> dict:
    """
    Orchestrate the full analysis pipeline:
    1. Fetch repository metadata.
    2. Retrieve file tree.
    3. Fetch inspectable file contents.
    4. Run the evidence analyzer.
    5. Return the complete report.

    Raises:
        github_service.GitHubError for any GitHub API failure.
    """
    deadline = time.monotonic() + config.INSPECTION_BUDGET_SECONDS

    # Step 1: repository metadata
    logger.info("Fetching metadata for %s/%s", owner, repo)
    metadata = get_repository_metadata(owner, repo, timeout=_request_timeout(deadline))
    branch = metadata.get("default_branch", "main")

    # Step 2: file tree
    logger.info("Fetching file tree for %s/%s @ %s", owner, repo, branch)
    file_tree = get_file_tree(
        owner,
        repo,
        branch,
        timeout=_request_timeout(deadline),
    )

    # Step 3: fetch file contents within limits
    logger.info("Fetching file contents (%d entries in tree)", len(file_tree))
    inspected_files, inspection_meta = fetch_inspectable_files(
        owner, repo, branch, file_tree, deadline=deadline
    )

    # Step 4: analyze
    logger.info("Running evidence analyzer for skills: %s", selected_skill_ids)
    report = analyze(metadata, inspected_files, inspection_meta, selected_skill_ids)

    # Add analysis timestamp
    report["analysed_at"] = datetime.now(timezone.utc).isoformat()

    return report
