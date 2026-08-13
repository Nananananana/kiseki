"""Adapters that speak to a local Ollama."""

from kiseki.adapters.ollama.models import (
    OllamaImageCaptioner,
    OllamaLanguageModel,
    OllamaTextEmbedder,
)

__all__ = [
    "OllamaImageCaptioner",
    "OllamaLanguageModel",
    "OllamaTextEmbedder",
]
