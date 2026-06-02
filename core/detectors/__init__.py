from core.detectors.base import Detection, ObjectDetector
from core.detectors.objects import (
    DEFAULT_OBJECT_DETECTORS,
    FaceDetector,
    QRCodeDetector,
    detect_faces,
    detect_object_regions,
    detect_objects,
    detect_qr_codes,
)

__all__ = [
    "DEFAULT_OBJECT_DETECTORS",
    "Detection",
    "FaceDetector",
    "ObjectDetector",
    "QRCodeDetector",
    "detect_faces",
    "detect_object_regions",
    "detect_objects",
    "detect_qr_codes",
]
