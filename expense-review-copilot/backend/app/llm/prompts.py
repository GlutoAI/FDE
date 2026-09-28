"""Load packaged YAML safely; no dynamic imports, evaluation, or parent traversal."""

from hashlib import sha256
from importlib.resources import files

import yaml
from pydantic import ValidationError

from app.core.errors import ConfigurationError
from app.llm.contracts import LoadedPrompt, PromptReference, PromptTemplate


def load_prompt(reference: PromptReference) -> LoadedPrompt:
    """Read and validate one exact packaged YAML version.

    Args:
        reference: Validated agent directory and integer revision.

    Returns:
        Typed prompt and SHA-256 fingerprint of its bytes.

    Raises:
        ConfigurationError: Prompt is absent, malformed, or has mismatched identity.
    """
    try:
        path = files("app").joinpath("prompts", reference.agent, f"v{reference.version}.yaml")
        content = path.read_bytes()
        template = PromptTemplate.model_validate(yaml.safe_load(content))
        if template.agent != reference.agent or template.version != reference.version:
            raise ConfigurationError("prompt_identity_mismatch: check YAML agent and version")
        return LoadedPrompt(template=template, sha256=sha256(content).hexdigest())
    except (OSError, ValueError, yaml.YAMLError, ValidationError) as error:
        raise ConfigurationError("invalid_prompt: check the packaged YAML prompt") from error
