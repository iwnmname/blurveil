import cv2
import numpy as np
from PyQt6.QtGui import QImage, QPixmap

from core.analyzer import (
    BOX_PAD,
    DIRECT_PATTERNS,
    OCR_MIN_CONFIDENCE,
    SECRET_ASSIGNMENT_RE,
    SECRET_KEYWORD_RE,
    TESS_CONFIG,
    _configure_bundled_tesseract,
    _confidence,
    _line_groups,
    _line_text,
    _looks_like_luhn_number,
    _looks_like_phone_number,
    _matches_direct_sensitive_value,
    _runtime_paths,
    _sensitive_line_region,
    analyze_cv_image,
    pytesseract,
)
from core.detectors import detect_faces, detect_object_regions, detect_qr_codes
from core.regions import Rect, dedupe_regions, pad_rect, union_rect


def qimage_to_cv_image(qimage: QImage):
    qimage = qimage.convertToFormat(QImage.Format.Format_RGBA8888)
    width = qimage.width()
    height = qimage.height()
    ptr = qimage.bits()
    ptr.setsize(height * width * 4)
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)


def qpixmap_to_cv_image(pixmap: QPixmap):
    return qimage_to_cv_image(pixmap.toImage())


def cv_image_to_qpixmap(cv_img):
    height, width, _ = cv_img.shape
    bytes_per_line = 3 * width
    cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    qimage = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


def apply_blur_regions(cv_img, regions: list[Rect]):
    result = cv_img.copy()
    for (x, y, w, h) in regions:
        roi = result[y:y+h, x:x+w]
        if roi.size > 0:
            result[y:y+h, x:x+w] = cv2.GaussianBlur(roi, (51, 51), 30)
    return result


def analyze_qimage(qimage: QImage) -> dict:
    return analyze_cv_image(qimage_to_cv_image(qimage))


def analyze_image(pixmap: QPixmap) -> dict:
    return analyze_cv_image(qpixmap_to_cv_image(pixmap))


def render_image(cv_image, regions: list[Rect]) -> QPixmap:
    return cv_image_to_qpixmap(apply_blur_regions(cv_image, regions))


def save_clean(cv_image, regions: list[Rect], file_path: str) -> bool:
    result = apply_blur_regions(cv_image, regions)
    if file_path.lower().endswith(('.jpg', '.jpeg')):
        return cv2.imwrite(file_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return cv2.imwrite(file_path, result)


_union_rect = union_rect
_dedupe_regions = dedupe_regions


def _pad_rect(rect: Rect, pad: int = BOX_PAD) -> Rect:
    return pad_rect(rect, pad)
