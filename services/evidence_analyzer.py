"""
Rule-based evidence analyzer for SkillProof.

Design principles:
- Deterministic: same input → same output, every time.
- Conservative: prefer no finding over a false positive.
- Transparent: every finding cites a specific file and pattern.
- Honest: distinguishes source-code evidence from documentation mentions.
- Safe: never executes content; treats all file text as untrusted data.

Status values:
  evidence_found              – at least one meaningful artifact was identified.
  not_found_in_inspected_files – inspection completed; no relevant evidence found.
  needs_further_assessment    – weak or ambiguous evidence only.
  inspection_incomplete       – relevant files could not be inspected.
"""

import re
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Status constants ───────────────────────────────────────────────────────────

STATUS_FOUND = "evidence_found"
STATUS_NOT_FOUND = "not_found_in_inspected_files"
STATUS_NEEDS_ASSESSMENT = "needs_further_assessment"
STATUS_INCOMPLETE = "inspection_incomplete"

# ── Pattern helpers ────────────────────────────────────────────────────────────

def _has(content: str, pattern: str, flags: int = re.IGNORECASE | re.MULTILINE) -> bool:
    return bool(re.search(pattern, content, flags))


def _ext(path: str) -> str:
    return os.path.splitext(path.lower())[1]


def _filename(path: str) -> str:
    return os.path.basename(path).lower()


def _is_readme(path: str) -> bool:
    return _filename(path) in {"readme.md", "readme.txt", "readme.rst", "readme"}


def _is_test_file(path: str) -> bool:
    fn = _filename(path)
    return fn.startswith("test_") or fn.endswith("_test.py") or fn.endswith(".test.js") or \
           fn.endswith(".spec.js") or fn.endswith(".test.ts") or fn.endswith(".spec.ts") or \
           "test" in path.lower().split("/")


def _safe_excerpt(content: str, pattern: str, max_len: int = 120) -> Optional[str]:
    """Return a short excerpt around the first pattern match, or None."""
    try:
        m = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if not m:
            return None
        start = max(0, m.start() - 20)
        end = min(len(content), m.end() + 80)
        snippet = content[start:end].strip()
        snippet = re.sub(r'\s+', ' ', snippet)
        return snippet[:max_len]
    except Exception:
        return None

# ── Per-skill detection functions ──────────────────────────────────────────────

def _check_python(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) != ".py":
            continue
        if _is_readme(path):
            continue
        # Require actual code, not just a file
        has_import = _has(content, r'^\s*(import\s+\w+|from\s+\w+\s+import)', re.MULTILINE)
        has_def = _has(content, r'^\s*def\s+\w+\s*\(|^\s*class\s+\w+', re.MULTILINE)
        if has_import or has_def:
            evidence.append({
                "file_path": path,
                "file_url": url,
                "evidence_type": "source_code",
                "description": "Python source file containing imports and/or function/class definitions.",
                "limitations": "Code presence does not confirm authorship or independent proficiency.",
            })
    return _status(evidence), evidence, _python_next_step(evidence)


def _python_next_step(ev): return [
    "A practical Python task or code walkthrough can provide stronger evidence of independent ability."
] if ev else [
    "Check whether Python code exists in a different repository, or provide a code walkthrough."
]


def _check_javascript(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) not in {".js", ".jsx", ".mjs", ".cjs"}:
            continue
        if _is_readme(path):
            continue
        # Require genuine code indicators
        has_import = _has(content, r'(import\s+.+\s+from\s+[\'"]|require\s*\(|export\s+(default|const|function|class))')
        has_fn = _has(content, r'(function\s+\w+\s*\(|const\s+\w+\s*=\s*(async\s+)?\(|=>\s*\{)')
        if has_import or has_fn:
            evidence.append({
                "file_path": path,
                "file_url": url,
                "evidence_type": "source_code",
                "description": "JavaScript source file with imports/exports or function definitions.",
                "limitations": "Code presence does not confirm authorship or independent proficiency.",
            })
    return _status(evidence), evidence, []


def _check_csharp(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) != ".cs":
            continue
        has_ns = _has(content, r'\bnamespace\s+\w+')
        has_class = _has(content, r'\b(public|private|internal|protected)\s+(class|interface|struct)\s+\w+')
        if has_ns or has_class:
            evidence.append({
                "file_path": path,
                "file_url": url,
                "evidence_type": "source_code",
                "description": "C# source file with namespace/class/interface definitions.",
                "limitations": "Code presence does not confirm authorship or proficiency.",
            })
    return _status(evidence), evidence, []


