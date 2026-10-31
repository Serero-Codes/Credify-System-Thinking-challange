"""
SkillProof backend configuration.
All environment-specific values are read from environment variables
with sensible defaults for local development.
"""
import os

# GitHub API
GITHUB_API_BASE = "https://api.github.com"
GITHUB_API_TIMEOUT = int(os.getenv("GITHUB_API_TIMEOUT", "15"))
INSPECTION_BUDGET_SECONDS = int(os.getenv("INSPECTION_BUDGET_SECONDS", "60"))
GITHUB_MAX_RETRIES = 1

# Inspection limits
MAX_FILES_TO_INSPECT = int(os.getenv("MAX_FILES_TO_INSPECT", "30"))
MAX_FILE_SIZE_BYTES = int(os.getenv("MAX_FILE_SIZE_BYTES", str(100 * 1024)))  # 100 KB
MAX_SKILLS_PER_REQUEST = int(os.getenv("MAX_SKILLS_PER_REQUEST", "8"))

# CORS – allow the Vite dev server and the production origin
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173"
).split(",")
CORS_ORIGINS = [origin.strip() for origin in CORS_ORIGINS if origin.strip()]

# File extensions that are worth inspecting for evidence
INSPECTABLE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".cs", ".sql",
    ".html", ".css", ".tf",
    ".yml", ".yaml",
}

# File and directory names to always skip
EXCLUDED_PATHS = {
    "node_modules", ".git", "dist", "build", "vendor",
    ".venv", "venv", "env", "__pycache__",
    "coverage", ".pytest_cache", ".mypy_cache",
}

# File names that must never be fetched (secrets / binaries)
SENSITIVE_FILENAMES = {
    ".env", ".env.local", ".env.production",
    "id_rsa", "id_ed25519", "id_ecdsa",
    "*.pem", "*.key", "*.p12", "*.pfx",
}

# User-Agent for GitHub API requests
USER_AGENT = "SkillProof/1.0 (graduate-skills-evidence-prototype)"

# README file names to inspect
README_NAMES = {"readme.md", "readme.txt", "readme.rst", "readme"}

# GitHub Actions workflow path prefix
WORKFLOW_PREFIX = ".github/workflows/"
