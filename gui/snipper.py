import mss
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPixmap, QPainter, QColor, QImage

from core.sanitizer import blur_sensitive_data
from gui.preview import PreviewWindow

class SnippingWidget(QWidget):
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
        
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            sct_img = sct.grab(monitor)
            img = QImage(sct_img.bgra, sct_img.width, sct_img.height, QImage.Format.Format_ARGB32).copy()
            self.original_pixmap = QPixmap.fromImage(img)

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
        
        processed_pixmap = blur_sensitive_data(cropped)
        self.open_preview(processed_pixmap)
        
        self.close()

    def open_preview(self, pixmap):
        self.preview = PreviewWindow(pixmap)
        self.preview.show()