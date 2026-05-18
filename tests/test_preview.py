import unittest

import numpy as np
from PyQt6.QtWidgets import QApplication

from gui.preview import ImageCanvas, PreviewWindow


_APP = None


def _app():
    global _APP
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    _APP = app
    return app


class PreviewModeTests(unittest.TestCase):
    def setUp(self):
        _app()
        self.canvas = ImageCanvas(np.zeros((80, 100, 3), dtype=np.uint8), [], [])

    def test_switching_mode_clears_active_drag_state(self):
        self.canvas._drag_start = object()
        self.canvas._drag_current = object()
        self.canvas._is_dragging = True

        self.canvas.set_mode("crop")

        self.assertEqual("crop", self.canvas._mode)
        self.assertIsNone(self.canvas._drag_start)
        self.assertIsNone(self.canvas._drag_current)
        self.assertFalse(self.canvas._is_dragging)

    def test_crop_reset_is_undoable_and_redoable(self):
        self.canvas.set_mode("crop")
        self.canvas._crop_rect = (10, 10, 40, 40)

        self.canvas.reset_crop()

        self.assertEqual((0, 0, 100, 80), self.canvas._crop_rect)
        self.canvas.undo()
        self.assertEqual((10, 10, 40, 40), self.canvas._crop_rect)
        self.canvas.redo()
        self.assertEqual((0, 0, 100, 80), self.canvas._crop_rect)

    def test_region_change_is_undoable_and_redoable(self):
        region = {"rect": (1, 2, 3, 4), "active": True, "auto": False}

        self.canvas._push_blur_history()
        self.canvas._regions.append(region)

        self.canvas.undo()
        self.assertEqual([], self.canvas._regions)
        self.canvas.redo()
        self.assertEqual([region], self.canvas._regions)

    def test_undo_redo_history_is_separate_per_mode(self):
        region = {"rect": (1, 2, 3, 4), "active": True, "auto": False}
        self.canvas._push_blur_history()
        self.canvas._regions.append(region)
        self.canvas.set_mode("crop")
        self.canvas._crop_rect = (10, 10, 40, 40)
        self.canvas.reset_crop()

        self.canvas.undo()
        self.assertEqual([region], self.canvas._regions)
        self.assertEqual((10, 10, 40, 40), self.canvas._crop_rect)

        self.canvas.set_mode("blur")
        self.canvas.undo()
        self.assertEqual([], self.canvas._regions)
        self.assertEqual((10, 10, 40, 40), self.canvas._crop_rect)

    def test_preview_buttons_switch_modes_and_follow_history_state(self):
        preview = PreviewWindow(np.zeros((80, 100, 3), dtype=np.uint8), [], [])

        self.assertEqual("blur", preview.canvas._mode)
        self.assertFalse(preview.btn_undo.isEnabled())
        self.assertFalse(preview.btn_redo.isEnabled())

        preview.btn_crop_mode.click()
        self.assertEqual("crop", preview.canvas._mode)

        preview.canvas._crop_rect = (10, 10, 40, 40)
        preview.canvas.reset_crop()
        self.assertTrue(preview.btn_undo.isEnabled())

        preview.btn_undo.click()
        self.assertTrue(preview.btn_redo.isEnabled())

        preview.btn_blur_mode.click()
        self.assertFalse(preview.btn_undo.isEnabled())
        self.assertFalse(preview.btn_redo.isEnabled())


if __name__ == "__main__":
    unittest.main()
