import cv2
import numpy as np
import pytesseract
import re
from PyQt6.QtGui import QImage, QPixmap

TESS_CONFIG = r'--oem 3 --psm 6'

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
    height, width, channel = cv_img.shape
    bytes_per_line = 3 * width
    cv_img_rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
    qimage = QImage(cv_img_rgb.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
    return QPixmap.fromImage(qimage)


def apply_blur_regions(cv_img, regions: list[tuple[int, int, int, int]]):
    result = cv_img.copy()
    for (x, y, w, h) in regions:
        roi = result[y:y+h, x:x+w]
        if roi.size > 0:
            blurred_roi = cv2.GaussianBlur(roi, (51, 51), 30)
            result[y:y+h, x:x+w] = blurred_roi
    return result


def analyze_image(pixmap: QPixmap) -> dict:
    image = qpixmap_to_cv_image(pixmap)
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=TESS_CONFIG)

    lines: dict[tuple, dict] = {}
    n = len(data['text'])
    for i in range(n):
        text = data['text'][i].strip()
        if not text:
            continue
        conf = int(data['conf'][i])
        if conf < 20:
            continue

        key = (data['block_num'][i], data['par_num'][i], data['line_num'][i])
        if key not in lines:
            lines[key] = {'words': [], 'texts': []}
        lines[key]['words'].append((data['left'][i], data['top'][i], data['width'][i], data['height'][i]))
        lines[key]['texts'].append(text)

    ocr_lines = []
    auto_regions = []

    for key, line in lines.items():
        words = line['words']
        texts = line['texts']
        line_text = ' '.join(texts)

        xs = [x for x, y, w, h in words]
        ys = [y for x, y, w, h in words]
        x2s = [x + w for x, y, w, h in words]
        y2s = [y + h for x, y, w, h in words]
        lx, ly = min(xs), min(ys)
        lw, lh = max(x2s) - lx, max(y2s) - ly

        pad = 4
        line_rect = (max(0, lx - pad), max(0, ly - pad), lw + pad * 2, lh + pad * 2)

        ocr_lines.append({
            "rect": line_rect,
            "text": line_text,
            "words": words,
        })

        is_sensitive = any(re.search(pattern, line_text) for pattern in PATTERNS.values())
        if is_sensitive:
            auto_regions.append(line_rect)

    return {
        "cv_image": image,
        "ocr_lines": ocr_lines,
        "auto_regions": auto_regions,
    }


def render_image(cv_image, regions: list[tuple[int, int, int, int]]) -> QPixmap:
    result = apply_blur_regions(cv_image, regions)
    return cv_image_to_qpixmap(result)


def save_clean(cv_image, regions: list[tuple[int, int, int, int]], file_path: str) -> bool:
    result = apply_blur_regions(cv_image, regions)
    if file_path.lower().endswith(('.jpg', '.jpeg')):
        return cv2.imwrite(file_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return cv2.imwrite(file_path, result)
