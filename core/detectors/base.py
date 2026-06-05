from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import numpy as np

from core.regions import Rect


@dataclass(frozen=True)
class Detection:
    rect: Rect
    kind: str
    label: str | None = None
    score: float | None = None


class ObjectDetector(Protocol):
    name: str

    def detect(self, cv_img: np.ndarray) -> list[Detection]:
        ...
