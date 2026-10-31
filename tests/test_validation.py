"""
Tests for URL and skill validation.
"""
import pytest
from core.validation import validate_repository_url, validate_skills, ValidationError


# ── URL validation ─────────────────────────────────────────────────────────────

class TestRepositoryUrl:
    def test_valid_url(self):
        owner, repo = validate_repository_url("https://github.com/octocat/Hello-World")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_valid_url_with_git_suffix(self):
        owner, repo = validate_repository_url("https://github.com/octocat/Hello-World.git")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_valid_url_trailing_slash(self):
        owner, repo = validate_repository_url("https://github.com/octocat/Hello-World/")
        assert owner == "octocat"
        assert repo == "Hello-World"

    def test_empty_url(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("")
        assert exc.value.code == "EMPTY_URL"

    def test_none_url(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url(None)
        assert exc.value.code == "EMPTY_URL"

    def test_http_not_https(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("http://github.com/octocat/Hello-World")
        assert exc.value.code == "INVALID_SCHEME"

    def test_wrong_hostname(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://gitlab.com/octocat/Hello-World")
        assert exc.value.code == "INVALID_HOST"

    def test_lookalike_hostname(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://github.com.evil.com/octocat/Hello-World")
        assert exc.value.code == "INVALID_HOST"

    def test_github_profile_url(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://github.com/octocat")
        assert exc.value.code == "MISSING_REPOSITORY"

    def test_url_with_credentials(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://user:pass@github.com/octocat/Hello-World")
        assert exc.value.code == "URL_CREDENTIALS"

    def test_unexpected_port(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://github.com:8080/octocat/Hello-World")
        assert exc.value.code == "UNEXPECTED_PORT"

    def test_malformed_port(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://github.com:invalid/octocat/Hello-World")
        assert exc.value.code == "UNEXPECTED_PORT"

    def test_empty_user_info_rejected(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://@github.com/octocat/Hello-World")
        assert exc.value.code == "URL_CREDENTIALS"

    def test_arbitrary_url(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://example.com/some/path")
        assert exc.value.code == "INVALID_HOST"

    def test_deep_path_rejected(self):
        with pytest.raises(ValidationError) as exc:
            validate_repository_url("https://github.com/octocat/Hello-World/tree/main/src")
        assert exc.value.code == "INVALID_REPOSITORY_PATH"


# ── Skill validation ───────────────────────────────────────────────────────────

class TestSkillValidation:
    def test_valid_single_skill(self):
        result = validate_skills(["python"])
        assert result == ["python"]

    def test_valid_multiple_skills(self):
        result = validate_skills(["python", "docker", "flask"])
        assert set(result) == {"python", "docker", "flask"}

    def test_max_8_skills(self):
        skills = ["python", "javascript", "sql", "docker", "flask", "html", "css", "vuejs"]
        result = validate_skills(skills)
        assert len(result) == 8

    def test_too_many_skills(self):
        skills = ["python", "javascript", "sql", "docker", "flask", "html", "css", "vuejs", "aws"]
        with pytest.raises(ValidationError) as exc:
            validate_skills(skills)
        assert exc.value.code == "TOO_MANY_SKILLS"

    def test_empty_list(self):
        with pytest.raises(ValidationError) as exc:
            validate_skills([])
        assert exc.value.code == "NO_SKILLS"

    def test_unsupported_skill(self):
        with pytest.raises(ValidationError) as exc:
            validate_skills(["python", "blockchain_nfts"])
        assert exc.value.code == "UNSUPPORTED_SKILL"

    def test_not_a_list(self):
        with pytest.raises(ValidationError) as exc:
            validate_skills("python")
        assert exc.value.code == "INVALID_SKILLS_TYPE"

    def test_non_string_skill(self):
        with pytest.raises(ValidationError) as exc:
            validate_skills([123])
        assert exc.value.code == "INVALID_SKILL_ID"

    def test_deduplication(self):
        result = validate_skills(["python", "python", "docker"])
        assert result.count("python") == 1
        assert "docker" in result
