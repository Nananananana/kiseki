"""Specification for the values that cross the model ports."""

import pytest
from kiseki.ports.models import CaptionRequest, Completion, Usage


class TestCaptionRequest:
    def test_carries_images_and_a_prompt(self) -> None:
        request = CaptionRequest((b"one", b"two"), "describe this")
        assert len(request.images) == 2
        assert request.prompt == "describe this"

    def test_context_is_optional(self) -> None:
        """Where and when a photograph was taken helps, but is not required."""
        assert CaptionRequest((b"one",), "describe").context == ""

    def test_rejects_a_request_with_no_images(self) -> None:
        with pytest.raises(ValueError, match="at least one image"):
            CaptionRequest((), "describe")

    def test_rejects_a_blank_prompt(self) -> None:
        with pytest.raises(ValueError, match="prompt"):
            CaptionRequest((b"one",), "   ")


class TestCompletion:
    def test_records_which_model_produced_it(self) -> None:
        """A caption and the narrative written from it must be traceable."""
        assert Completion("some text", "qwen3-vl:8b").model == "qwen3-vl:8b"

    def test_token_counts_default_to_zero(self) -> None:
        completion = Completion("some text", "a-model")
        assert completion.input_tokens == 0
        assert completion.output_tokens == 0


class TestUsage:
    def test_starts_at_nothing(self) -> None:
        usage = Usage()
        assert usage.calls == 0
        assert usage.failures == 0

    def test_recording_returns_a_new_value(self) -> None:
        original = Usage()
        updated = original.record(Completion("t", "m", 10, 5))
        assert original.calls == 0
        assert updated.calls == 1

    def test_accumulates_tokens(self) -> None:
        usage = Usage().record(Completion("t", "m", 10, 5))
        usage = usage.record(Completion("t", "m", 3, 2))
        assert usage.input_tokens == 13
        assert usage.output_tokens == 7

    def test_counts_a_failure_as_a_call(self) -> None:
        """A refused request still costs time, and may still cost money."""
        usage = Usage().record_failure()
        assert usage.calls == 1
        assert usage.failures == 1
