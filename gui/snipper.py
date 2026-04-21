from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QRectF, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QPainterPath, QColor
import platform

from core.sanitizer import analyze_image
from gui.errors import safe_slot
from gui.preview import PreviewWindow
from platforms.screen_capture import grab_virtual_desktop


def _macos_activate():
    if platform.system() == "Darwin":
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass


class SnippingWidget(QWidget):
    preview_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setCursor(Qt.CursorShape.CrossCursor)

        screen = QApplication.primaryScreen()
        self.virtual_geometry = screen.virtualGeometry()
        self.setGeometry(self.virtual_geometry)

        self.capture = grab_virtual_desktop()
        self.original_pixmap = self.capture.pixmap

        self.pixel_ratio_x = self.capture.width / self.virtual_geometry.width()
        self.pixel_ratio_y = self.capture.height / self.virtual_geometry.height()
        self.original_pixmap.setDevicePixelRatio(self.pixel_ratio_x)

        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False

        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.original_pixmap)

        if self.is_selecting:
            selection_rect = QRect(self.begin, self.end).normalized()

            overlay = QPainterPath()
            overlay.addRect(QRectF(self.rect()))
            hole = QPainterPath()
            hole.addRect(QRectF(selection_rect))
            painter.fillPath(overlay.subtracted(hole), QColor(0, 0, 0, 100))

            painter.setPen(QColor(255, 0, 0))
            painter.drawRect(selection_rect)
        else:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.is_selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    @safe_slot("Не удалось обработать скриншот")
    def mouseReleaseEvent(self, event):
        self.is_selecting = False

        rect = QRect(self.begin, self.end).normalized()

        self.hide()
        QApplication.processEvents()

        if rect.width() < 10 or rect.height() < 10:
            self.close()
            return

        global_x = self.virtual_geometry.x() + rect.x()
        global_y = self.virtual_geometry.y() + rect.y()
        x = int(global_x * self.pixel_ratio_x - self.capture.left)
        y = int(global_y * self.pixel_ratio_y - self.capture.top)
        w = int(rect.width() * self.pixel_ratio_x)
        h = int(rect.height() * self.pixel_ratio_y)

        cropped = self.original_pixmap.copy(x, y, w, h)
        cropped.setDevicePixelRatio(1.0)

        try:
            result = analyze_image(cropped)
            self.open_preview(result)
        finally:
            self.close()

    def open_preview(self, result: dict):
        self.preview = PreviewWindow(result["cv_image"], result["ocr_boxes"], result["auto_regions"])
        _macos_activate()
        self.preview.show()
        self.preview.activateWindow()
        self.preview.raise_()
        self.preview_ready.emit(self.preview)
