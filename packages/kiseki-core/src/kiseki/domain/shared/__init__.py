"""Value objects shared across the domain.

Everything here is immutable, validated on construction, and free of any
dependency outside the standard library.
"""

from kiseki.domain.shared.confidence import Confidence
from kiseki.domain.shared.geo import EARTH_RADIUS_METERS, Distance, GeoArea, GeoPoint
from kiseki.domain.shared.settings import OutingSettings, StopSettings
from kiseki.domain.shared.speed import Speed
from kiseki.domain.shared.time_range import TimeRange

__all__ = [
    "EARTH_RADIUS_METERS",
    "Confidence",
    "Distance",
    "GeoArea",
    "GeoPoint",
    "OutingSettings",
    "Speed",
    "StopSettings",
    "TimeRange",
]
