import unittest
from unittest.mock import patch

from PyQt6.QtGui import QImage

from gui.analysis import ImageAnalysisWorker


class ImageAnalysisWorkerTests(unittest.TestCase):
    def test_worker_emits_finished_result(self):
        image = QImage(2, 2, QImage.Format.Format_RGB888)
        result = {"cv_image": object(), "ocr_boxes": [], "auto_regions": []}
        emitted = []

        with patch("gui.analysis.analyze_qimage", return_value=result):
            worker = ImageAnalysisWorker(image)
            worker.finished.connect(emitted.append)
            worker.run()

        self.assertEqual([result], emitted)

    def test_worker_emits_failure(self):
        image = QImage(2, 2, QImage.Format.Format_RGB888)
        error = RuntimeError("ocr failed")
        emitted = []

        with patch("gui.analysis.analyze_qimage", side_effect=error):
            worker = ImageAnalysisWorker(image)
            worker.failed.connect(emitted.append)
            worker.run()

        self.assertEqual([error], emitted)


if __name__ == "__main__":
    unittest.main()
