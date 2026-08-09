"""Deciding what kind of content a file holds.

Only signals available without looking at pixels are used. A photographed
receipt, menu or whiteboard is indistinguishable from a photograph by metadata
alone, so the ``document`` kind is reserved but never assigned here. Detecting
it needs image understanding, which arrives with captioning in v0.2.
"""

import re
from dataclasses import dataclass

PHOTO = "photo"
SCREENSHOT = "screenshot"
DOCUMENT = "document"
OTHER = "other"

SCREENSHOT_NAME = re.compile(
    r"^(screenshot|screen[ _-]?shot|scr_|shot_|スクリーンショット|screencapture)",
    re.IGNORECASE,
)
LOSSLESS_SUFFIXES = frozenset({".png", ".bmp", ".webp"})
SCREEN_SHAPES = frozenset(
    {
        (9, 16),
        (9, 19),
        (9, 195),
        (9, 20),
        (9, 21),
        (16, 9),
        (19, 9),
        (195, 9),
        (20, 9),
        (21, 9),
        (3, 4),
        (4, 3),
    }
)
SHAPE_TOLERANCE = 0.02


@dataclass(frozen=True)
class MediaEvidence:
    """Everything known about a file before its pixels are examined."""

    filename: str
    suffix: str
    has_camera_metadata: bool
    width: int | None = None
    height: int | None = None


def _looks_like_a_screen(width: int | None, height: int | None) -> bool:
    if not width or not height:
        return False
    ratio = width / height
    return any(abs(ratio - short / long_) < SHAPE_TOLERANCE for short, long_ in SCREEN_SHAPES)


def classify(evidence: MediaEvidence) -> str:
    """Return the content kind for a file.

    The name is checked before camera metadata because an edited or re-saved
    screenshot can carry the metadata of the device that exported it.
    """
    if SCREENSHOT_NAME.match(evidence.filename):
        return SCREENSHOT
    if evidence.has_camera_metadata:
        return PHOTO
    if evidence.suffix.lower() in LOSSLESS_SUFFIXES and _looks_like_a_screen(
        evidence.width, evidence.height
    ):
        return SCREENSHOT
    return OTHER
