"""Deterministic stand-ins for the models."""

from kiseki.adapters.fake.models import (
    FakeImageCaptioner,
    FakeLanguageModel,
    FakeTextEmbedder,
)

__all__ = ["FakeImageCaptioner", "FakeLanguageModel", "FakeTextEmbedder"]