def _check_sql(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    sql_patterns = r'\b(SELECT\s+.+\s+FROM|INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|CREATE\s+TABLE|ALTER\s+TABLE|DROP\s+TABLE)\b'
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        # .sql files OR SQL embedded in source code
        is_sql_file = _ext(path) == ".sql"
        if not is_sql_file and not _has(content, sql_patterns):
            continue
        if _is_readme(path):
            continue
        if _has(content, sql_patterns):
            description = (
                "SQL file containing query statements and/or table definitions."
                if is_sql_file else
                "SQL query statements found in source file."
            )
            evidence.append({
                "file_path": path,
                "file_url": url,
                "evidence_type": "source_code",
                "description": description,
                "limitations": "SQL patterns in code do not confirm advanced database design ability.",
            })
    return _status(evidence), evidence, []


def _check_rest_apis(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    patterns = [
        # Flask
        (r'@\w+\.route\s*\([\'"]\/[^\'"]*[\'"]', "Flask route decorator"),
        # Express
        (r'(app|router)\.(get|post|put|patch|delete)\s*\([\'"]', "Express route handler"),
        # ASP.NET Core
        (r'\[(HttpGet|HttpPost|HttpPut|HttpPatch|HttpDelete|Route)\]', "ASP.NET Core route attribute"),
        # FastAPI / similar
        (r'@app\.(get|post|put|patch|delete)\s*\([\'"]', "FastAPI/similar route decorator"),
        # Generic controller methods
        (r'\[ApiController\]', "ASP.NET ApiController attribute"),
    ]
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _is_readme(path):
            continue
        for pattern, label in patterns:
            if _has(content, pattern):
                evidence.append({
                    "file_path": path,
                    "file_url": url,
                    "evidence_type": "source_code",
                    "description": f"API route definition identified: {label}.",
                    "limitations": "A route definition indicates API implementation work but does not confirm production-quality design.",
                })
                break  # one evidence item per file
    return _status(evidence), evidence, []


def _check_flask(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) != ".py":
            continue
        if _is_readme(path):
            continue
        has_import = _has(content, r'from\s+flask\s+import|import\s+flask')
        has_app = _has(content, r'Flask\s*\(')
        has_route = _has(content, r'@\w+\.route\s*\(')
        if has_import and (has_app or has_route):
            evidence.append({
                "file_path": path,
                "file_url": url,
                "evidence_type": "source_code",
                "description": "Flask import and application/route usage found in Python source file.",
                "limitations": "Framework usage does not confirm mastery of all Flask features.",
            })
    return _status(evidence), evidence, []


def _check_aspnet(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) == ".csproj":
            if _has(content, r'Microsoft\.AspNetCore'):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "project_configuration",
                    "description": "ASP.NET Core project file detected.",
                    "limitations": "Project configuration confirms framework choice, not individual proficiency.",
                })
        elif _ext(path) == ".cs":
            has_controller = _has(content, r'\[ApiController\]|\[Controller\]')
            has_endpoints = _has(content, r'\[(HttpGet|HttpPost|HttpPut|HttpDelete|Route)\]')
            if has_controller or has_endpoints:
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": "ASP.NET Core controller/endpoint attributes found.",
                    "limitations": "Framework patterns in code do not confirm full proficiency.",
                })
    return _status(evidence), evidence, []


def _check_database_integration(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    patterns = [
        (r'(SqlConnection|MySqlConnection|NpgsqlConnection|psycopg2|pymysql)', "Database connection usage"),
        (r'(SQLAlchemy|from\s+sqlalchemy|db\.session|models\.Model)', "ORM usage (SQLAlchemy)"),
        (r'(Entity|DbContext|\.Include\(|\.Where\()', "Entity Framework patterns"),
        (r'(mongoose|sequelize|typeorm|prisma)', "ORM/ODM library usage"),
        (r'migrations/', "Database migration directory"),
    ]
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _is_readme(path):
            continue
        for pattern, label in patterns:
            if _has(content, pattern):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": f"Database integration pattern identified: {label}.",
                    "limitations": "Library usage does not confirm database design skill independently.",
                })
                break
    return _status(evidence), evidence, []


