"""
Shared LLM provider for gemara-mcp evaluation harnesses.

Auto-detects the best available LLM backend and provides a unified
interface for text generation. Used by harnesses that need an LLM
(detLLM, DeepEval, MCP Evals, Promptfoo).

Resolution order:
    1. Explicit LLM_PROVIDER env var
    2. Ollama (if reachable at OLLAMA_BASE_URL)
    3. Vertex AI (if VERTEX_PROJECT is set)
    4. OpenAI (if OPENAI_API_KEY is set)

Environment variables:
    LLM_PROVIDER        Force a provider: "ollama", "vertex_ai", "openai"
    OLLAMA_BASE_URL      Ollama endpoint (default: http://localhost:11434)
    OLLAMA_MODEL         Ollama model name (default: qwen2.5:7b)
    VERTEX_PROJECT       Google Cloud project ID
    VERTEX_LOCATION      Vertex AI region (default: us-central1)
    VERTEX_MODEL         Vertex AI model (default: gemini-2.0-flash)
    OPENAI_API_KEY       OpenAI API key
    OPENAI_MODEL         OpenAI model (default: gpt-4o-mini)
    EVAL_MODEL           Override for the litellm model string used by judges
"""

from __future__ import annotations

import os
import urllib.request
import json
from dataclasses import dataclass


@dataclass
class ProviderInfo:
    """Resolved LLM provider details."""

    name: str
    litellm_model: str
    display: str


def _ollama_reachable(base_url: str, timeout: float = 3.0) -> bool:
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def resolve_provider() -> ProviderInfo:
    """Detect the best available LLM backend.

    Returns a ProviderInfo with the litellm-compatible model string.
    Raises RuntimeError if no backend is available.
    """
    explicit = os.environ.get("LLM_PROVIDER", "").strip().lower()

    if explicit == "ollama" or (not explicit and _ollama_env_set()):
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        if explicit == "ollama" or _ollama_reachable(base_url):
            return ProviderInfo(
                name="ollama",
                litellm_model=f"ollama/{model}",
                display=f"Ollama ({model} at {base_url})",
            )
        if explicit == "ollama":
            raise RuntimeError(
                f"LLM_PROVIDER=ollama but Ollama is not reachable at {base_url}"
            )

    if explicit == "vertex_ai" or (not explicit and _vertex_env_set()):
        project = os.environ.get("VERTEX_PROJECT", "")
        location = os.environ.get("VERTEX_LOCATION", "us-central1")
        model = os.environ.get("VERTEX_MODEL", "gemini-2.0-flash")
        if project or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            return ProviderInfo(
                name="vertex_ai",
                litellm_model=f"vertex_ai/{model}",
                display=f"Vertex AI ({model} in {project or 'default'}:{location})",
            )
        if explicit == "vertex_ai":
            raise RuntimeError(
                "LLM_PROVIDER=vertex_ai but VERTEX_PROJECT and "
                "GOOGLE_APPLICATION_CREDENTIALS are not set"
            )

    if explicit == "openai" or (not explicit and os.environ.get("OPENAI_API_KEY")):
        model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        return ProviderInfo(
            name="openai",
            litellm_model=f"openai/{model}",
            display=f"OpenAI ({model})",
        )

    if not explicit:
        base_url = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")
        if _ollama_reachable(base_url):
            return ProviderInfo(
                name="ollama",
                litellm_model=f"ollama/{model}",
                display=f"Ollama ({model} at {base_url})",
            )

    raise RuntimeError(
        "No LLM backend available. Set one of:\n"
        "  - OLLAMA_BASE_URL (and ensure Ollama is running)\n"
        "  - VERTEX_PROJECT + VERTEX_LOCATION (Google Cloud Vertex AI)\n"
        "  - OPENAI_API_KEY (OpenAI)\n"
        "  - LLM_PROVIDER to force a specific backend"
    )


def resolve_eval_model() -> str:
    """Return the litellm model string for LLM-as-judge use.

    Checks EVAL_MODEL env var first, then falls back to resolve_provider().
    """
    override = os.environ.get("EVAL_MODEL", "").strip()
    if override:
        return override
    return resolve_provider().litellm_model


def generate(prompt: str, temperature: float = 0.0, seed: int | None = 42) -> str:
    """Generate text using the auto-detected LLM backend via litellm.

    This is a synchronous convenience wrapper. For async usage, call
    litellm.acompletion directly with resolve_provider().litellm_model.
    """
    import litellm

    provider = resolve_provider()

    kwargs: dict = {
        "model": provider.litellm_model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": temperature,
    }

    if provider.name == "ollama" and seed is not None:
        kwargs.setdefault("extra_body", {})
        kwargs["extra_body"]["options"] = {"seed": seed}

    response = litellm.completion(**kwargs)
    return response.choices[0].message.content or ""


def _ollama_env_set() -> bool:
    return bool(
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_MODEL")
    )


def _vertex_env_set() -> bool:
    return bool(
        os.environ.get("VERTEX_PROJECT")
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    )
