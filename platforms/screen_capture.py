from dataclasses import dataclass

import mss
import numpy as np
from PyQt6.QtGui import QImage, QPixmap


@dataclass(frozen=True)
class ScreenCapture:
    pixmap: QPixmap
    left: int
    top: int
    width: int
    height: int


def grab_virtual_desktop() -> ScreenCapture:
    """Capture the whole virtual desktop using mss."""
    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)

    img = np.frombuffer(screenshot.bgra, dtype=np.uint8).reshape(screenshot.height, screenshot.width, 4)
    img_rgb = np.ascontiguousarray(img[:, :, [2, 1, 0]])
    height, width = img_rgb.shape[:2]
    qimage = QImage(img_rgb.data, width, height, width * 3, QImage.Format.Format_RGB888)

    return ScreenCapture(
        pixmap=QPixmap.fromImage(qimage.copy()),
        left=int(monitor["left"]),
        top=int(monitor["top"]),
        width=int(monitor["width"]),
        height=int(monitor["height"]),
    )
