from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QAction
from PyQt6.QtCore import Qt
from core.sanitizer import analyze_image
from gui.errors import safe_slot
from gui.preview import PreviewWindow
from gui.snipper import SnippingWidget
from gui.hotkey import HotkeyHandler, DEFAULT_HOTKEY, format_hotkey_for_display
from platforms.screen_capture import grab_virtual_desktop
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

        self.hotkey_handler = HotkeyHandler(DEFAULT_HOTKEY)
        self.hotkey_handler.activated.connect(self.start_snipping)
        self.hotkey_handler.start()

        if not QIcon.hasThemeIcon("edit-cut"):
            pixmap = QPixmap(16, 16)
            pixmap.fill(Qt.GlobalColor.green)
            icon = QIcon(pixmap)
        else:
            icon = QIcon.fromTheme("edit-cut")

        self.tray_icon = QSystemTrayIcon(icon, self.app)
        self.tray_icon.setToolTip(f"Blurveil ({format_hotkey_for_display(self.hotkey_handler.hotkey)})")

        menu = QMenu()
        self.action_snip = QAction("Сделать скриншот", self.app)
        self.action_snip.triggered.connect(self.start_snipping)
        menu.addAction(self.action_snip)

        self.action_fullscreen = QAction("Скрин всего экрана", self.app)
        self.action_fullscreen.triggered.connect(self.capture_fullscreen)
        menu.addAction(self.action_fullscreen)

        action_quit = QAction("Выход", self.app)
        action_quit.triggered.connect(self.quit_app)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

    @safe_slot("Не удалось начать выделение области")
    def start_snipping(self, *_args):
        if self._snipping_active:
            self._close_existing_snipper()

        self._snipping_active = True
        self._set_capture_actions_enabled(False)

        try:
            _macos_activate()
            self.snipper = SnippingWidget()
            self.snipper.preview_ready.connect(self._on_preview_ready)
            self.snipper.destroyed.connect(
                lambda *_args, snipper=self.snipper: self._on_snipper_destroyed(snipper)
            )
            self.snipper.activateWindow()
        except Exception:
            self._on_snipper_destroyed()
            raise

    def _close_existing_snipper(self):
        try:
            if self.snipper is not None:
                snipper = self.snipper
                self.snipper.close()
                QApplication.processEvents()
                if self.snipper is snipper:
                    self._on_snipper_destroyed(snipper)
        except RuntimeError:
            pass

    def _on_snipper_destroyed(self, snipper=None):
        if snipper is not None and snipper is not self.snipper:
            return
        self.snipper = None
        self._snipping_active = False
        self._set_capture_actions_enabled(True)

    @safe_slot("Не удалось сделать скрин всего экрана")
    def capture_fullscreen(self, *_args):
        if self._snipping_active:
            self._close_existing_snipper()

        self._set_capture_actions_enabled(False)
        try:
            capture = grab_virtual_desktop()
            result = analyze_image(capture.pixmap)
            self._open_preview(result)
        finally:
            self._set_capture_actions_enabled(True)

    def _on_preview_ready(self, preview):
        self._previews.append(preview)
        preview.destroyed.connect(lambda: self._previews.remove(preview) if preview in self._previews else None)

    def _open_preview(self, result: dict):
        preview = PreviewWindow(result["cv_image"], result["ocr_boxes"], result["auto_regions"])
        _macos_activate()
        preview.show()
        preview.activateWindow()
        preview.raise_()
        self._on_preview_ready(preview)

    def _set_capture_actions_enabled(self, enabled: bool):
        self.action_snip.setEnabled(enabled)
        self.action_fullscreen.setEnabled(enabled)

    def quit_app(self):
        self.hotkey_handler.stop()
        self.tray_icon.hide()
        self.app.quit()
