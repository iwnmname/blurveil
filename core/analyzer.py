from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytesseract

from core.detectors import DEFAULT_OBJECT_DETECTORS, detect_object_regions
from core.regions import Rect, dedupe_regions, pad_rect, union_rect


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


def _runtime_paths() -> list[Path]:
    paths = []
    if getattr(sys, "frozen", False):
        bundle_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        paths.extend([
            bundle_dir,
            bundle_dir / "bin",
            bundle_dir.parent / "Resources",
            Path(sys.executable).parent,
        ])
    return paths


def _configure_bundled_tesseract():
    executable_names = ["tesseract.exe"] if sys.platform.startswith("win") else ["tesseract"]
    for base_path in _runtime_paths():
        for executable_name in executable_names:
            candidate = base_path / executable_name
            if candidate.exists():
                pytesseract.pytesseract.tesseract_cmd = str(candidate)
                break
        else:
            continue
        break

    for base_path in _runtime_paths():
        tessdata_path = base_path / "tessdata"
        if tessdata_path.exists():
            os.environ.setdefault("TESSDATA_PREFIX", str(tessdata_path))
            break


_configure_bundled_tesseract()


def _confidence(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


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


def _sensitive_line_region(words: list[dict]) -> Rect | None:
    text = _line_text(words)
    if not SECRET_ASSIGNMENT_RE.search(text) and not SECRET_KEYWORD_RE.search(text):
        return None

    for index, word in enumerate(words):
        if SECRET_KEYWORD_RE.search(word["text"]):
            tail_words = words[index:]
            return union_rect([word["rect"] for word in tail_words])
    return union_rect([word["rect"] for word in words])


def analyze_cv_image(image, object_detectors=DEFAULT_OBJECT_DETECTORS) -> dict:
    data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT, config=TESS_CONFIG)

    ocr_boxes = []
    ocr_entries = []
    auto_regions = []

    for i in range(len(data['text'])):
        text = data['text'][i].strip()
        if not text or _confidence(data['conf'][i]) < OCR_MIN_CONFIDENCE:
            continue
        x, y, w, h = data['left'][i], data['top'][i], data['width'][i], data['height'][i]
        rect = pad_rect((x, y, w, h), BOX_PAD)
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
            region = union_rect([word["rect"] for word in line_words])
            if region is not None:
                auto_regions.append(region)

        region = _sensitive_line_region(line_words)
        if region is not None:
            auto_regions.append(region)

    auto_regions.extend(detect_object_regions(image, object_detectors))

    return {
        "cv_image": image,
        "ocr_boxes": ocr_boxes,
        "auto_regions": dedupe_regions(auto_regions),
    }
