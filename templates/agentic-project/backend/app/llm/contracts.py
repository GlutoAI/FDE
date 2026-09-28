"""Immutable data contracts at the provider and prompt boundaries."""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class Contract(BaseModel):
    """A frozen value object that rejects undeclared fields and type coercion."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


ProviderName = Literal["fixture", "openai", "anthropic"]
LiveProviderName = Literal["openai", "anthropic"]


class ModelProfile(Contract):
    """Nonsecret provider selection and hard request limits."""

    provider: ProviderName = Field(description="Registered provider adapter")
    model_id: str = Field(min_length=1, description="Provider model ID or snapshot")
    timeout_seconds: float = Field(gt=0, le=60, description="Request timeout in seconds")
    max_output_tokens: int = Field(ge=16, le=256, description="Diagnostic output token cap")
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh"] | None = Field(
        default=None, description="Optional supported provider reasoning setting"
    )


class EmbeddingProfile(Contract):
    """Nonsecret embedding model selection; vectors from different profiles never mix."""

    provider: Literal["fixture", "openai"] = Field(
        description="Embedding adapter; Anthropic offers no embeddings API"
    )
    model_id: str = Field(min_length=1, description="Provider embedding model ID")
    dimensions: int = Field(ge=8, le=4096, description="Vector length requested and enforced")
    timeout_seconds: float = Field(gt=0, le=60, description="Request timeout in seconds")
    max_batch_size: int = Field(ge=1, le=2048, description="Texts sent per embedding request")

    @property
    def index_version(self) -> str:
        """Identifier stored with every vector so searches compare like with like."""
        return f"{self.provider}:{self.model_id}:{self.dimensions}"


OutputT = TypeVar("OutputT", bound=BaseModel)


class AgentResult(Contract, Generic[OutputT]):
    """Validated agent output plus metadata supplied by the application, never the model."""

    status: Literal["ok"] = Field(default="ok", description="Agent completed successfully")
    output: OutputT = Field(description="Pydantic AI validated agent output")
    provider: ProviderName = Field(description="Provider adapter that served the request")
    model_id: str = Field(min_length=1, description="Model reported by the provider")
    prompt_version: int = Field(description="Prompt revision used")
    prompt_sha256: str = Field(description="Exact YAML content fingerprint")
    input_tokens: int | None = Field(
        default=None, ge=0, description="Observed usage; unknown for fixtures"
    )
    output_tokens: int | None = Field(
        default=None, ge=0, description="Observed usage; unknown for fixtures"
    )


class PromptReference(Contract):
    """A path-safe identifier for a packaged YAML prompt."""

    agent: str = Field(pattern=r"^[a-z][a-z0-9_]*$", description="Prompt directory name")
    version: int = Field(ge=1, description="Immutable prompt version")


class PromptTemplate(Contract):
    """Validated prompt text loaded from an immutable YAML asset."""

    agent: str = Field(min_length=1, description="Agent role owning the prompt")
    version: int = Field(ge=1, description="Prompt revision")
    system: str = Field(min_length=1, max_length=4000, description="Trusted system instructions")
    model_profile: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9_]*$",
        description="Optional named model profile override",
    )
    model: str | None = Field(
        default=None,
        min_length=1,
        max_length=160,
        pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$",
        description="Optional provider model ID; inherits selected profile limits and credentials",
    )
    user: str = Field(min_length=1, max_length=4000, description="Fixed synthetic probe message")


class LoadedPrompt(Contract):
    """A prompt with its exact content fingerprint."""

    template: PromptTemplate = Field(description="Validated YAML content")
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$", description="Hash of the original YAML bytes")
