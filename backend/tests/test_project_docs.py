import re

from app.config.settings import PROJECT_ROOT, Settings

ENV_EXAMPLE_PATH = PROJECT_ROOT / ".env.example"
ENV_EXAMPLE_LINE_PATTERN = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)=", re.MULTILINE)
LOCAL_DEVELOPMENT_SECTION_MARKER = "# Local development only"
LOCAL_DEVELOPMENT_VARIABLES = {
    "POSTGRES_PORT",
    "MAILPIT_SMTP_PORT",
    "MAILPIT_UI_PORT",
    "MINIO_API_PORT",
    "MINIO_CONSOLE_PORT",
    "BACKEND_PORT",
    "VITE_API_PROXY_TARGET",
    "TEST_DATABASE_URL",
}
BILLING_NOTES = (
    "/api/webhooks/billing/",
    "trial_period_days",
    "Stripe webhook events:",
    "Lemon Squeezy webhook events:",
    "Creem webhook events:",
    "https://test-api.creem.io",
)


def settings_field_names() -> set[str]:
    return set(Settings.model_fields)


def env_example_sections() -> tuple[str, str]:
    """Split .env.example into the app settings part and the local-development part (phase 01 layout)."""
    env_example = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    assert LOCAL_DEVELOPMENT_SECTION_MARKER in env_example
    app_section, local_development_section = env_example.split(LOCAL_DEVELOPMENT_SECTION_MARKER, 1)
    return app_section, local_development_section


def variable_names(section: str) -> set[str]:
    return set(ENV_EXAMPLE_LINE_PATTERN.findall(section))


def test_env_example_lists_every_setting() -> None:
    app_section, _ = env_example_sections()
    missing_variables = settings_field_names() - variable_names(app_section)
    assert missing_variables == set()


def test_env_example_has_no_unknown_variables() -> None:
    app_section, local_development_section = env_example_sections()
    assert variable_names(app_section) - settings_field_names() == set()
    assert variable_names(local_development_section) == LOCAL_DEVELOPMENT_VARIABLES


def test_env_example_sets_required_variables_uncommented() -> None:
    app_section, _ = env_example_sections()
    for required_name in ("DATABASE_URL", "JWT_SECRET", "APP_URL"):
        assert re.search(rf"^{required_name}=\S+", app_section, re.MULTILINE), required_name


def test_env_example_keeps_billing_notes() -> None:
    app_section, _ = env_example_sections()
    missing_notes = [note for note in BILLING_NOTES if note not in app_section]
    assert missing_notes == []


README_PATH = PROJECT_ROOT / "README.md"
MAKEFILE_PATH = PROJECT_ROOT / "Makefile"
BILLING_PROVIDERS = ("stripe", "lemonsqueezy", "creem")


def readme_text() -> str:
    return README_PATH.read_text(encoding="utf-8")


def test_readme_documents_every_setting() -> None:
    readme = readme_text()
    undocumented = {name for name in settings_field_names() if f"`{name}`" not in readme}
    assert undocumented == set()


def test_readme_make_targets_exist() -> None:
    readme = readme_text()
    used_targets = set(re.findall(r"^make ([a-z][a-z0-9-]*)", readme, re.MULTILINE))
    used_targets |= set(re.findall(r"`make ([a-z][a-z0-9-]*)[` ]", readme))
    defined_targets = set(re.findall(r"^([a-z][a-z0-9-]*):", MAKEFILE_PATH.read_text(encoding="utf-8"), re.MULTILINE))
    assert used_targets, "README should show make targets"
    assert used_targets - defined_targets == set()


def test_readme_paths_exist() -> None:
    referenced_paths = set(re.findall(r"`((?:backend|frontend)/[A-Za-z0-9_./-]+)`", readme_text()))
    missing_paths = {path for path in referenced_paths if not (PROJECT_ROOT / path).exists()}
    assert missing_paths == set()


def test_readme_lists_billing_webhook_urls() -> None:
    readme = readme_text()
    for provider in BILLING_PROVIDERS:
        assert f"/api/webhooks/billing/{provider}" in readme


def test_readme_links_runsite() -> None:
    readme = readme_text()
    for url in ("https://runsite.app", "https://docs.runsite.app", "https://dashboard.runsite.app/templates/"):
        assert url in readme
    assert "Deploy on Runsite" in readme
