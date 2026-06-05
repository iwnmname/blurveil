from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from core.detectors.base import Detection, ObjectDetector
from core.regions import Rect, pad_rect_xy


FACE_CASCADE_FILENAME = "haarcascade_frontalface_default.xml"
FACE_PAD_RATIO = 0.18
QR_PAD = 8


class QRCodeDetector:
    name = "qr"

    def detect(self, cv_img: np.ndarray) -> list[Detection]:
        detector = cv2.QRCodeDetector()
        retval, _decoded, points, _ = detector.detectAndDecodeMulti(cv_img)
        detections: list[Detection] = []

        if not retval or points is None:
            return detections

        for pts in points:
            pts = pts.astype(int)
            x_min = int(pts[:, 0].min())
            y_min = int(pts[:, 1].min())
            x_max = int(pts[:, 0].max())
            y_max = int(pts[:, 1].max())
            rect = pad_rect_xy((x_min, y_min, x_max - x_min, y_max - y_min), cv_img.shape, QR_PAD)
            if rect is not None:
                detections.append(Detection(rect=rect, kind=self.name, label="QR code"))

        return detections


class FaceDetector:
    name = "face"

    def __init__(
        self,
        cascade_path: str | Path | None = None,
        *,
        scale_factor: float = 1.1,
        min_neighbors: int = 5,
        min_size: tuple[int, int] = (24, 24),
    ):
        self.cascade_path = Path(cascade_path) if cascade_path is not None else _default_face_cascade_path()
        self.scale_factor = scale_factor
        self.min_neighbors = min_neighbors
        self.min_size = min_size
        self._cascade = None

    def detect(self, cv_img: np.ndarray) -> list[Detection]:
        cascade = self._load_cascade()
        if cascade is None:
            return []

        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            flags=cv2.CASCADE_SCALE_IMAGE,
            minSize=self.min_size,
        )

        detections: list[Detection] = []
        for x, y, w, h in faces:
            pad_x = max(4, int(w * FACE_PAD_RATIO))
            pad_y = max(4, int(h * FACE_PAD_RATIO))
            rect = pad_rect_xy((int(x), int(y), int(w), int(h)), cv_img.shape, pad_x, pad_y)
            if rect is not None:
                detections.append(Detection(rect=rect, kind=self.name, label="Face"))
        return detections

    def _load_cascade(self):
        if self._cascade is not None:
            return self._cascade
        if self.cascade_path is None or not self.cascade_path.exists():
            return None

        cascade = cv2.CascadeClassifier(str(self.cascade_path))
        if cascade.empty():
            return None

        self._cascade = cascade
        return self._cascade


def _default_face_cascade_path() -> Path | None:
    haarcascades = getattr(cv2.data, "haarcascades", None)
    if not haarcascades:
        return None
    return Path(haarcascades) / FACE_CASCADE_FILENAME


DEFAULT_OBJECT_DETECTORS: tuple[ObjectDetector, ...] = (
    QRCodeDetector(),
    FaceDetector(),
)


def detect_objects(
    cv_img: np.ndarray,
    detectors: tuple[ObjectDetector, ...] | list[ObjectDetector] = DEFAULT_OBJECT_DETECTORS,
) -> list[Detection]:
    detections: list[Detection] = []
    for detector in detectors:
        detections.extend(detector.detect(cv_img))
    return detections


def detect_object_regions(
    cv_img: np.ndarray,
    detectors: tuple[ObjectDetector, ...] | list[ObjectDetector] = DEFAULT_OBJECT_DETECTORS,
) -> list[Rect]:
    return [detection.rect for detection in detect_objects(cv_img, detectors)]


def detect_qr_codes(cv_img: np.ndarray) -> list[Rect]:
    return [detection.rect for detection in QRCodeDetector().detect(cv_img)]


def detect_faces(cv_img: np.ndarray) -> list[Rect]:
    return [detection.rect for detection in FaceDetector().detect(cv_img)]
