import cv2
import numpy as np
import pytesseract
import re
from PyQt6.QtGui import QImage, QPixmap

TESS_CONFIG = r'--oem 3 --psm 11'

PATTERNS = {
    "Email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    "IP": r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
    "Secret": r'(?i)\b(secret|password|passwd|token|api[_-]?key|auth)\b',
}


def qpixmap_to_cv_image(pixmap: QPixmap):
    qimage = pixmap.toImage().convertToFormat(QImage.Format.Format_RGBA8888)
    width = qimage.width()
    height = qimage.height()
    ptr = qimage.bits()
    ptr.setsize(height * width * 4)
    arr = np.frombuffer(ptr, np.uint8).reshape((height, width, 4))
    return cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)


def cv_image_to_qpixmap(cv_img):
    height, width, _ = cv_img.shape
    bytes_per_line = 3 * width
    cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    qimage = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


def apply_blur_regions(cv_img, regions: list[tuple[int, int, int, int]]):
    result = cv_img.copy()
    for (x, y, w, h) in regions:
        roi = result[y:y+h, x:x+w]
        if roi.size > 0:
            result[y:y+h, x:x+w] = cv2.GaussianBlur(roi, (51, 51), 30)
    return result


def analyze_image(pixmap: QPixmap) -> dict:
    image = qpixmap_to_cv_image(pixmap)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=TESS_CONFIG)

    ocr_boxes = []
    auto_regions = []
    pad = 4

    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if not text or int(data['conf'][i]) < 20:
            continue
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        rect = (max(0, x - pad), max(0, y - pad), w + pad * 2, h + pad * 2)
        ocr_boxes.append({"rect": rect, "text": text})
        if any(re.search(pattern, text) for pattern in PATTERNS.values()):
            auto_regions.append(rect)

    return {
        "cv_image": image,
        "ocr_boxes": ocr_boxes,
        "auto_regions": auto_regions,
    }


def render_image(cv_image, regions: list[tuple[int, int, int, int]]) -> QPixmap:
    return cv_image_to_qpixmap(apply_blur_regions(cv_image, regions))


def save_clean(cv_image, regions: list[tuple[int, int, int, int]], file_path: str) -> bool:
    result = apply_blur_regions(cv_image, regions)
    if file_path.lower().endswith(('.jpg', '.jpeg')):
        return cv2.imwrite(file_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return cv2.imwrite(file_path, result)