def _check_html(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) not in {".html", ".htm"}:
            # Also check .vue template sections
            if _ext(path) == ".vue" and _has(content, r'<template>[\s\S]+?</template>'):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": "HTML template section found in Vue single-file component.",
                    "limitations": "Template code does not confirm standalone HTML authoring ability.",
                })
            continue
        if _has(content, r'<(html|head|body|div|p|section|nav|form|input|button)\b'):
            evidence.append({
                "file_path": path, "file_url": url,
                "evidence_type": "source_code",
                "description": "HTML file with structural or semantic elements.",
                "limitations": "HTML file presence does not confirm advanced semantic markup ability.",
            })
    return _status(evidence), evidence, []


def _check_css(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        is_css = _ext(path) in {".css", ".scss", ".sass", ".less"}
        is_vue = _ext(path) == ".vue"
        if is_css:
            # CSS selectors + properties
            if _has(content, r'[\.\#\w]+\s*\{[^}]+\}'):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": "CSS file with selectors and style declarations.",
                    "limitations": "CSS presence does not confirm responsive design or advanced layout skill.",
                })
        elif is_vue:
            if _has(content, r'<style[\s\S]+?</style>'):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": "CSS style section found in Vue single-file component.",
                    "limitations": "Scoped component styles do not confirm standalone CSS authoring ability.",
                })
    return _status(evidence), evidence, []


def _check_vuejs(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) == ".vue":
            has_template = _has(content, r'<template>')
            has_script = _has(content, r'<script')
            if has_template or has_script:
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": "Vue single-file component with template and/or script section.",
                    "limitations": "SFC presence does not confirm advanced component design or state management.",
                })
        elif _ext(path) in {".js", ".mjs"}:
            if _has(content, r'(createApp|new Vue\s*\(|from\s+[\'"]vue[\'"])'):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": "Vue application setup found in JavaScript file.",
                    "limitations": "Setup code does not confirm component architecture or Vue ecosystem proficiency.",
                })
    return _status(evidence), evidence, []


def _check_aws(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    aws_patterns = [
        (r'provider\s*["\']aws["\']', "Terraform AWS provider"),
        (r'(aws_\w+|aws::\w+)', "AWS resource reference"),
        (r'(boto3|botocore|@aws-sdk)', "AWS SDK usage"),
        (r'(amazonaws\.com|arn:aws:)', "AWS resource identifier"),
        (r'(AWS::[\w:]+)', "CloudFormation AWS resource"),
        (r'(ECS|Lambda|S3Bucket|DynamoDB|RDS|EC2)\s*:', "CloudFormation/CDK resource type"),
    ]
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _is_readme(path):
            continue
        for pattern, label in aws_patterns:
            if _has(content, pattern):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "configuration",
                    "description": f"AWS reference identified: {label}.",
                    "limitations": "Infrastructure configuration does not confirm operational AWS experience.",
                })
                break
    return _status(evidence), evidence, []


def _check_docker(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        fn = _filename(path)
        if fn == "dockerfile":
            # Require at least a FROM instruction
            if _has(content, r'^FROM\s+\S+', re.MULTILINE):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "configuration",
                    "description": "Dockerfile with FROM instruction and container build steps.",
                    "limitations": "A Dockerfile does not confirm container orchestration or production deployment experience.",
                })
        elif fn in {"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"}:
            if _has(content, r'services\s*:', re.MULTILINE):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "configuration",
                    "description": "Docker Compose file with service definitions.",
                    "limitations": "Compose configuration does not confirm advanced container networking knowledge.",
                })
    return _status(evidence), evidence, []


def _check_terraform(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    tf_patterns = r'\b(resource\s*["\']|provider\s*["\']|module\s*["\']|variable\s*["\']|output\s*["\'])'
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if _ext(path) != ".tf":
            continue
        if _has(content, tf_patterns):
            evidence.append({
                "file_path": path, "file_url": url,
                "evidence_type": "configuration",
                "description": "Terraform configuration file with resource/provider/module blocks.",
                "limitations": "IaC files do not confirm cloud infrastructure administration experience.",
            })
    return _status(evidence), evidence, []


def _check_cicd(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        is_workflow = path.lower().startswith(".github/workflows/") and _ext(path) in {".yml", ".yaml"}
        if is_workflow:
            has_jobs = _has(content, r'^jobs\s*:', re.MULTILINE)
            has_steps = _has(content, r'^\s+steps\s*:', re.MULTILINE)
            if has_jobs or has_steps:
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "configuration",
                    "description": "GitHub Actions workflow file with job and step definitions.",
                    "limitations": "A workflow file does not confirm advanced pipeline design or DevOps experience.",
                })
        # Also detect other common CI config
        elif _filename(path) in {".travis.yml", "circle.yml", ".circleci/config.yml", "azure-pipelines.yml", "jenkinsfile"}:
            evidence.append({
                "file_path": path, "file_url": url,
                "evidence_type": "configuration",
                "description": f"CI/CD pipeline configuration file detected ({_filename(path)}).",
                "limitations": "Pipeline configuration does not confirm advanced DevOps practices.",
            })
    return _status(evidence), evidence, []


