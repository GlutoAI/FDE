"""Compose the Pydantic AI connection agent and own each vendor's async SDK client lifetime.

This is the model-side composition root: the only module that names concrete providers and
embedders. Opening a client sends no request; inference happens only in ``run_agent``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from pydantic import SecretStr
from pydantic_ai.embeddings import Embedder
from pydantic_ai.embeddings.openai import OpenAIEmbeddingModel
from pydantic_ai.models.anthropic import AnthropicModel
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.models.test import TestModel
from pydantic_ai.providers.anthropic import AnthropicProvider
from pydantic_ai.providers.openai import OpenAIProvider

from app.agents.connection.agent import ConnectionAgent
from app.agents.connection.models import ConnectionInput, ConnectionOutput
from app.core.errors import ConfigurationError
from app.core.settings import (
    API_KEY_VARIABLES,
    ProjectLocation,
    Settings,
    load_model_profile,
)
from app.llm.contracts import (
    EmbeddingProfile,
    LiveProviderName,
    LoadedPrompt,
    ModelProfile,
    PromptReference,
)
from app.llm.prompts import load_prompt
from app.llm.provider import ModelProvider
from app.llm.providers.anthropic import AnthropicModelProvider
from app.llm.providers.fixture import FixtureModelProvider
from app.llm.providers.openai import OpenAIModelProvider
from app.llm.runtime import build_agent_runtime
from app.rag.embedder import BaseEmbedder, HashingEmbedder, PydanticAIEmbedder

# Pinned so an ambient OPENAI_BASE_URL or ANTHROPIC_BASE_URL cannot redirect keys elsewhere.
OPENAI_BASE_URL = "https://api.openai.com/v1"
ANTHROPIC_BASE_URL = "https://api.anthropic.com"


@asynccontextmanager
async def create_connection_agent(
    location: ProjectLocation,
    settings: Settings,
    *,
    vendor: LiveProviderName | None = None,
) -> AsyncIterator[ConnectionAgent]:
    """Resolve YAML model selection, compose a typed agent, and close its client on exit.

    Args:
        location: Explicit project config root.
        settings: Validated mode and local credentials; YAML never carries credentials.
        vendor: Vendor chosen explicitly for a live probe; None uses the configured role.

    Yields:
        A configured agent; only run_agent performs inference.

    Raises:
        ConfigurationError: Prompt, profile, or the selected vendor's credentials are invalid.
    """
    prompt = load_prompt(PromptReference(agent="connection", version=1))
    profile = load_model_profile(location, settings, prompt, vendor=vendor)
    async with open_model_provider(profile, settings) as provider:
        yield build_connection_agent(provider, prompt, profile)


@asynccontextmanager
async def open_model_provider(
    profile: ModelProfile, settings: Settings
) -> AsyncIterator[ModelProvider]:
    """Open the SDK client for the profile's vendor and close it on exit.

    Args:
        profile: Resolved provider and model; its timeout bounds the client.
        settings: Source of the selected vendor's key.

    Yields:
        The provider for that vendor; the fixture provider opens no client.

    Raises:
        ConfigurationError: The selected vendor's key is absent.
    """
    if profile.provider == "fixture":
        yield FixtureModelProvider(build_fixture_model(profile))
        return
    api_key = _require_api_key(settings, profile.provider)
    # max_retries=0 everywhere: a failed probe costs one request, never a silent retry loop.
    if profile.provider == "openai":
        async with AsyncOpenAI(
            api_key=api_key.get_secret_value(),
            base_url=OPENAI_BASE_URL,
            max_retries=0,
            timeout=profile.timeout_seconds,
        ) as openai_client:
            model = OpenAIResponsesModel(
                profile.model_id, provider=OpenAIProvider(openai_client=openai_client)
            )
            yield OpenAIModelProvider(model)
        return
    async with AsyncAnthropic(
        api_key=api_key.get_secret_value(),
        base_url=ANTHROPIC_BASE_URL,
        max_retries=0,
        timeout=profile.timeout_seconds,
    ) as anthropic_client:
        yield AnthropicModelProvider(
            AnthropicModel(
                profile.model_id, provider=AnthropicProvider(anthropic_client=anthropic_client)
            )
        )


def build_fixture_model(profile: ModelProfile) -> TestModel:
    """Build the scripted offline model that always returns a valid connection output.

    Args:
        profile: Fixture profile whose model ID is reported as the served model.

    Returns:
        A test model that makes no requests and calls no tools.
    """
    return TestModel(
        call_tools=[],
        custom_output_text=ConnectionOutput(status="ok", marker="CONNECTION_OK").model_dump_json(),
        model_name=profile.model_id,
        profile={"supports_json_schema_output": True},
    )


def build_connection_agent(
    provider: ModelProvider,
    prompt: LoadedPrompt,
    profile: ModelProfile,
) -> ConnectionAgent:
    """Assemble the initial typed agent without I/O.

    Args:
        provider: Live or fixture model boundary.
        prompt: Agent YAML already loaded and validated.
        profile: Resolved provider settings and request limits.

    Returns:
        A connection agent with matching Pydantic input and output classes.

    Raises:
        ConfigurationError: The provider cannot honor a profile setting.
    """
    runtime = build_agent_runtime(
        provider,
        prompt,
        profile,
        input_type=ConnectionInput,
        output_type=ConnectionOutput,
    )
    return ConnectionAgent(runtime, provider, prompt, profile, input_type=ConnectionInput)


@asynccontextmanager
async def open_embedder(
    profile: EmbeddingProfile, settings: Settings
) -> AsyncIterator[BaseEmbedder]:
    """Open the embedding client for the profile and close it on exit.

    Args:
        profile: Resolved embedding profile; its timeout bounds the client.
        settings: Source of the OpenAI key for hosted embeddings.

    Yields:
        The embedder; the fixture opens no client and makes no requests.

    Raises:
        ConfigurationError: Hosted embeddings are selected without the OpenAI key.
    """
    if profile.provider == "fixture":
        yield HashingEmbedder(profile)
        return
    api_key = _require_api_key(settings, "openai")
    async with AsyncOpenAI(
        api_key=api_key.get_secret_value(),
        base_url=OPENAI_BASE_URL,
        max_retries=0,
        timeout=profile.timeout_seconds,
    ) as openai_client:
        yield build_openai_embedder(profile, openai_client)


def build_openai_embedder(profile: EmbeddingProfile, openai_client: AsyncOpenAI) -> BaseEmbedder:
    """Assemble a hosted OpenAI embedder without I/O.

    Args:
        profile: OpenAI embedding profile.
        openai_client: Client whose lifetime the caller owns.

    Returns:
        An embedder that requests ``profile.dimensions``-length vectors.
    """
    model = OpenAIEmbeddingModel(
        profile.model_id, provider=OpenAIProvider(openai_client=openai_client)
    )
    return PydanticAIEmbedder(profile, Embedder(model, instrument=False))


def _require_api_key(settings: Settings, provider: LiveProviderName) -> SecretStr:
    """Return the vendor's key, or raise naming only the missing variable.

    Args:
        settings: Settings holding the optional per-vendor keys.
        provider: Vendor whose key the next client needs.

    Returns:
        The secret-wrapped key; the caller unwraps it only to hand it to the SDK client.

    Raises:
        ConfigurationError: The key is absent. The message names the variable, never a value.
    """
    api_key = settings.get_api_key(provider)
    if api_key is None:
        raise ConfigurationError(f"missing_credentials: set {API_KEY_VARIABLES[provider]}")
    return api_key
