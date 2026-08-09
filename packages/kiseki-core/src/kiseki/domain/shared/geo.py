"""Coordinates and distances.

Distance on the globe is computed with the haversine formula on a spherical
earth. The error against a proper ellipsoidal model is around 0.3 percent,
which is far below the accuracy of the coordinates a phone records, and it
keeps the domain layer free of dependencies.
"""

from dataclasses import dataclass
from math import asin, cos, isfinite, radians, sin, sqrt

EARTH_RADIUS_METERS = 6371008.8
"""Mean earth radius as defined by IUGG."""


@dataclass(frozen=True, order=True)
class Distance:
    """A non-negative distance. The unit is part of the type, not of the caller."""

    meters: float

    def __post_init__(self) -> None:
        if not isfinite(self.meters):
            raise ValueError("distance must be a finite number")
        if self.meters < 0:
            raise ValueError("distance cannot be negative")

    @property
    def kilometers(self) -> float:
        return self.meters / 1000

    @classmethod
    def from_kilometers(cls, kilometers: float) -> "Distance":
        return cls(kilometers * 1000)


@dataclass(frozen=True)
class GeoPoint:
    """A point on the earth's surface."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not isfinite(self.latitude) or not isfinite(self.longitude):
            raise ValueError("coordinates must be finite numbers")
        if not -90 <= self.latitude <= 90:
            raise ValueError(f"latitude {self.latitude} is outside [-90, 90]")
        if not -180 <= self.longitude <= 180:
            raise ValueError(f"longitude {self.longitude} is outside [-180, 180]")

    def distance_to(self, other: "GeoPoint") -> Distance:
        """Great circle distance. Symmetric, and correct across the antimeridian."""
        latitude = radians(self.latitude)
        other_latitude = radians(other.latitude)
        half_latitude_delta = radians(other.latitude - self.latitude) / 2
        half_longitude_delta = radians(other.longitude - self.longitude) / 2

        chord = (
            sin(half_latitude_delta) ** 2
            + cos(latitude) * cos(other_latitude) * sin(half_longitude_delta) ** 2
        )
        return Distance(2 * EARTH_RADIUS_METERS * asin(sqrt(min(1.0, chord))))
