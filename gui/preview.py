from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication, QFileDialog
from PyQt6.QtCore import Qt

class PreviewWindow(QWidget):
    def __init__(self, pixmap):
        super().__init__()
        self.setWindowTitle("Blurveil Preview")
        self.setGeometry(100, 100, 600, 400)
        
        main_layout = QVBoxLayout()
        
        self.label = QLabel()
        self.label.setPixmap(pixmap)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.label)
        
        buttons_layout = QHBoxLayout()
        
        btn_copy = QPushButton("Скопировать в буфер")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        buttons_layout.addWidget(btn_copy)
        
        btn_save = QPushButton("Сохранить как...")
        btn_save.clicked.connect(self.save_to_file)
        buttons_layout.addWidget(btn_save)
        
        main_layout.addLayout(buttons_layout)
        
        self.setLayout(main_layout)
        self.pixmap = pixmap

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(self.pixmap)
        self.close()

    def save_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Сохранить изображение", 
            "", 
            "PNG Images (*.png);;JPEG Images (*.jpg)"
        )
        
        if file_path:
            self.pixmap.save(file_path)
            self.close()