from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout

from core.sanitizer import analyze_qimage


class ImageAnalysisWorker(QObject):
    finished = pyqtSignal(dict)
    failed = pyqtSignal(object)

    def __init__(self, image: QImage):
        super().__init__()
        self.image = image

    @pyqtSlot()
    def run(self):
        try:
            self.finished.emit(analyze_qimage(self.image))
        except Exception as exc:
            self.failed.emit(exc)


class ProcessingDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Blurveil")
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint
        )
        self.setModal(False)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("Обрабатываю скриншот...")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        description = QLabel("Поиск конфиденциальных данных.")
        description.setAlignment(Qt.AlignmentFlag.AlignCenter)
        description.setWordWrap(True)
        layout.addWidget(description)

        progress = QProgressBar()
        progress.setRange(0, 0)
        layout.addWidget(progress)

        self.setLayout(layout)
        self.resize(360, self.sizeHint().height())
