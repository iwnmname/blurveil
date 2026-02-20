from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal
from PyQt6.QtGui import QPainter, QColor
import platform

from core.sanitizer import analyze_image
from gui.preview import PreviewWindow


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
        virtual_geometry = screen.virtualGeometry()
        self.setGeometry(virtual_geometry)

        self.original_pixmap = screen.grabWindow(0)

        self.pixel_ratio = self.original_pixmap.width() / virtual_geometry.width()
        self.original_pixmap.setDevicePixelRatio(self.pixel_ratio)

        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False

        self.show()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.original_pixmap)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100))

        if self.is_selecting:
            selection_rect = QRect(self.begin, self.end).normalized()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(selection_rect, Qt.GlobalColor.transparent)

            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QColor(255, 0, 0))
            painter.drawRect(selection_rect)

    def mousePressEvent(self, event):
        self.begin = event.pos()
        self.end = event.pos()
        self.is_selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        self.end = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        self.is_selecting = False

        rect = QRect(self.begin, self.end).normalized()

        self.hide()
        QApplication.processEvents()

        if rect.width() < 10 or rect.height() < 10:
            self.close()
            return

        x = int(rect.x() * self.pixel_ratio)
        y = int(rect.y() * self.pixel_ratio)
        w = int(rect.width() * self.pixel_ratio)
        h = int(rect.height() * self.pixel_ratio)

        cropped = self.original_pixmap.copy(x, y, w, h)
        cropped.setDevicePixelRatio(1.0)

        result = analyze_image(cropped)
        self.open_preview(result)

        self.close()

    def open_preview(self, result: dict):
        self.preview = PreviewWindow(result["cv_image"], result["ocr_boxes"], result["auto_regions"])
        _macos_activate()
        self.preview.show()
        self.preview.activateWindow()
        self.preview.raise_()
        self.preview_ready.emit(self.preview)
