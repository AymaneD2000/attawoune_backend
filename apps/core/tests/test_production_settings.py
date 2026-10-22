"""Exercise environment profiles in fresh processes, independent of local .env files."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


BACKEND_ROOT = Path(__file__).resolve().parents[3]
PROFILE_VARIABLES = {
    "DJANGO_ENV", "SECRET_KEY", "DEBUG", "ALLOWED_HOSTS", "CORS_ALLOWED_ORIGINS",
    "CSRF_TRUSTED_ORIGINS", "CORS_ALLOW_ALL_ORIGINS", "SECURE_SSL_REDIRECT",
    "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE", "SECURE_HSTS_SECONDS",
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", "SECURE_HSTS_PRELOAD", "DATABASE_URL",
}
PRODUCTION_ENV = {
    "DJANGO_ENV": "production",
    "SECRET_KEY": "test-only-secret-for-settings-validation-at-least-fifty-characters-12345",
    "ALLOWED_HOSTS": "example.edu",
    "CORS_ALLOWED_ORIGINS": "https://app.example.edu",
}


def run_settings(env: dict[str, str], *, inspect: bool = False) -> subprocess.CompletedProcess[str]:
    merged = {key: value for key, value in os.environ.items() if key not in PROFILE_VARIABLES}
    merged.update(env)
    # Use decouple's real environment reader without loading a developer's .env.
    script = (
        "import decouple; "
        "decouple.config = decouple.Config(decouple.RepositoryEmpty()); "
        "import core.settings as settings; "
    )
    if inspect:
        names = sorted(PROFILE_VARIABLES - {"SECRET_KEY", "DATABASE_URL"})
        script += (
            "import json; print(json.dumps({name: getattr(settings, name) "
            f"for name in {names!r}" + "}))"
        )
    return subprocess.run(
        [sys.executable, "-c", script], cwd=BACKEND_ROOT, env=merged,
        text=True, capture_output=True, check=False, timeout=10,
    )


@pytest.mark.parametrize("name", ["SECRET_KEY", "ALLOWED_HOSTS", "CORS_ALLOWED_ORIGINS"])
@pytest.mark.parametrize("value", [None, "", "   "])
def test_production_rejects_missing_required_settings(name, value):
    env = dict(PRODUCTION_ENV)
    if value is None:
        env.pop(name)
    else:
        env[name] = value
    result = run_settings(env)
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert name in result.stderr


@pytest.mark.parametrize("secret", ["short-secret", "django-insecure-" + "x" * 60])
def test_production_rejects_unsafe_secret_keys(secret):
    result = run_settings({**PRODUCTION_ENV, "SECRET_KEY": secret})
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr


@pytest.mark.parametrize("length", [49, 50])
def test_production_secret_length_boundary(length):
    result = run_settings({**PRODUCTION_ENV, "SECRET_KEY": ("abcdefghij" * 5)[:length]})
    if length < 50:
        assert result.returncode != 0
        assert "SECRET_KEY" in result.stderr
    else:
        assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name,value", [
    ("DEBUG", "true"),
    ("SECURE_SSL_REDIRECT", "false"),
    ("SESSION_COOKIE_SECURE", "false"),
    ("CSRF_COOKIE_SECURE", "false"),
    ("CORS_ALLOW_ALL_ORIGINS", "true"),
    ("SECURE_HSTS_SECONDS", "0"),
    ("SECURE_HSTS_SECONDS", "-1"),
])
def test_production_rejects_disabled_security(name, value):
    result = run_settings({**PRODUCTION_ENV, name: value})
    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert name in result.stderr


@pytest.mark.parametrize("name", ["ALLOWED_HOSTS", "CORS_ALLOWED_ORIGINS"])
def test_production_rejects_empty_comma_separated_lists(name):
    result = run_settings({**PRODUCTION_ENV, name: " , , "})
    assert result.returncode != 0
    assert name in result.stderr


def test_production_defaults_are_secure():
    result = run_settings(PRODUCTION_ENV, inspect=True)
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["DJANGO_ENV"] == "production"
    assert settings["DEBUG"] is False
    assert settings["SECURE_SSL_REDIRECT"] is True
    assert settings["SESSION_COOKIE_SECURE"] is True
    assert settings["CSRF_COOKIE_SECURE"] is True
    assert settings["SECURE_HSTS_SECONDS"] == 31536000
    assert settings["CORS_ALLOW_ALL_ORIGINS"] is False
    assert settings["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is False
    assert settings["SECURE_HSTS_PRELOAD"] is False
    assert settings["CSRF_TRUSTED_ORIGINS"] == []


@pytest.mark.parametrize("profile", [None, "development", "test"])
def test_local_profiles_keep_local_defaults(profile):
    result = run_settings({"DJANGO_ENV": profile} if profile else {}, inspect=True)
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["DJANGO_ENV"] == (profile or "development")
    assert settings["ALLOWED_HOSTS"] == ["localhost", "127.0.0.1"]
    assert settings["CORS_ALLOWED_ORIGINS"] == ["http://localhost:5173", "http://127.0.0.1:5173"]
    for name in ["SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"]:
        assert settings[name] is False
    assert settings["SECURE_HSTS_SECONDS"] == 0
    assert settings["CORS_ALLOW_ALL_ORIGINS"] is True


@pytest.mark.parametrize("profile", ["development", "test"])
def test_local_profiles_allow_explicit_configuration(profile):
    result = run_settings({
        "DJANGO_ENV": profile,
        "DEBUG": "true",
        "ALLOWED_HOSTS": "local.example.edu",
        "CORS_ALLOWED_ORIGINS": "https://local.example.edu",
        "CORS_ALLOW_ALL_ORIGINS": "false",
        "SECURE_SSL_REDIRECT": "true",
        "SESSION_COOKIE_SECURE": "true",
        "CSRF_COOKIE_SECURE": "true",
        "SECURE_HSTS_SECONDS": "60",
    }, inspect=True)
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["DEBUG"] is True
    assert settings["ALLOWED_HOSTS"] == ["local.example.edu"]
    assert settings["CORS_ALLOWED_ORIGINS"] == ["https://local.example.edu"]
    assert settings["CORS_ALLOW_ALL_ORIGINS"] is False
    for name in ["SECURE_SSL_REDIRECT", "SESSION_COOKIE_SECURE", "CSRF_COOKIE_SECURE"]:
        assert settings[name] is True
    assert settings["SECURE_HSTS_SECONDS"] == 60


@pytest.mark.parametrize("profile", ["staging", "", "prod"])
def test_unknown_profile_is_rejected(profile):
    result = run_settings({"DJANGO_ENV": profile})
    assert result.returncode != 0
    assert "DJANGO_ENV" in result.stderr
    assert "development, test, production" in result.stderr


def test_profile_and_origin_lists_are_normalized():
    result = run_settings({
        **PRODUCTION_ENV,
        "DJANGO_ENV": " Production ",
        "ALLOWED_HOSTS": " example.edu, api.example.edu , ",
        "CORS_ALLOWED_ORIGINS": " https://app.example.edu/ , ",
        "CSRF_TRUSTED_ORIGINS": " https://app.example.edu/ , ",
        "SECURE_HSTS_INCLUDE_SUBDOMAINS": "true",
        "SECURE_HSTS_PRELOAD": "true",
    }, inspect=True)
    assert result.returncode == 0, result.stderr
    settings = json.loads(result.stdout)
    assert settings["ALLOWED_HOSTS"] == ["example.edu", "api.example.edu"]
    assert settings["CORS_ALLOWED_ORIGINS"] == ["https://app.example.edu"]
    assert settings["CSRF_TRUSTED_ORIGINS"] == ["https://app.example.edu"]
    assert settings["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is True
    assert settings["SECURE_HSTS_PRELOAD"] is True
