"""Specification for what the model errors mean.

A caller has to decide whether to retry, and the exception type is how it knows.
This matters more for a hosted model than a local one, and the ports are written
for both.
"""

import pytest
from kiseki.ports.models import ModelRefusedError, ModelUnavailableError


class TestModelErrors:
    def test_unavailable_means_retrying_may_work(self) -> None:
        """A timeout, a rate limit, a model still loading."""
        assert issubclass(ModelUnavailableError, RuntimeError)

    def test_refused_means_retrying_will_not(self) -> None:
        """A malformed request, an image too large, content declined."""
        assert issubclass(ModelRefusedError, RuntimeError)

    def test_they_are_distinct(self) -> None:
        assert not issubclass(ModelRefusedError, ModelUnavailableError)
        assert not issubclass(ModelUnavailableError, ModelRefusedError)

    def test_both_carry_a_message(self) -> None:
        with pytest.raises(ModelUnavailableError, match="took too long"):
            raise ModelUnavailableError("the model took too long to answer")
