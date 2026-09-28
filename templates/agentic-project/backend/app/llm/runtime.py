"""Construct typed Pydantic AI runtimes and normalize errors without exposing response bodies.

This module is vendor-neutral: vendor settings, output modes, and SDK errors come from the
injected ModelProvider.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from pydantic_ai import Agent
from pydantic_ai.exceptions import (
    ModelAPIError,
    ModelHTTPError,
    UnexpectedModelBehavior,
    UsageLimitExceeded,
    UserError,
)

from app.core.errors import AgentOutputError, ConfigurationError, ProviderError
from app.llm.contracts import LoadedPrompt, ModelProfile
from app.llm.provider import ModelProvider

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


def build_agent_runtime(
    provider: ModelProvider,
    prompt: LoadedPrompt,
    profile: ModelProfile,
    *,
    input_type: type[InputT],
    output_type: type[OutputT],
) -> Agent[InputT, OutputT]:
    """Build a one-request typed runtime without network I/O.

    Args:
        provider: Configured vendor boundary, including offline fixtures.
        prompt: Validated agent YAML.
        profile: Resolved limits and model selection.
        input_type: Validated request type, also used as typed runtime dependencies.
        output_type: Pydantic schema the response must satisfy.

    Returns:
        A Pydantic AI agent with output repair and model retries disabled.

    Raises:
        ConfigurationError: The provider cannot honor a profile setting.
    """
    return Agent[InputT, OutputT](
        model=provider.get_model(),
        deps_type=input_type,
        output_type=provider.build_output_spec(output_type),
        instructions=prompt.template.system,
        name=prompt.template.agent,
        model_settings=provider.build_model_settings(profile),
        # No automatic re-ask on invalid output: a bad response fails loudly and costs one call.
        retries=0,
    )


@contextmanager
def normalize_model_errors(provider: ModelProvider) -> Iterator[None]:
    """Translate provider/runtime failures into safe application errors.

    Args:
        provider: The vendor whose SDK errors may surface during the call.

    Yields:
        Control to the single model invocation.

    Raises:
        ProviderError: Provider, transport, timeout, or malformed protocol response failed.
        AgentOutputError: The response violates the output schema or request limit.
        ConfigurationError: Pydantic AI rejected the model configuration.
    """
    # Order matters: ModelHTTPError subclasses ModelAPIError. Every message is a fixed code;
    # the original exception, which may hold the response body, stays only in __cause__.
    try:
        yield
    except TimeoutError as error:
        raise ProviderError("timeout: model request exceeded its timeout") from error
    except ModelHTTPError as error:
        code = classify_http_status(error.status_code, error.body)
        raise ProviderError(f"{code}: model provider rejected the request") from error
    except ModelAPIError as error:
        code = provider.classify_sdk_error(error.__cause__) or "network"
        raise ProviderError(f"{code}: model request failed") from error
    except UserError as error:
        raise ConfigurationError(
            "unsupported_model_configuration: check native output support"
        ) from error
    except (UnexpectedModelBehavior, UsageLimitExceeded, ValidationError) as error:
        raise AgentOutputError(
            "invalid_output: model response failed the agent contract"
        ) from error
    except (AttributeError, TypeError) as error:
        # Adapters raise these when a 200 response lacks fields they read (e.g. output: null).
        raise ProviderError("invalid_response: provider returned malformed fields") from error
    except Exception as error:
        # Some SDK errors reach here unwrapped by Pydantic AI; anything unrecognized is a bug.
        sdk_error_code = provider.classify_sdk_error(error)
        if sdk_error_code is None:
            raise
        raise ProviderError(f"{sdk_error_code}: model request failed") from error


def classify_http_status(status: int, body: object) -> str:
    """Return a safe error code for a provider HTTP status, reading only a known body code.

    Args:
        status: HTTP status returned by the provider.
        body: Parsed error body; only its ``code`` field is read, never its message.

    Returns:
        One of quota, rate_limit, authentication, permission, model_unavailable,
        invalid_request, or provider_error.
    """
    content = body.get("error", body) if isinstance(body, dict) else {}
    code = content.get("code") if isinstance(content, dict) else None
    if status == 429:
        return "quota" if code == "insufficient_quota" else "rate_limit"
    return {
        401: "authentication",
        403: "permission",
        404: "model_unavailable",
        400: "invalid_request",
    }.get(status, "provider_error")
