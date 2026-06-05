import cv2
import numpy as np
import pytesseract
import re
from PyQt6.QtGui import QImage, QPixmap

TESS_CONFIG = r'--oem 3 --psm 11'
OCR_MIN_CONFIDENCE = 20
BOX_PAD = 4

DIRECT_PATTERNS = {
    "Email": re.compile(r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'),
    "IPv4": re.compile(
        r'\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b'
    ),
    "IPv6": re.compile(r'\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b'),
    "Phone": re.compile(r'(?<!\w)\+?\d[\d\s().-]{7,}\d(?!\w)'),
    "CreditCard": re.compile(r'(?<!\d)(?:\d[ -]?){13,19}(?!\d)'),
    "JWT": re.compile(r'\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b'),
    "AWSAccessKey": re.compile(r'\b(?:AKIA|ASIA)[0-9A-Z]{16}\b'),
    "GitHubToken": re.compile(r'\bgh[pousr]_[A-Za-z0-9_]{30,}\b'),
    "SlackToken": re.compile(r'\bxox[baprs]-[A-Za-z0-9-]{20,}\b'),
    "PrivateKey": re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'),
    "IBAN": re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b'),
}

SECRET_KEYWORD_RE = re.compile(
    r'(?i)\b('
    r'password|passwd|pwd|passphrase|secret|token|api[_-]?key|access[_-]?key|'
    r'private[_-]?key|client[_-]?secret|auth|authorization|bearer|session|cookie|'
    r'jwt|refresh[_-]?token|access[_-]?token'
    r')\b'
)

SECRET_ASSIGNMENT_RE = re.compile(
    r'(?i)\b('
    r'password|passwd|pwd|passphrase|secret|token|api[_-]?key|access[_-]?key|'
    r'private[_-]?key|client[_-]?secret|auth|authorization|bearer|session|cookie|'
    r'jwt|refresh[_-]?token|access[_-]?token'
    r')\b\s*[:=]\s*\S+'
)


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


def apply_blur_regions(cv_img, regions: list[tuple[int, int, int, int]]):
    result = cv_img.copy()
    for (x, y, w, h) in regions:
        roi = result[y:y+h, x:x+w]
        if roi.size > 0:
            result[y:y+h, x:x+w] = cv2.GaussianBlur(roi, (51, 51), 30)
    return result


def detect_qr_codes(cv_img) -> list[tuple[int, int, int, int]]:
    detector = cv2.QRCodeDetector()
    retval, _decoded, points, _ = detector.detectAndDecodeMulti(cv_img)
    regions = []
    if retval and points is not None:
        pad = 8
        h_img, w_img = cv_img.shape[:2]
        for pts in points:
            pts = pts.astype(int)
            x_min = max(0, int(pts[:, 0].min()) - pad)
            y_min = max(0, int(pts[:, 1].min()) - pad)
            x_max = min(w_img, int(pts[:, 0].max()) + pad)
            y_max = min(h_img, int(pts[:, 1].max()) + pad)
            regions.append((x_min, y_min, x_max - x_min, y_max - y_min))
    return regions


def _confidence(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def _pad_rect(rect: tuple[int, int, int, int], pad: int = BOX_PAD) -> tuple[int, int, int, int]:
    x, y, w, h = rect
    return (max(0, x - pad), max(0, y - pad), w + pad * 2, h + pad * 2)


def _union_rect(rects: list[tuple[int, int, int, int]]) -> tuple[int, int, int, int] | None:
    if not rects:
        return None

    x_min = min(rect[0] for rect in rects)
    y_min = min(rect[1] for rect in rects)
    x_max = max(rect[0] + rect[2] for rect in rects)
    y_max = max(rect[1] + rect[3] for rect in rects)
    return (x_min, y_min, x_max - x_min, y_max - y_min)


def _dedupe_regions(regions: list[tuple[int, int, int, int]]) -> list[tuple[int, int, int, int]]:
    seen = set()
    result = []
    for region in regions:
        if region not in seen:
            seen.add(region)
            result.append(region)
    return result


def _looks_like_luhn_number(text: str) -> bool:
    digits = re.sub(r'\D', '', text)
    if not 13 <= len(digits) <= 19:
        return False

    total = 0
    reverse_digits = digits[::-1]
    for i, char in enumerate(reverse_digits):
        value = int(char)
        if i % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _looks_like_phone_number(text: str) -> bool:
    if re.fullmatch(r'\d{1,3}(?:\.\d{1,3}){3}', text.strip()):
        return False

    digits = re.sub(r'\D', '', text)
    return 10 <= len(digits) <= 15


def _matches_direct_sensitive_value(text: str) -> bool:
    for name, pattern in DIRECT_PATTERNS.items():
        if name == "CreditCard":
            if any(_looks_like_luhn_number(match.group(0)) for match in pattern.finditer(text)):
                return True
            continue
        if name == "Phone":
            if any(_looks_like_phone_number(match.group(0)) for match in pattern.finditer(text)):
                return True
            continue
        if pattern.search(text):
            return True
    return False


def _line_groups(entries: list[dict]) -> list[list[dict]]:
    grouped: dict[tuple, list[dict]] = {}
    for entry in entries:
        key = (
            entry.get("block_num"),
            entry.get("par_num"),
            entry.get("line_num"),
        )
        grouped.setdefault(key, []).append(entry)

    lines = []
    for words in grouped.values():
        words.sort(key=lambda item: item["rect"][0])
        lines.append(words)
    lines.sort(key=lambda words: (words[0]["rect"][1], words[0]["rect"][0]))
    return lines


def _line_text(words: list[dict]) -> str:
    return " ".join(word["text"] for word in words)


def _sensitive_line_region(words: list[dict]) -> tuple[int, int, int, int] | None:
    text = _line_text(words)
    if not SECRET_ASSIGNMENT_RE.search(text) and not SECRET_KEYWORD_RE.search(text):
        return None

    for index, word in enumerate(words):
        if SECRET_KEYWORD_RE.search(word["text"]):
            tail_words = words[index:]
            return _union_rect([word["rect"] for word in tail_words])
    return _union_rect([word["rect"] for word in words])


def analyze_cv_image(image) -> dict:
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=TESS_CONFIG)

    ocr_boxes = []
    ocr_entries = []
    auto_regions = []

    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if not text or _confidence(data['conf'][i]) < OCR_MIN_CONFIDENCE:
            continue
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        rect = _pad_rect((x, y, w, h))
        ocr_boxes.append({"rect": rect, "text": text})
        ocr_entries.append({
            "rect": rect,
            "text": text,
            "block_num": data.get("block_num", [None])[i],
            "par_num": data.get("par_num", [None])[i],
            "line_num": data.get("line_num", [None])[i],
        })
        if _matches_direct_sensitive_value(text):
            auto_regions.append(rect)

    for line_words in _line_groups(ocr_entries):
        line_text = _line_text(line_words)
        if _matches_direct_sensitive_value(line_text):
            region = _union_rect([word["rect"] for word in line_words])
            if region is not None:
                auto_regions.append(region)

        region = _sensitive_line_region(line_words)
        if region is not None:
            auto_regions.append(region)

    auto_regions.extend(detect_qr_codes(image))

    return {
        "cv_image": image,
        "ocr_boxes": ocr_boxes,
        "auto_regions": _dedupe_regions(auto_regions),
    }


def analyze_qimage(qimage: QImage) -> dict:
    return analyze_cv_image(qimage_to_cv_image(qimage))


def analyze_image(pixmap: QPixmap) -> dict:
    return analyze_cv_image(qpixmap_to_cv_image(pixmap))


def render_image(cv_image, regions: list[tuple[int, int, int, int]]) -> QPixmap:
    return cv_image_to_qpixmap(apply_blur_regions(cv_image, regions))


def save_clean(cv_image, regions: list[tuple[int, int, int, int]], file_path: str) -> bool:
    result = apply_blur_regions(cv_image, regions)
    if file_path.lower().endswith(('.jpg', '.jpeg')):
        return cv2.imwrite(file_path, result, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return cv2.imwrite(file_path, result)
