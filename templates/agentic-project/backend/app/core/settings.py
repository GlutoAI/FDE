"""Load explicit project configuration without discovering parent .env files.

Precedence, lowest to highest: ``config/default.toml``, ``config/<env>.toml``, the project's
``.env``, then the process environment. Model selection lives in ``config/models.toml`` and is
resolved separately by ``load_model_profile`` and ``load_embedding_profile``.
"""

import os
import tomllib
from pathlib import Path
from typing import Any, Literal, override

from dotenv import dotenv_values
from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.core.errors import ConfigurationError
from app.llm.contracts import (
    Contract,
    EmbeddingProfile,
    LiveProviderName,
    LoadedPrompt,
    ModelProfile,
    PromptReference,
)
from app.llm.prompts import load_prompt

# Variable names only, for messages and config-check; values are read by Settings.
API_KEY_VARIABLES: dict[LiveProviderName, str] = {
    "openai": "TEMPLATE_OPENAI_API_KEY",
    "anthropic": "TEMPLATE_ANTHROPIC_API_KEY",
}

# settings.py -> core -> app -> backend -> project root. Docker keeps this layout for the same
# reason (see docker/Dockerfile.api).
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]


class ProjectLocation(Contract):
    """Explicit project root supplied by the caller, and the fixed layout beneath it.

    The project root holds ``.env`` and ``data/``; ``backend/`` holds ``config/`` and the
    ignored runtime state in ``backend/data/``.
    """

    root: Path = Field(description="Project root containing backend/, data/, and optional .env")

    @property
    def backend_root(self) -> Path:
        """Return the backend directory, the working directory for launched MCP servers."""
        return self.root / "backend"

    @property
    def config_dir(self) -> Path:
        """Return the directory of versioned TOML configuration."""
        return self.backend_root / "config"

    @property
    def env_file(self) -> Path:
        """Return the project's only dotenv file."""
        return self.root / ".env"

    @property
    def data_root(self) -> Path:
        """Return the project's input data directory."""
        return self.root / "data"

    @property
    def state_dir(self) -> Path:
        """Return the ignored directory for the local database and server logs."""
        return self.backend_root / "data"


