from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtCore import Qt
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
        action_snip = QAction("Сделать скриншот", self.app)
        action_snip.triggered.connect(self.start_snipping)
        menu.addAction(action_snip)

        action_quit = QAction("Выход", self.app)
        action_quit.triggered.connect(self.quit_app)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    def start_snipping(self):
        if self.snipper is not None:
            try:
                self.snipper.close()
            except RuntimeError:
                pass
            self.snipper = None

        _macos_activate()
        self.snipper = SnippingWidget()
        self.snipper.preview_ready.connect(self._on_preview_ready)
        self.snipper.show()
        self.snipper.activateWindow()

    def _on_preview_ready(self, preview):
        self._previews.append(preview)
        preview.destroyed.connect(lambda: self._previews.remove(preview) if preview in self._previews else None)

    def quit_app(self):
        self.hotkey_handler.stop()
        self.tray_icon.hide()
        self.app.quit()