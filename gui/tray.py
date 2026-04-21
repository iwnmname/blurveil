from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtCore import Qt
from gui.errors import safe_slot
from gui.snipper import SnippingWidget
from gui.hotkey import HotkeyHandler
import platform


def _macos_activate():
    if platform.system() == "Darwin":
        try:
            from AppKit import NSApplication
            NSApplication.sharedApplication().activateIgnoringOtherApps_(True)
        except Exception:
            pass


class BlurveilTrayApp:
    def __init__(self, app):
        self.app = app
        self.snipper = None
        self._snipping_active = False
        self._previews: list = []

        self.hotkey_handler = HotkeyHandler("<ctrl>+<shift>+s")
        self.hotkey_handler.activated.connect(self.start_snipping)
        self.hotkey_handler.start()

        if not QIcon.hasThemeIcon("edit-cut"):
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.green)
            icon = QIcon(pixmap)
        else:
            icon = QIcon.fromTheme("edit-cut")

        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip(f"Blurveil ({self.hotkey_handler.hotkey})")

        menu = QMenu()
        self.action_snip = QAction("Сделать скриншот", self.app)
        self.action_snip.triggered.connect(self.start_snipping)
        menu.addAction(self.action_snip)

        action_quit = QAction("Выход", self.app)
        action_quit.triggered.connect(self.quit_app)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    @safe_slot("Не удалось начать выделение области")
    def start_snipping(self, *_args):
        if self._snipping_active:
            self._focus_existing_snipper()
            return

        self._snipping_active = True
        self.action_snip.setEnabled(False)

        try:
            _macos_activate()
            self.snipper = SnippingWidget()
            self.snipper.preview_ready.connect(self._on_preview_ready)
            self.snipper.destroyed.connect(self._on_snipper_destroyed)
            self.snipper.activateWindow()
        except Exception:
            self._on_snipper_destroyed()
            raise

    def _focus_existing_snipper(self):
        try:
            if self.snipper is not None and self.snipper.isVisible():
                _macos_activate()
                self.snipper.raise_()
                self.snipper.activateWindow()
        except RuntimeError:
            self._on_snipper_destroyed()

    def _on_snipper_destroyed(self, *_args):
        self.snipper = None
        self._snipping_active = False
        self.action_snip.setEnabled(True)

    def _on_preview_ready(self, preview):
        self._previews.append(preview)
        preview.destroyed.connect(lambda: self._previews.remove(preview) if preview in self._previews else None)

    def quit_app(self):
        self.hotkey_handler.stop()
        self.tray_icon.hide()
        self.app.quit()