def _check_automated_testing(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    evidence = []
    test_patterns = [
        (r'^def\s+test_\w+\s*\(', "pytest-style test function"),
        (r'(unittest\.TestCase|self\.assert\w+\()', "unittest test case"),
        (r'(describe\s*\(|it\s*\(|test\s*\(|expect\s*\()', "JavaScript test (Jest/Mocha)"),
        (r'\[Fact\]|\[Theory\]|\[TestMethod\]', ".NET test attribute"),
        (r'(assert\s+\w|assertEqual|assertTrue|assertFalse)', "assertion in test"),
    ]
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if not _is_test_file(path) and "test" not in path.lower():
            continue
        for pattern, label in test_patterns:
            if _has(content, pattern, re.MULTILINE):
                evidence.append({
                    "file_path": path, "file_url": url,
                    "evidence_type": "source_code",
                    "description": f"Test code identified: {label}.",
                    "limitations": "Test presence does not confirm test coverage, quality, or TDD practice.",
                })
                break
    return _status(evidence), evidence, []


def _check_git(files: list[dict]) -> tuple[str, list[dict], list[str]]:
    """
    Git/GitHub evidence is contextual: the repository itself exists on GitHub.
    Check for GitHub Actions and meaningful workflow configuration as stronger evidence.
    Repository hosting alone is weak evidence of advanced Git proficiency.
    """
    evidence = []
    for f in files:
        path, content, url = f["path"], f["content"], f["github_url"]
        if path.lower().startswith(".github/workflows/"):
            evidence.append({
                "file_path": path, "file_url": url,
                "evidence_type": "configuration",
                "description": "GitHub Actions workflow used — indicates familiarity with GitHub-based automation.",
                "limitations": "Using GitHub Actions does not confirm advanced Git branching, merging, or conflict resolution skills.",
            })
    if not evidence:
        # Weak evidence: the repo exists
        return STATUS_NEEDS_ASSESSMENT, [], [
            "The repository is hosted on GitHub, which shows basic familiarity with version control hosting. "
            "A practical Git task, commit history review, or branching demonstration can provide stronger evidence."
        ]
    return _status(evidence), evidence, []


# ── Status calculator ──────────────────────────────────────────────────────────

def _status(evidence: list) -> str:
    if evidence:
        return STATUS_FOUND
    return STATUS_NOT_FOUND


# ── Dispatch table ─────────────────────────────────────────────────────────────

_SKILL_CHECKS = {
    "python": _check_python,
    "javascript": _check_javascript,
    "csharp": _check_csharp,
    "sql": _check_sql,
    "rest_apis": _check_rest_apis,
    "flask": _check_flask,
    "aspnet": _check_aspnet,
    "database_integration": _check_database_integration,
    "html": _check_html,
    "css": _check_css,
    "vuejs": _check_vuejs,
    "aws": _check_aws,
    "docker": _check_docker,
    "terraform": _check_terraform,
    "cicd": _check_cicd,
    "automated_testing": _check_automated_testing,
    "git": _check_git,
}

# ── Public entry point ─────────────────────────────────────────────────────────

def analyze(
    repository_meta: dict,
    inspected_files: list[dict],
    inspection_meta: dict,
    selected_skill_ids: list[str],
) -> dict:
    """
    Run the evidence analyzer over inspected files for the selected skills.

    Returns the complete analysis report structure.
    """
    from core.skills_catalogue import SKILLS_BY_ID

    skills_results = []
    skills_with_evidence = 0

    for skill_id in selected_skill_ids:
        skill_def = SKILLS_BY_ID.get(skill_id, {})
        check_fn = _SKILL_CHECKS.get(skill_id)

        if check_fn is None:
            # Skill in catalogue but not yet implemented
            status = STATUS_INCOMPLETE
            evidence = []
            next_steps = ["This skill has not yet been implemented in the analyzer."]
        elif not inspected_files and inspection_meta.get("files_inspected", 0) == 0:
            # The inspection itself failed — don't report this as a negative finding
            status = STATUS_INCOMPLETE
            evidence = []
            next_steps = ["The repository could not be inspected. Check the URL and try again."]
        else:
            status, evidence, next_steps = check_fn(inspected_files)
            inspection_was_limited = (
                inspection_meta.get("files_skipped", 0) > 0
                or inspection_meta.get("limited_by_file_budget", False)
                or inspection_meta.get("limited_by_time_budget", False)
            )
            if status != STATUS_FOUND and inspection_was_limited:
                status = STATUS_INCOMPLETE
                next_steps = [
                    "Repeat the inspection or review the repository manually; some files were not assessed."
                ]

        if status == STATUS_FOUND:
            skills_with_evidence += 1

        explanation = _build_explanation(skill_id, status, evidence, inspection_meta)

        skills_results.append({
            "id": skill_id,
            "name": skill_def.get("name", skill_id),
            "category": skill_def.get("category", ""),
            "status": status,
            "explanation": explanation,
            "evidence": evidence,
            "recommended_next_steps": next_steps or _default_next_steps(status),
            "limitations": _skill_limitations(status),
        })

    total_skills = len(selected_skill_ids)
    skills_needing_assessment = total_skills - skills_with_evidence

    return {
        "repository": {
            "name": repository_meta.get("name", ""),
            "owner": repository_meta.get("owner", ""),
            "full_name": repository_meta.get("full_name", ""),
            "url": repository_meta.get("html_url", ""),
            "description": repository_meta.get("description", ""),
            "primary_language": repository_meta.get("primary_language"),
            "default_branch": repository_meta.get("default_branch", "main"),
        },
        "inspection": inspection_meta,
        "summary": {
            "selected_skills": total_skills,
            "skills_with_evidence": skills_with_evidence,
            "skills_needing_further_assessment": skills_needing_assessment,
        },
        "skills": skills_results,
        "limitations": [
            "Only a bounded selection of accessible repository files was inspected.",
            "Evidence patterns are predefined rules — valid implementations may not be recognised.",
            "Code presence does not confirm authorship, code quality, or independent proficiency.",
            "Missing evidence does not mean the graduate lacks the skill.",
            "This report does not constitute a formal skills certification.",
            "A structured assessment or project walkthrough can provide additional evidence.",
        ],
    }


# ── Explanation builders ───────────────────────────────────────────────────────

def _build_explanation(skill_id: str, status: str, evidence: list, meta: dict) -> str:
    if status == STATUS_FOUND:
        count = len(evidence)
        plural = "files" if count > 1 else "file"
        return (
            f"Relevant evidence was identified in {count} inspected {plural}. "
            "Source links are provided for direct inspection."
        )
    if status == STATUS_NOT_FOUND:
        inspected = meta.get("files_inspected", 0)
        return (
            f"No recognised evidence was found across {inspected} inspected file(s). "
            "The skill may exist in files not inspected, in a different repository, "
            "or may require a practical demonstration to assess."
        )
    if status == STATUS_NEEDS_ASSESSMENT:
        return (
            "The available evidence is insufficient to make a finding. "
            "A practical task, project walkthrough, or structured interview can provide clearer evidence."
        )
    if status == STATUS_INCOMPLETE:
        return (
            "This skill could not be assessed because the repository could not be fully inspected. "
            "Check the repository URL and GitHub availability."
        )
    return "Status unknown."


def _default_next_steps(status: str) -> list[str]:
    if status == STATUS_NOT_FOUND:
        return ["Provide an alternative repository or complete a practical task to demonstrate this skill."]
    if status == STATUS_NEEDS_ASSESSMENT:
        return ["A structured practical task or project walkthrough is recommended."]
    return []


def _skill_limitations(status: str) -> list[str]:
    base = [
        "Detected patterns indicate relevant artifacts but do not prove authorship.",
        "Static code inspection cannot assess code quality, design decisions, or problem-solving approach.",
    ]
    if status == STATUS_FOUND:
        return base
    if status == STATUS_NOT_FOUND:
        return ["Absence of evidence in inspected files is not evidence of absence of the skill."]
    return []
