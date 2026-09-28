"""Exercise configuration precedence, isolated roots, and fail-closed modes."""

from pathlib import Path

import pytest

from app.core.errors import ConfigurationError
from app.core.settings import ProjectLocation, load_model_profile, load_settings


def test_load_settings_works_without_credentials(project_location: ProjectLocation) -> None:
    settings = load_settings(project_location)
    assert settings.model_mode == "fixture"
    assert settings.llm_api_key is None
    assert load_model_profile(project_location, settings).provider == "fixture"


def test_load_settings_accepts_entire_env_example(project_location: ProjectLocation) -> None:
    example = Path(__file__).resolve().parents[2] / ".env.example"
    (project_location.root / ".env").write_text(example.read_text())
    settings = load_settings(project_location)
    assert settings.external_sending_enabled is False
    assert settings.llm_api_key is None


def test_load_settings_process_overrides_dotenv_and_toml(
    project_location: ProjectLocation,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (project_location.config_dir / "default.toml").write_text('llm_model = "base"\n')
    (project_location.config_dir / "local.toml").write_text('llm_model = "local"\n')
    assert load_settings(project_location).llm_model == "local"
    (project_location.root / ".env").write_text("CASHFLOW_LLM_MODEL=dotenv\n")
    assert load_settings(project_location).llm_model == "dotenv"
    monkeypatch.setenv("CASHFLOW_LLM_MODEL", "process")
    assert load_settings(project_location).llm_model == "process"


def test_load_settings_does_not_read_parent_dotenv(project_location: ProjectLocation) -> None:
    (project_location.root.parent / ".env").write_text("CASHFLOW_LLM_API_KEY=parent-test-secret\n")
    assert load_settings(project_location).llm_api_key is None


@pytest.mark.parametrize(
    "entry",
    [
        "CASHFLOW_ENV=production",
        "CASHFLOW_MODEL_MODE=invalid",
        "CASHFLOW_EXTERNAL_SENDING_ENABLED=true",
        "CASHFLOW_MODEL_MODE=live",
    ],
)
def test_load_settings_rejects_unsupported_or_uncredentialed_modes(
    project_location: ProjectLocation,
    entry: str,
) -> None:
    (project_location.root / ".env").write_text(entry + "\n")
    with pytest.raises(ConfigurationError):
        load_settings(project_location)


def test_load_settings_keeps_blank_template_secrets_optional(
    project_location: ProjectLocation,
) -> None:
    (project_location.root / ".env").write_text(
        "CASHFLOW_LLM_API_KEY=\nCASHFLOW_LLM_MODEL=\nCASHFLOW_LLM_PROVIDER=\n"
    )
    assert load_settings(project_location).llm_api_key is None


def test_load_settings_masks_secret_representation(project_location: ProjectLocation) -> None:
    (project_location.root / ".env").write_text("CASHFLOW_LLM_API_KEY=sentinel-test-secret\n")
    settings = load_settings(project_location)
    assert "sentinel-test-secret" not in repr(settings)
    assert "sentinel-test-secret" not in settings.model_dump_json()


def test_load_settings_rejects_unknown_toml_fields(project_location: ProjectLocation) -> None:
    (project_location.config_dir / "local.toml").write_text('model_mod = "fixture"\n')
    with pytest.raises(ConfigurationError, match="unknown_setting"):
        load_settings(project_location)


def test_load_model_profile_applies_live_override(project_location: ProjectLocation) -> None:
    (project_location.root / ".env").write_text(
        "CASHFLOW_MODEL_MODE=live\nCASHFLOW_LLM_API_KEY=test-secret\nCASHFLOW_LLM_MODEL=chosen-model\n"
    )
    profile = load_model_profile(project_location, load_settings(project_location))
    assert profile.model_id == "chosen-model"
    assert profile.provider == "openai"


@pytest.mark.parametrize(
    "change", ["unknown_role", "unknown_provider", "zero_timeout", "live_fixture"]
)
def test_load_model_profile_rejects_invalid_catalog(
    project_location: ProjectLocation, change: str
) -> None:
    path = project_location.config_dir / "models.toml"
    content = path.read_text()
    replacements = {
        "unknown_role": ('connection = "connection"', 'connection = "missing"'),
        "unknown_provider": ('provider = "openai"', 'provider = "unknown"'),
        "zero_timeout": ("timeout_seconds = 20", "timeout_seconds = 0"),
        "live_fixture": ('connection = "connection"', 'connection = "fixture"'),
    }
    path.write_text(content.replace(*replacements[change]))
    (project_location.root / ".env").write_text(
        "CASHFLOW_MODEL_MODE=live\nCASHFLOW_LLM_API_KEY=test-secret\n"
    )
    with pytest.raises(ConfigurationError):
        load_model_profile(project_location, load_settings(project_location))


def test_load_settings_reports_missing_config_safely(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="invalid_configuration"):
        load_settings(ProjectLocation(root=tmp_path))


def test_model_selection_inherits_default_without_role_binding(
    project_location: ProjectLocation,
) -> None:
    path = project_location.config_dir / "models.toml"
    path.write_text(path.read_text().replace('[roles]\nconnection = "connection"', "[roles]"))
    settings = load_settings(project_location).model_copy(update={"model_mode": "live"})
    assert load_model_profile(project_location, settings).model_id == "gpt-5.4-mini-2026-03-17"


def test_model_selection_yaml_profile_then_model_then_environment(
    project_location: ProjectLocation,
) -> None:
    from app.llm.contracts import PromptReference
    from app.llm.prompts import load_prompt

    path = project_location.config_dir / "models.toml"
    path.write_text(
        path.read_text()
        + '\n[profiles.specialist]\nprovider="openai"\nmodel_id="gpt-5.5"\ntimeout_seconds=30\nmax_output_tokens=256\n'
    )
    settings = load_settings(project_location).model_copy(update={"model_mode": "live"})
    prompt = load_prompt(PromptReference(agent="connection", version=2))
    prompt = prompt.model_copy(
        update={"template": prompt.template.model_copy(update={"model_profile": "specialist"})}
    )
    profile = load_model_profile(project_location, settings, prompt)
    assert profile.model_id == "gpt-5.5"
    assert profile.timeout_seconds == 30
    prompt = prompt.model_copy(
        update={"template": prompt.template.model_copy(update={"model": "yaml-model"})}
    )
    assert load_model_profile(project_location, settings, prompt).model_id == "yaml-model"
    settings = settings.model_copy(update={"llm_model": "environment-model"})
    assert load_model_profile(project_location, settings, prompt).model_id == "environment-model"


def test_model_selection_yaml_does_not_enable_live_in_fixture_mode(
    project_location: ProjectLocation,
) -> None:
    from app.llm.contracts import PromptReference
    from app.llm.prompts import load_prompt

    prompt = load_prompt(PromptReference(agent="connection", version=2))
    prompt = prompt.model_copy(
        update={"template": prompt.template.model_copy(update={"model": "gpt-5.5"})}
    )
    profile = load_model_profile(project_location, load_settings(project_location), prompt)
    assert profile.provider == "fixture"
    assert profile.model_id == "connection-fixture-v1"


def test_load_settings_masks_anthropic_key(project_location: ProjectLocation) -> None:
    (project_location.root / ".env").write_text(
        "CASHFLOW_ANTHROPIC_API_KEY=sentinel-anthropic-secret\n"
    )
    settings = load_settings(project_location)
    assert settings.get_api_key("anthropic") is not None
    assert settings.get_api_key("openai") is None
    assert "sentinel-anthropic-secret" not in repr(settings)
    assert "sentinel-anthropic-secret" not in settings.model_dump_json()


def test_load_settings_accepts_live_mode_with_only_anthropic_key(
    project_location: ProjectLocation,
) -> None:
    (project_location.root / ".env").write_text(
        "CASHFLOW_MODEL_MODE=live\nCASHFLOW_ANTHROPIC_API_KEY=test-secret\n"
    )
    assert load_settings(project_location).model_mode == "live"


def test_explicit_vendor_uses_exact_catalog_profile(
    project_location: ProjectLocation, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CASHFLOW_LLM_MODEL", "environment-model")
    settings = load_settings(project_location).model_copy(update={"model_mode": "live"})
    profile = load_model_profile(project_location, settings, vendor="anthropic")
    assert profile.provider == "anthropic"
    assert profile.model_id == "claude-opus-5-5"


def test_environment_vendor_selects_profile_and_ignores_yaml_model(
    project_location: ProjectLocation, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.llm.contracts import PromptReference
    from app.llm.prompts import load_prompt

    monkeypatch.setenv("CASHFLOW_LLM_PROVIDER", "anthropic")
    settings = load_settings(project_location).model_copy(update={"model_mode": "live"})
    prompt = load_prompt(PromptReference(agent="connection", version=2))
    prompt = prompt.model_copy(
        update={"template": prompt.template.model_copy(update={"model": "gpt-5.5"})}
    )
    assert load_model_profile(project_location, settings, prompt).model_id == "claude-opus-5-5"
    settings = settings.model_copy(update={"llm_model": "claude-sonnet-5"})
    profile = load_model_profile(project_location, settings, prompt)
    assert (profile.provider, profile.model_id) == ("anthropic", "claude-sonnet-5")


@pytest.mark.parametrize(
    ("replacement", "reason"),
    [
        (('anthropic = "connection_anthropic"', ""), "unknown_vendor_profile"),
        (('anthropic = "connection_anthropic"', 'anthropic = "connection"'), "incompatible"),
        (('anthropic = "connection_anthropic"', 'anthropic = "absent"'), "unknown_model"),
    ],
)
def test_vendor_selection_rejects_invalid_vendor_profiles(
    project_location: ProjectLocation, replacement: tuple[str, str], reason: str
) -> None:
    path = project_location.config_dir / "models.toml"
    path.write_text(path.read_text().replace(*replacement))
    settings = load_settings(project_location).model_copy(update={"model_mode": "live"})
    with pytest.raises(ConfigurationError, match=reason):
        load_model_profile(project_location, settings, vendor="anthropic")


def test_model_selection_rejects_unknown_yaml_profile(project_location: ProjectLocation) -> None:
    from app.llm.contracts import PromptReference
    from app.llm.prompts import load_prompt

    prompt = load_prompt(PromptReference(agent="connection", version=2))
    prompt = prompt.model_copy(
        update={"template": prompt.template.model_copy(update={"model_profile": "absent"})}
    )
    with pytest.raises(ConfigurationError, match="unknown_model_profile"):
        load_model_profile(project_location, load_settings(project_location), prompt)
