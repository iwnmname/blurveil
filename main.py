import sys
import mss
import mss.tools
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSystemTrayIcon, 
                             QMenu, QWidget, QLabel, QVBoxLayout, QPushButton)
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QAction

from core import blur_sensitive_data

class SnippingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setWindowState(Qt.WindowState.WindowFullScreen)
        
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[0]
                sct_img = sct.grab(monitor)
                self.original_pixmap = QPixmap()
                self.original_pixmap.loadFromData(mss.tools.to_png(sct_img.rgb, sct_img.size))
        except Exception as e:
            print(f"Не удалось сделать скриншот (Linux Wayland?): {e}")
            screen_geo = QApplication.primaryScreen().geometry()
            self.original_pixmap = QPixmap(screen_geo.width(), screen_geo.height())
            self.original_pixmap.fill(Qt.GlobalColor.white)
            
            painter = QPainter(self.original_pixmap)
            painter.setPen(Qt.GlobalColor.black)
            font = painter.font()
            font.setPointSize(20)
            painter.setFont(font)
            
            painter.drawText(200, 100, "Тестовый режим.")
            painter.drawText(200, 150, "Моя почта: admin@blurveil.com") 
            painter.drawText(200, 200, "Секретный токен: secret_12345")
            painter.end()


        self.begin = QPoint()
        self.end = QPoint()
        self.is_selecting = False

        self.showFullScreen()

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
        self.close()
        
        rect = QRect(self.begin, self.end).normalized()
        if rect.width() < 5 or rect.height() < 5:
            return

        cropped = self.original_pixmap.copy(rect)
        
        print("Запускаю распознавание...")
        processed_pixmap = blur_sensitive_data(cropped)

        self.open_preview(processed_pixmap)

    def open_preview(self, pixmap):
        self.preview = PreviewWindow(pixmap)
        self.preview.show()

class PreviewWindow(QWidget):
    def __init__(self, pixmap):
        super().__init__()
        self.setWindowTitle("Blurveil Preview")
        self.setGeometry(100, 100, 400, 300)
        layout = QVBoxLayout()
        
        self.label = QLabel()
        self.label.setPixmap(pixmap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.label)
        
        btn_copy = QPushButton("Скопировать в буфер")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(btn_copy)
        
        self.setLayout(layout)
        self.pixmap = pixmap

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.pixmap)
        self.close()

class BlurveilApp:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)

        if not QIcon.hasThemeIcon("edit-cut"): 
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.green)
            icon = QIcon(pixmap)
        else:
            icon = QIcon.fromTheme("edit-cut")
        
        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip("Blurveil")
        
        menu = QMenu()
        action_snip = QAction("Сделать скриншот", self.app)
        action_snip.triggered.connect(self.start_snipping)
        menu.addAction(action_snip)
        
        action_quit = QAction("Выход", self.app)
        action_quit.triggered.connect(self.app.quit)
        menu.addAction(action_quit)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def start_snipping(self):
        self.snipper = SnippingWidget()
        self.snipper.show()

    def run(self):
        sys.exit(self.app.exec())

if __name__ == "__main__":
    app = BlurveilApp()
    app.run()