from PyQt6.QtCore import QSettings, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


ONBOARDING_SEEN_KEY = "onboarding/seen_v1"


def _settings() -> QSettings:
    return QSettings("Blurveil", "Blurveil")


def should_show_onboarding(settings: QSettings | None = None) -> bool:
    settings = settings or _settings()
    return not settings.value(ONBOARDING_SEEN_KEY, False, type=bool)


def mark_onboarding_seen(settings: QSettings | None = None):
    settings = settings or _settings()
    settings.setValue(ONBOARDING_SEEN_KEY, True)
    settings.sync()


class OnboardingDialog(QDialog):
    start_requested = pyqtSignal()

    def __init__(self, hotkey_label: str):
        super().__init__()
        self.setWindowTitle("Добро пожаловать в Blurveil")
        self.setModal(False)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        title = QLabel("Blurveil готовит безопасные скриншоты")
        title_font = title.font()
        title_font.setPointSize(title_font.pointSize() + 3)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        intro = QLabel(
            "Приложение живет в системном трее и работает локально: скриншоты не отправляются наружу."
        )
        intro.setWordWrap(True)
        main_layout.addWidget(intro)

        steps = QLabel(
            f"1. Нажмите {hotkey_label} или выберите действие в меню трея.\n"
            "2. Выделите область экрана или сделайте скрин всего экрана.\n"
            "3. Проверьте предпросмотр: можно отключить авто-блюр, добавить блюр вручную, обрезать, скопировать или сохранить результат."
        )
        steps.setWordWrap(True)
        main_layout.addWidget(steps)

        note = QLabel(
            "Blurveil ищет чувствительные данные, QR-коды и лица, но перед публикацией все равно стоит быстро проверить предпросмотр."
        )
        note.setWordWrap(True)
        main_layout.addWidget(note)

        actions = QHBoxLayout()
        actions.addStretch(1)

        start_button = QPushButton("Сделать скриншот")
        start_button.clicked.connect(self._request_start)
        actions.addWidget(start_button)

        close_button = QPushButton("Понятно")
        close_button.clicked.connect(self.accept)
        actions.addWidget(close_button)
        main_layout.addLayout(actions)

        self.setLayout(main_layout)
        self.resize(560, self.sizeHint().height())

    def _request_start(self):
        self.accept()
        self.start_requested.emit()
