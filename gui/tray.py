from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction
from PyQt6.QtCore import QSize, QThread, QTimer
from gui.analysis import ImageAnalysisWorker, ProcessingDialog
from gui.errors import safe_slot, show_exception
from gui.onboarding import OnboardingDialog, mark_onboarding_seen, should_show_onboarding
from gui.permissions import MacOSPermissionsDialog, should_show_macos_permissions_preflight
from gui.preview import PreviewWindow
from gui.snipper import SnippingWidget
from gui.hotkey import HotkeyHandler, DEFAULT_HOTKEY, format_hotkey_for_display
from platforms.screen_capture import grab_virtual_desktop
from pathlib import Path
import platform
import sys


def _resource_path(relative_path: str) -> Path:
    base_path = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base_path / relative_path


def app_icon() -> QIcon:
    icon = QIcon(str(_resource_path("assets/icons/blurveil.ico")))
    if not icon.isNull():
        return icon

    icon = QIcon(str(_resource_path("assets/icons/blurveil-icon-1024.png")))
    if not icon.isNull():
        return icon

    return QIcon.fromTheme("edit-cut")


def tray_icon() -> QIcon:
    if platform.system() == "Darwin":
        icon = QIcon()
        for size in (16, 18, 20, 24, 32, 36, 48, 64, 128, 256, 512, 1024):
            path = _resource_path(f"assets/icons/tray/blurveil-tray-template-{size}.png")
            if path.exists():
                icon.addFile(str(path), QSize(size, size))
        if not icon.isNull():
            icon.setIsMask(True)
            return icon

    return app_icon()


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
        self._analysis_active = False
        self._analysis_thread = None
        self._analysis_worker = None
        self._processing_dialog = None
        self._permissions_dialog = None
        self._onboarding_dialog = None
        self._previews: list = []
        self._hotkey_start_error = None

        self.hotkey_handler = HotkeyHandler(DEFAULT_HOTKEY)
        self.hotkey_handler.activated.connect(self.start_snipping)
        try:
            self.hotkey_handler.start()
        except Exception as exc:
            self._hotkey_start_error = exc

        self.tray_icon = QSystemTrayIcon(tray_icon(), self.app)
        self.tray_icon.setToolTip(f"Blurveil ({format_hotkey_for_display(self.hotkey_handler.hotkey)})")

        menu = QMenu()
        self.action_snip = QAction("Сделать скриншот", self.app)
        self.action_snip.triggered.connect(self.start_snipping)
        menu.addAction(self.action_snip)

        self.action_fullscreen = QAction("Скрин всего экрана", self.app)
        self.action_fullscreen.triggered.connect(self.capture_fullscreen)
        menu.addAction(self.action_fullscreen)

        menu.addSeparator()

        action_onboarding = QAction("Как пользоваться", self.app)
        action_onboarding.triggered.connect(lambda: self._show_onboarding(force=True))
        menu.addAction(action_onboarding)

        if platform.system() == "Darwin":
            action_permissions = QAction("Проверить разрешения macOS", self.app)
            action_permissions.triggered.connect(lambda: self._show_permissions_dialog(force=True))
            menu.addAction(action_permissions)

        menu.addSeparator()

        action_quit = QAction("Выход", self.app)
        action_quit.triggered.connect(self.quit_app)
        menu.addAction(action_quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.show()

        if should_show_onboarding():
            QTimer.singleShot(0, self._show_onboarding_on_first_launch)
        elif platform.system() == "Darwin":
            QTimer.singleShot(0, self._show_permissions_preflight)
        if self._hotkey_start_error is not None:
            QTimer.singleShot(0, self._show_hotkey_start_error)

    @safe_slot("Не удалось начать выделение области")
    def start_snipping(self, *_args):
        if self._analysis_active:
            self._focus_processing_dialog()
            return

        if self._snipping_active:
            self._focus_existing_snipper()
            return

        self._snipping_active = True
        self._set_capture_actions_enabled(False)

        try:
            _macos_activate()
            self.snipper = SnippingWidget()
            self.snipper.capture_ready.connect(self._start_analysis)
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
        if not self._analysis_active:
            self._set_capture_actions_enabled(True)

    @safe_slot("Не удалось сделать скрин всего экрана")
    def capture_fullscreen(self, *_args):
        if self._analysis_active:
            self._focus_processing_dialog()
            return

        if self._snipping_active:
            self._focus_existing_snipper()
            return

        self._set_capture_actions_enabled(False)
        try:
            capture = grab_virtual_desktop()
            self._start_analysis(capture.pixmap)
        except Exception:
            self._set_capture_actions_enabled(True)
            raise

    def _start_analysis(self, pixmap):
        if self._analysis_active:
            self._focus_processing_dialog()
            return

        self._analysis_active = True
        self._set_capture_actions_enabled(False)
        self._show_processing_dialog()

        try:
            image = pixmap.toImage().copy()
            thread = QThread(self.app)
            worker = ImageAnalysisWorker(image)
            worker.moveToThread(thread)

            self._analysis_thread = thread
            self._analysis_worker = worker

            thread.started.connect(worker.run)
            worker.finished.connect(self._on_analysis_finished)
            worker.failed.connect(self._on_analysis_failed)
            worker.finished.connect(thread.quit)
            worker.failed.connect(thread.quit)
            thread.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            thread.finished.connect(self._cleanup_analysis)
            thread.start()
        except Exception:
            self._cleanup_analysis()
            raise

    def _show_processing_dialog(self):
        self._processing_dialog = ProcessingDialog()
        self._processing_dialog.show()
        self._processing_dialog.activateWindow()
        self._processing_dialog.raise_()

    def _focus_processing_dialog(self):
        if self._processing_dialog is None:
            return
        self._processing_dialog.show()
        self._processing_dialog.activateWindow()
        self._processing_dialog.raise_()

    def _close_processing_dialog(self):
        if self._processing_dialog is not None:
            self._processing_dialog.close()
            self._processing_dialog = None

    def _on_analysis_finished(self, result: dict):
        self._close_processing_dialog()
        self._open_preview(result)

    def _on_analysis_failed(self, exc: Exception):
        self._close_processing_dialog()
        show_exception("Не удалось обработать скриншот", exc, tray_icon=self.tray_icon)

    def _cleanup_analysis(self):
        self._close_processing_dialog()
        self._analysis_thread = None
        self._analysis_worker = None
        self._analysis_active = False
        if not self._snipping_active:
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

    def _show_permissions_preflight(self):
        self._show_permissions_dialog(force=False)

    def _show_onboarding_on_first_launch(self):
        if not should_show_onboarding():
            if platform.system() == "Darwin":
                self._show_permissions_preflight()
            return
        self._show_onboarding(force=False)

    def _show_onboarding(self, force: bool):
        if not force and not should_show_onboarding():
            return
        if self._onboarding_dialog is not None and self._onboarding_dialog.isVisible():
            _macos_activate()
            self._onboarding_dialog.activateWindow()
            self._onboarding_dialog.raise_()
            return

        dialog = OnboardingDialog(format_hotkey_for_display(self.hotkey_handler.hotkey))
        self._onboarding_dialog = dialog
        dialog.start_requested.connect(self.start_snipping)
        dialog.finished.connect(lambda: self._on_onboarding_finished(dialog, force))

        _macos_activate()
        dialog.show()
        dialog.activateWindow()
        dialog.raise_()

        if not force:
            mark_onboarding_seen()

    def _on_onboarding_finished(self, dialog, force: bool):
        if self._onboarding_dialog is dialog:
            self._onboarding_dialog = None
        if not force and platform.system() == "Darwin":
            QTimer.singleShot(0, self._show_permissions_preflight)

    def _show_permissions_dialog(self, force: bool):
        if platform.system() != "Darwin":
            return
        if not force and not should_show_macos_permissions_preflight():
            return
        if self._permissions_dialog is not None and self._permissions_dialog.isVisible():
            self._permissions_dialog.activateWindow()
            self._permissions_dialog.raise_()
            return

        self._permissions_dialog = MacOSPermissionsDialog()
        self._permissions_dialog.finished.connect(lambda: setattr(self, "_permissions_dialog", None))
        self._permissions_dialog.show()
        self._permissions_dialog.activateWindow()
        self._permissions_dialog.raise_()

    def _show_hotkey_start_error(self):
        show_exception(
            "Не удалось запустить глобальную горячую клавишу",
            self._hotkey_start_error,
            tray_icon=self.tray_icon,
        )
        self._show_permissions_dialog(force=True)

    def quit_app(self):
        self.hotkey_handler.stop()
        self.tray_icon.hide()
        self.app.quit()
