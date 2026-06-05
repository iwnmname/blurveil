from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from platforms.macos_permissions import (
    get_macos_permission_statuses,
    has_missing_macos_permissions,
    is_macos,
    request_macos_permission_prompts,
)


def should_show_macos_permissions_preflight() -> bool:
    return is_macos() and has_missing_macos_permissions()


class MacOSPermissionsDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Разрешения macOS для Blurveil")
        self._status_labels: dict[str, QLabel] = {}

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(18, 16, 18, 16)
        main_layout.setSpacing(12)

        intro = QLabel(
            "Для скриншотов и глобальных горячих клавиш Blurveil нужны разрешения macOS."
        )
        intro.setWordWrap(True)
        main_layout.addWidget(intro)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        main_layout.addLayout(grid)

        for row, status in enumerate(get_macos_permission_statuses()):
            title = QLabel(status.title)
            title.setMinimumWidth(150)
            grid.addWidget(title, row, 0, alignment=Qt.AlignmentFlag.AlignTop)

            status_label = QLabel()
            self._status_labels[status.key] = status_label
            grid.addWidget(status_label, row, 1, alignment=Qt.AlignmentFlag.AlignTop)

            description = QLabel(status.description)
            description.setWordWrap(True)
            grid.addWidget(description, row, 2)

            button = QPushButton("Открыть")
            button.clicked.connect(lambda _checked=False, url=status.settings_url: self._open_settings(url))
            grid.addWidget(button, row, 3, alignment=Qt.AlignmentFlag.AlignTop)

        actions = QHBoxLayout()
        request_button = QPushButton("Запросить системный доступ")
        request_button.clicked.connect(self._request_access)
        actions.addWidget(request_button)

        refresh_button = QPushButton("Проверить снова")
        refresh_button.clicked.connect(self._refresh_statuses)
        actions.addWidget(refresh_button)

        close_button = QPushButton("Закрыть")
        close_button.clicked.connect(self.close)
        actions.addWidget(close_button)
        main_layout.addLayout(actions)

        hint = QLabel(
            "После изменения разрешений macOS может попросить перезапустить приложение."
        )
        hint.setWordWrap(True)
        main_layout.addWidget(hint)

        self.setLayout(main_layout)
        self.resize(760, self.sizeHint().height())
        self._refresh_statuses()

    def _refresh_statuses(self):
        for status in get_macos_permission_statuses():
            label = self._status_labels.get(status.key)
            if label is None:
                continue
            label.setText(self._status_text(status.granted))

    def _request_access(self):
        request_macos_permission_prompts()
        self._refresh_statuses()

    def _open_settings(self, url: str):
        QDesktopServices.openUrl(QUrl(url))

    def _status_text(self, granted: bool | None) -> str:
        if granted is True:
            return "Разрешено"
        if granted is False:
            return "Не разрешено"
        return "Проверьте вручную"
