"""
SkillProof Flask API
Entry point: python app.py  (or flask run from backend/)
"""
import logging

from flask import Flask, jsonify, request
from flask_cors import CORS

from core import config
from core.skills_catalogue import SKILLS
from core.validation import ValidationError, validate_repository_url, validate_skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app, origins=config.CORS_ORIGINS)

# ── Error helpers ──────────────────────────────────────────────────────────────

def error_response(code: str, message: str, http_status: int):
    return jsonify({"error": {"code": code, "message": message}}), http_status


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return jsonify({"status": "ok", "service": "SkillProof API"})


@app.get("/api/skills")
def skills():
    """Return the supported skill catalogue."""
    return jsonify({
        "skills": SKILLS,
        "max_per_request": config.MAX_SKILLS_PER_REQUEST,
    })


@app.post("/api/analyze")
def analyze():
    """
    POST /api/analyze
    Body: { "repository_url": "...", "skills": ["python", "docker", ...] }
    Returns the full evidence report.
    """
    # Parse JSON body
    if not request.is_json:
        return error_response("INVALID_CONTENT_TYPE", "Request must be JSON.", 400)

    try:
        body = request.get_json(force=False, silent=False)
    except Exception:
        return error_response("INVALID_JSON", "Could not parse the request body as JSON.", 400)

    if not isinstance(body, dict):
        return error_response("INVALID_BODY", "Request body must be a JSON object.", 400)

    # Validate inputs
    try:
        owner, repo = validate_repository_url(body.get("repository_url", ""))
        skill_ids = validate_skills(body.get("skills", []))
    except ValidationError as exc:
        return error_response(exc.code, exc.message, 400)

    # Run the analysis pipeline
    try:
        from services.report_builder import build_report
        report = build_report(owner, repo, skill_ids)
        return jsonify(report), 200

    except Exception as exc:
        # Import here to avoid circular issues at startup
        try:
            from services.github_service import GitHubError
            if isinstance(exc, GitHubError):
                if exc.status_code == 404:
                    return error_response("REPOSITORY_NOT_FOUND", exc.message, 404)
                if exc.status_code in (403, 429):
                    return error_response("GITHUB_RATE_LIMITED", exc.message, 429)
                if exc.status_code == 504:
                    return error_response("GITHUB_TIMEOUT", exc.message, 504)
                return error_response("GITHUB_ERROR", exc.message, 502)
        except ImportError:
            pass

        logger.exception("Unexpected error during analysis of %s/%s", owner, repo)
        return error_response(
            "INTERNAL_ERROR",
            "An unexpected error occurred. Please try again.",
            500,
        )


# ── Global error handlers ──────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(_):
    return error_response("NOT_FOUND", "Endpoint not found.", 404)


@app.errorhandler(405)
def method_not_allowed(_):
    return error_response("METHOD_NOT_ALLOWED", "Method not allowed.", 405)


@app.errorhandler(413)
def request_too_large(_):
    return error_response("REQUEST_TOO_LARGE", "Request body is too large.", 413)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
