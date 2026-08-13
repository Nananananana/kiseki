"""The Ollama adapters against a real Ollama.

Excluded from CI by the llm marker; run deliberately with
`uv run pytest -m llm` on a machine where Ollama is serving the
reference models from docs/models.md.

The shared captioner contract sends arbitrary bytes as images, which a
real vision model rejects, so the captioner is exercised here with a
generated image instead of by inheritance. Making that contract
runnable against real adapters is a refinement for later.
"""

from io import BytesIO

import pytest
from kiseki.adapters.ollama.models import (
    OllamaImageCaptioner,
    OllamaLanguageModel,
    OllamaTextEmbedder,
)
from kiseki.ports.models import CaptionRequest
from model_contract import LanguageModelContract, TextEmbedderContract
from PIL import Image

pytestmark = pytest.mark.llm


def _photograph(colour: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (128, 128), colour).save(buffer, format="PNG")
    return buffer.getvalue()


class TestOllamaLanguageModel(LanguageModelContract):
    @pytest.fixture
    def language_model(self) -> OllamaLanguageModel:
        return OllamaLanguageModel()


class TestOllamaTextEmbedder(TextEmbedderContract):
    @pytest.fixture
    def embedder(self) -> OllamaTextEmbedder:
        return OllamaTextEmbedder()


class TestOllamaImageCaptioner:
    def test_describes_a_real_image(self) -> None:
        captioner = OllamaImageCaptioner()
        request = CaptionRequest(
            (_photograph((200, 30, 30)),),
            "Describe this image in one sentence.",
        )
        result = captioner.caption([request])[0]
        assert result.text.strip()
        assert result.model.strip()
        assert captioner.usage.calls == 1

    def test_accepts_several_images_in_one_request(self) -> None:
        request = CaptionRequest(
            (_photograph((200, 30, 30)), _photograph((30, 30, 200))),
            "Describe these images in one sentence.",
        )
        assert OllamaImageCaptioner().caption([request])[0].text.strip()
