"""
Predefined skill catalogue.
This is the single source of truth for supported skills.
The frontend fetches this list from /api/skills; it does not maintain
its own copy.
"""

SKILLS = [
    # --- Programming languages ---
    {
        "id": "python",
        "name": "Python",
        "category": "Programming",
        "description": "Source files, imports, function/class definitions, recognised application patterns.",
    },
    {
        "id": "javascript",
        "name": "JavaScript",
        "category": "Programming",
        "description": "Source files, imports/exports, function declarations, recognised application code.",
    },
    {
        "id": "csharp",
        "name": "C#",
        "category": "Programming",
        "description": "Source files, namespace/class/method definitions, recognised .NET patterns.",
    },
    {
        "id": "sql",
        "name": "SQL",
        "category": "Programming",
        "description": "SQL files, query statements, table definitions, database queries in source files.",
    },
    # --- Backend development ---
    {
        "id": "rest_apis",
        "name": "REST APIs",
        "category": "Backend development",
        "description": "Route definitions, HTTP method handlers, controller endpoints, recognised framework patterns.",
    },
    {
        "id": "flask",
        "name": "Flask",
        "category": "Backend development",
        "description": "Flask imports, app creation, route decorators, application structure.",
    },
    {
        "id": "aspnet",
        "name": "ASP.NET Core",
        "category": "Backend development",
        "description": "Controller patterns, endpoint mappings, project files, recognised .NET web patterns.",
    },
    {
        "id": "database_integration",
        "name": "Database integration",
        "category": "Backend development",
        "description": "ORM usage, raw query execution, migration files, connection configuration patterns.",
    },
    # --- Frontend development ---
    {
        "id": "html",
        "name": "HTML",
        "category": "Frontend development",
        "description": "HTML files containing document structure, semantic elements, form elements.",
    },
    {
        "id": "css",
        "name": "CSS",
        "category": "Frontend development",
        "description": "CSS files with selectors and style declarations, or component style sections.",
    },
    {
        "id": "vuejs",
        "name": "Vue.js",
        "category": "Frontend development",
        "description": "Single-file components (.vue), Vue imports, component structure, Composition or Options API.",
    },
    # --- Cloud and DevOps ---
    {
        "id": "aws",
        "name": "AWS",
        "category": "Cloud and DevOps",
        "description": "Infrastructure config referencing AWS resources, SDK usage, deployment config, IaC with AWS providers.",
    },
    {
        "id": "docker",
        "name": "Docker",
        "category": "Cloud and DevOps",
        "description": "Dockerfile with meaningful instructions, Docker Compose service definitions.",
    },
    {
        "id": "terraform",
        "name": "Terraform",
        "category": "Cloud and DevOps",
        "description": ".tf files with resource, provider, or module blocks.",
    },
    {
        "id": "cicd",
        "name": "CI/CD",
        "category": "Cloud and DevOps",
        "description": "GitHub Actions workflow files, pipeline configuration with meaningful job/step definitions.",
    },
    # --- Testing and practices ---
    {
        "id": "automated_testing",
        "name": "Automated testing",
        "category": "Testing and development practices",
        "description": "Test files with test functions/cases, recognised test framework usage.",
    },
    {
        "id": "git",
        "name": "Git / GitHub",
        "category": "Testing and development practices",
        "description": "Repository structure, GitHub Actions workflows, recognised version-control artifacts.",
    },
]

# Quick lookup by id
SKILLS_BY_ID: dict = {s["id"]: s for s in SKILLS}
VALID_SKILL_IDS: set = set(SKILLS_BY_ID.keys())
