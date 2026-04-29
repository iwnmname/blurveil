from dataclasses import dataclass
import platform

import mss
import numpy as np
from PyQt6.QtWidgets import QApplication
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
    if platform.system() == "Darwin":
        qt_capture = _grab_macos_retina_screen()
        if qt_capture is not None:
            return qt_capture

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


def _grab_macos_retina_screen() -> ScreenCapture | None:
    app = QApplication.instance()
    if app is None:
        return None

    screens = QApplication.screens()
    if len(screens) != 1:
        return None

    screen = screens[0]
    geometry = screen.geometry()
    pixmap = screen.grabWindow(0)
    dpr = pixmap.devicePixelRatio()

    return ScreenCapture(
        pixmap=pixmap,
        left=int(geometry.x() * dpr),
        top=int(geometry.y() * dpr),
        width=pixmap.width(),
        height=pixmap.height(),
    )
