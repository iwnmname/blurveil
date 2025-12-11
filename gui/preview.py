from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QApplication
from PyQt6.QtCore import Qt

class PreviewWindow(QWidget):
    def __init__(self, pixmap):
        super().__init__()
        self.setWindowTitle("Blurveil Preview")
        self.setGeometry(100, 100, 600, 400)
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