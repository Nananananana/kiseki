"""Consent travels with the observation and is honoured mechanically.

use_for_preference=False keeps a photograph in the journeys but out
of every per-photo reading; None means the record predates the field
and counts as consent, like every earlier carried field. See
ADR-0032.
"""

from datetime import UTC, datetime

from kiseki.domain.photo.observation import PhotoId, PhotoObservation

AT = datetime(2026, 6, 1, 10, tzinfo=UTC)


class TestPreferenceConsent:
    def test_defaults_to_none_and_counts_as_consent(self) -> None:
        observation = PhotoObservation(PhotoId("p1"), AT)
        assert observation.use_for_preference is None
        assert observation.may_inform_preferences

    def test_a_withheld_preference_is_honoured(self) -> None:
        observation = PhotoObservation(
            PhotoId("p1"), AT, None, thumbnail_ref=None, use_for_preference=False
        )
        assert not observation.may_inform_preferences