class Settings(BaseSettings):
    """Validated runtime settings for one project; infrastructure keys come in later phases.

    Every field maps to a ``TEMPLATE_<FIELD>`` variable. Secrets are ``SecretStr`` with
    ``repr=False``, so they never appear in logs, errors, or ``repr``.
    """

    model_config = SettingsConfigDict(
        env_prefix="TEMPLATE_",
        # Blank lines in .env (``KEY=``) mean "unset", not an empty key.
        env_ignore_empty=True,
        # The project .env may hold variables for other tools.
        extra="ignore",
        # Validation errors would otherwise echo the rejected value, which may be a key.
        hide_input_in_errors=True,
    )
    env: Literal["local", "test"] = Field(default="local", description="Implemented environment")
    model_mode: Literal["fixture", "live"] = Field(default="fixture", description="Inference mode")
    external_actions_enabled: Literal[False] = Field(default=False, description="Always disabled")
    openai_api_key: SecretStr | None = Field(
        default=None, repr=False, description="Local OpenAI key"
    )
    anthropic_api_key: SecretStr | None = Field(
        default=None, repr=False, description="Local Anthropic key"
    )
    llm_provider: LiveProviderName | None = Field(
        default=None, description="Optional vendor override; selects that vendor's profile"
    )
    llm_model: str | None = Field(
        default=None, min_length=1, description="Optional model ID override"
    )
    database_url: SecretStr | None = Field(
        default=None,
        repr=False,
        description="Async SQLAlchemy URL; may embed a password. Default: backend/data/app.db",
    )

    @field_validator("external_actions_enabled", mode="before")
    @classmethod
    def parse_disabled_flag(cls, value: object) -> object:
        """Accept the dotenv false literal while rejecting any enabled external-action mode.

        Args:
            value: Raw value from TOML, dotenv, or the environment.

        Returns:
            False for the string ``false`` in any case; any other value unchanged, so the
            ``Literal[False]`` type then rejects ``true``.
        """
        return False if isinstance(value, str) and value.lower() == "false" else value

    @classmethod
    @override
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Give process environment and project dotenv precedence over merged TOML defaults.

        ``load_settings`` passes the merged TOML as init arguments, which pydantic-settings
        would otherwise rank highest. File secrets are not a source.

        Args:
            settings_cls: The settings class being built.
            init_settings: Merged TOML values passed to the constructor.
            env_settings: Process environment variables.
            dotenv_settings: The project's ``.env`` file.
            file_secret_settings: Secrets directory source; deliberately unused.

        Returns:
            Sources in priority order, highest first.
        """
        return env_settings, dotenv_settings, init_settings

    def get_api_key(self, provider: LiveProviderName) -> SecretStr | None:
        """Return the configured key for one vendor.

        Args:
            provider: Vendor whose key is needed.

        Returns:
            The secret-wrapped key, or None when that vendor's key is absent.
        """
        return self.openai_api_key if provider == "openai" else self.anthropic_api_key


class ModelCatalog(Contract):
    """Named profiles and role bindings, validated before provider construction."""

    profiles: dict[str, ModelProfile] = Field(min_length=1, description="Approved model profiles")
    default_profile: str = Field(
        min_length=1, description="Profile inherited by agents without a selection"
    )
    roles: dict[str, str] = Field(
        default_factory=dict, description="Optional agent role to profile mapping"
    )
    vendor_profiles: dict[LiveProviderName, str] = Field(
        default_factory=dict, description="Profile used when a vendor is selected explicitly"
    )
    embedding_profiles: dict[str, EmbeddingProfile] = Field(
        default_factory=dict, description="Approved embedding profiles; 'fixture' is required"
    )
    default_embedding_profile: str | None = Field(
        default=None, min_length=1, description="Embedding profile used in live mode"
    )


def load_settings(
    location: ProjectLocation, *, execution_mode: Literal["fixture", "live"] | None = None
) -> Settings:
    """Read defaults, environment TOML, and explicit dotenv, then apply process overrides.

    Args:
        location: Root of this project's configuration, never inferred from parent directories.
        execution_mode: Explicit smoke command mode; takes precedence for this invocation only.

    Returns:
        Validated settings with secret-aware fields.

    Raises:
        ConfigurationError: Files or settings are invalid, or enabled live mode has no key.
    """
    try:
        defaults = _load_toml(location.config_dir / "default.toml")
        dotenv = dotenv_values(location.env_file, interpolate=False)
        environment = (
            os.environ.get("TEMPLATE_ENV")
            or dotenv.get("TEMPLATE_ENV")
            or defaults.get("env", "local")
        )
        if environment not in ("local", "test"):
            raise ConfigurationError("unsupported_environment: only local/test are implemented")
        merged = defaults | _load_toml(location.config_dir / f"{environment}.toml")
        if set(merged) - Settings.model_fields.keys():
            raise ConfigurationError("unknown_setting: check TOML field names")
        settings = Settings(_env_file=location.env_file, **merged)
        if execution_mode is not None:
            settings = settings.model_copy(update={"model_mode": execution_mode})
        if settings.model_mode == "live" and not (
            settings.openai_api_key or settings.anthropic_api_key
        ):
            raise ConfigurationError(
                "missing_credentials: set TEMPLATE_OPENAI_API_KEY or TEMPLATE_ANTHROPIC_API_KEY"
            )
        return settings
    except (OSError, ValueError, TypeError) as error:
        raise ConfigurationError("invalid_configuration: check project config files") from error


def load_model_profile(
    location: ProjectLocation,
    settings: Settings,
    prompt: LoadedPrompt | None = None,
    *,
    vendor: LiveProviderName | None = None,
) -> ModelProfile:
    """Resolve the connection role, keeping fixture mode independent of live overrides.

    Live selection, lowest to highest priority: default_profile, roles, YAML model_profile,
    YAML model, then TEMPLATE_LLM_MODEL. A vendor (TEMPLATE_LLM_PROVIDER or ``vendor``)
    replaces the role selection with ``vendor_profiles[vendor]`` and drops the YAML model,
    which belongs to the default vendor. An explicit ``vendor`` also ignores
    TEMPLATE_LLM_MODEL, so the probe uses exactly that vendor's catalog profile.

    Args:
        location: Project containing config/models.toml.
        settings: Selected execution mode and optional provider/model overrides.
        prompt: Agent YAML selection; defaults to the current connection prompt.
        vendor: Vendor chosen by an explicit command option; live mode only.

    Returns:
        A validated profile; no client or network activity is created here.

    Raises:
        ConfigurationError: A role/profile is missing, unknown, or incompatible.
    """
    try:
        catalog = ModelCatalog.model_validate(_load_toml(location.config_dir / "models.toml"))
        prompt = prompt or load_prompt(PromptReference(agent="connection", version=1))
        _validate_profile_references(catalog, prompt)
        if settings.model_mode == "fixture":
            return _require_mode_compatible(catalog.profiles["fixture"], is_live=False)
        selected_vendor = vendor or settings.llm_provider
        profile = catalog.profiles[_select_profile_name(catalog, prompt, selected_vendor)]
        if selected_vendor is not None and profile.provider != selected_vendor:
            raise ConfigurationError("incompatible_profile: vendor profile uses another provider")
        model_id = profile.model_id
        if vendor is None:
            yaml_model = None if selected_vendor else prompt.template.model
            model_id = settings.llm_model or yaml_model or model_id
        profile = ModelProfile.model_validate(profile.model_dump() | {"model_id": model_id})
        return _require_mode_compatible(profile, is_live=True)
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise ConfigurationError("invalid_model_catalog: check models.toml") from error


def load_embedding_profile(location: ProjectLocation, settings: Settings) -> EmbeddingProfile:
    """Resolve the embedding profile: the fixture offline, the configured default live.

    Args:
        location: Project containing config/models.toml.
        settings: Selected execution mode.

    Returns:
        A validated profile; no client or network activity is created here.

    Raises:
        ConfigurationError: The catalog lacks the required profile, or its provider does not
            match the execution mode.
    """
    try:
        catalog = ModelCatalog.model_validate(_load_toml(location.config_dir / "models.toml"))
    except (OSError, ValueError, TypeError) as error:
        raise ConfigurationError("invalid_model_catalog: check models.toml") from error
    name = "fixture" if settings.model_mode == "fixture" else catalog.default_embedding_profile
    profile = catalog.embedding_profiles.get(name or "")
    if profile is None:
        raise ConfigurationError(f"unknown_embedding_profile: models.toml has no {name} entry")
    if (profile.provider == "fixture") != (settings.model_mode == "fixture"):
        raise ConfigurationError("incompatible_profile: embedding provider does not match mode")
    return profile


def _validate_profile_references(catalog: ModelCatalog, prompt: LoadedPrompt) -> None:
    """Raise when the catalog or the prompt names a profile that does not exist.

    Checked before selection so a typo fails every mode, not only the mode that uses it.

    Args:
        catalog: Parsed ``models.toml``.
        prompt: Agent prompt whose optional ``model_profile`` is checked too.

    Raises:
        ConfigurationError: A default, role, vendor, or prompt profile name is unknown.
    """
    names = [
        catalog.default_profile,
        *catalog.roles.values(),
        *catalog.vendor_profiles.values(),
    ]
    if prompt.template.model_profile is not None:
        names.append(prompt.template.model_profile)
    if any(name not in catalog.profiles for name in names):
        raise ConfigurationError("unknown_model_profile: role references missing profile")


def _select_profile_name(
    catalog: ModelCatalog, prompt: LoadedPrompt, vendor: LiveProviderName | None
) -> str:
    """Return the live profile name for the prompt's role or an explicitly selected vendor.

    Args:
        catalog: Parsed ``models.toml`` whose references are already validated.
        prompt: Agent prompt; its ``model_profile`` beats the role binding.
        vendor: Explicitly selected vendor, which beats both.

    Returns:
        A key of ``catalog.profiles``.

    Raises:
        ConfigurationError: ``vendor`` has no entry in ``vendor_profiles``.
    """
    if vendor is not None:
        if vendor not in catalog.vendor_profiles:
            raise ConfigurationError(f"unknown_vendor_profile: models.toml has no {vendor} entry")
        return catalog.vendor_profiles[vendor]
    return prompt.template.model_profile or catalog.roles.get(
        prompt.template.agent, catalog.default_profile
    )


def _require_mode_compatible(profile: ModelProfile, *, is_live: bool) -> ModelProfile:
    """Return the profile, or raise when a fixture profile meets live mode or vice versa.

    Args:
        profile: Selected profile.
        is_live: Whether this invocation is authorized to call a hosted model.

    Returns:
        ``profile`` unchanged.

    Raises:
        ConfigurationError: The profile's provider does not match the mode.
    """
    if (profile.provider == "fixture") == is_live:
        raise ConfigurationError(
            "incompatible_profile: live verification cannot use fixture provider"
        )
    return profile


# TOML has arbitrary nested values; Settings/ModelCatalog validate this untyped I/O boundary.
def _load_toml(path: Path) -> dict[str, Any]:
    """Read a TOML file; callers normalize file and parse failures.

    Args:
        path: TOML file to read.

    Returns:
        The parsed document, not yet validated.

    Raises:
        OSError: The file cannot be read.
        tomllib.TOMLDecodeError: The file is not valid TOML (a ``ValueError``).
    """
    with path.open("rb") as stream:
        return tomllib.load(stream)
