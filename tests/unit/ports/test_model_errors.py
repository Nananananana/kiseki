"""Specification for what the model errors mean.

A caller has to decide whether to retry, and the exception type is how it knows.
This matters more for a hosted model than a local one, and the ports are written
for both.
"""

import pytest

from kiseki.ports.models import ModelRefused, ModelUnavailable


class TestModelErrors:
    def test_unavailable_means_retrying_may_work(self) -> None:
        """A timeout, a rate limit, a model still loading."""
        assert issubclass(ModelUnavailable, RuntimeError)

    def test_refused_means_retrying_will_not(self) -> None:
        """A malformed request, an image too large, content declined."""
        assert issubclass(ModelRefused, RuntimeError)

    def test_they_are_distinct(self) -> None:
        assert not issubclass(ModelRefused, ModelUnavailable)
        assert not issubclass(ModelUnavailable, ModelRefused)

    def test_both_carry_a_message(self) -> None:
        with pytest.raises(ModelUnavailable, match="took too long"):
            raise ModelUnavailable("the model took too long to answer")
