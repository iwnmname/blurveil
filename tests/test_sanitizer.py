import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory
import os

import numpy as np
from PyQt6.QtGui import QColor, QImage

from core import sanitizer


class SensitivePatternTests(unittest.TestCase):
    def test_detects_common_sensitive_values(self):
        samples = [
            "admin@example.com",
            "192.168.1.20",
            "2001:0db8:85a3:0000:0000:8a2e:0370:7334",
            "+1 (415) 555-2671",
            "4111 1111 1111 1111",
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.abcdefghijklmnopqrstuvwxyz.abcdefghijklmnopqrstuvwxyz",
            "AKIAIOSFODNN7EXAMPLE",
            "ghp_abcdefghijklmnopqrstuvwxyzABCDE12345",
            "xox" + "b-" + "123456789012-" + "abcdefghijklmnopqrstuvwxyz",
            "-----BEGIN PRIVATE KEY-----",
            "GB82WEST12345698765432",
        ]

        for sample in samples:
            with self.subTest(sample=sample):
                self.assertTrue(sanitizer._matches_direct_sensitive_value(sample))

    def test_rejects_common_false_positives(self):
        samples = [
            "999.999.999.999",
            "version 1.2.3",
            "order number 123456789",
            "short phone 123-456",
            "not a luhn card 4111 1111 1111 1112",
        ]

        for sample in samples:
            with self.subTest(sample=sample):
                self.assertFalse(sanitizer._matches_direct_sensitive_value(sample))

    def test_luhn_validation(self):
        self.assertTrue(sanitizer._looks_like_luhn_number("4111 1111 1111 1111"))
        self.assertFalse(sanitizer._looks_like_luhn_number("4111 1111 1111 1112"))


class RegionHelpersTests(unittest.TestCase):
    def test_line_grouping_orders_words(self):
        entries = [
            {"text": "value", "rect": (40, 20, 10, 5), "block_num": 1, "par_num": 1, "line_num": 1},
            {"text": "token:", "rect": (10, 20, 20, 5), "block_num": 1, "par_num": 1, "line_num": 1},
            {"text": "other", "rect": (10, 40, 20, 5), "block_num": 1, "par_num": 1, "line_num": 2},
        ]

        lines = sanitizer._line_groups(entries)

        self.assertEqual(["token:", "value"], [word["text"] for word in lines[0]])
        self.assertEqual(["other"], [word["text"] for word in lines[1]])

    def test_sensitive_line_blurs_keyword_tail(self):
        words = [
            {"text": "User", "rect": (0, 0, 10, 5)},
            {"text": "password:", "rect": (20, 0, 30, 5)},
            {"text": "secret-value", "rect": (60, 0, 50, 5)},
        ]

        self.assertEqual((20, 0, 90, 5), sanitizer._sensitive_line_region(words))

    def test_dedupes_regions_preserving_order(self):
        regions = [(1, 2, 3, 4), (5, 6, 7, 8), (1, 2, 3, 4)]

        self.assertEqual([(1, 2, 3, 4), (5, 6, 7, 8)], sanitizer._dedupe_regions(regions))


class ImageConversionTests(unittest.TestCase):
    def test_qimage_to_cv_image_preserves_dimensions_and_color_channels(self):
        image = QImage(2, 1, QImage.Format.Format_RGB888)
        image.setPixelColor(0, 0, QColor(255, 0, 0))
        image.setPixelColor(1, 0, QColor(0, 255, 0))

        cv_image = sanitizer.qimage_to_cv_image(image)

        self.assertEqual((1, 2, 3), cv_image.shape)
        self.assertEqual([0, 0, 255], cv_image[0, 0].tolist())
        self.assertEqual([0, 255, 0], cv_image[0, 1].tolist())

    def test_apply_blur_regions_does_not_mutate_original_image(self):
        image = np.zeros((80, 80, 3), dtype=np.uint8)
        image[20:60, 20:60] = 255

        blurred = sanitizer.apply_blur_regions(image, [(10, 10, 60, 60)])

        self.assertFalse(np.shares_memory(image, blurred))
        self.assertTrue(np.array_equal(image[20:60, 20:60], np.full((40, 40, 3), 255, dtype=np.uint8)))

    def test_analyze_cv_image_filters_low_confidence_and_marks_sensitive_lines(self):
        fake_ocr = {
            "text": ["password:", "secret-value", "noise"],
            "conf": ["95", "95", "5"],
            "left": [10, 80, 10],
            "top": [20, 20, 60],
            "width": [60, 90, 30],
            "height": [10, 10, 10],
            "block_num": [1, 1, 1],
            "par_num": [1, 1, 1],
            "line_num": [1, 1, 2],
        }
        image = np.zeros((100, 220, 3), dtype=np.uint8)

        with patch.object(sanitizer.pytesseract, "image_to_data", return_value=fake_ocr):
            with patch.object(sanitizer, "detect_qr_codes", return_value=[]):
                result = sanitizer.analyze_cv_image(image)

        self.assertEqual(["password:", "secret-value"], [box["text"] for box in result["ocr_boxes"]])
        self.assertIn((6, 16, 168, 18), result["auto_regions"])


class RuntimeTesseractTests(unittest.TestCase):
    def test_configures_bundled_tesseract_when_frozen(self):
        original_cmd = sanitizer.pytesseract.pytesseract.tesseract_cmd
        original_tessdata = os.environ.get("TESSDATA_PREFIX")

        try:
            with TemporaryDirectory() as tmpdir:
                bundle_dir = Path(tmpdir)
                tesseract_path = bundle_dir / "tesseract"
                tessdata_path = bundle_dir / "tessdata"
                tesseract_path.write_text("", encoding="utf-8")
                tessdata_path.mkdir()

                with patch.object(sanitizer.sys, "frozen", True, create=True):
                    with patch.object(sanitizer.sys, "_MEIPASS", str(bundle_dir), create=True):
                        with patch.object(sanitizer.sys, "platform", "darwin"):
                            sanitizer._configure_bundled_tesseract()

                self.assertEqual(str(tesseract_path), sanitizer.pytesseract.pytesseract.tesseract_cmd)
                self.assertEqual(str(tessdata_path), os.environ.get("TESSDATA_PREFIX"))
        finally:
            sanitizer.pytesseract.pytesseract.tesseract_cmd = original_cmd
            if original_tessdata is None:
                os.environ.pop("TESSDATA_PREFIX", None)
            else:
                os.environ["TESSDATA_PREFIX"] = original_tessdata


if __name__ == "__main__":
    unittest.main()
