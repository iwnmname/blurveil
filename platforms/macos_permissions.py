from dataclasses import dataclass
import platform


@dataclass(frozen=True)
class MacOSPermissionStatus:
    key: str
    title: str
    granted: bool | None
    description: str
    settings_url: str


def is_macos() -> bool:
    return platform.system() == "Darwin"


def _screen_recording_granted() -> bool | None:
    try:
        from Quartz import CGPreflightScreenCaptureAccess

        return bool(CGPreflightScreenCaptureAccess())
    except Exception:
        return None


def _accessibility_granted(prompt: bool = False) -> bool | None:
    try:
        from ApplicationServices import (
            AXIsProcessTrusted,
            AXIsProcessTrustedWithOptions,
            kAXTrustedCheckOptionPrompt,
        )

        if prompt:
            return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
        return bool(AXIsProcessTrusted())
    except Exception:
        return None


def request_macos_permission_prompts():
    if not is_macos():
        return

    try:
        from Quartz import CGRequestScreenCaptureAccess

        CGRequestScreenCaptureAccess()
    except Exception:
        pass

    _accessibility_granted(prompt=True)


def get_macos_permission_statuses() -> list[MacOSPermissionStatus]:
    if not is_macos():
        return []

    return [
        MacOSPermissionStatus(
            key="screen_recording",
            title="Запись экрана",
            granted=_screen_recording_granted(),
            description="Нужна, чтобы приложение могло захватывать изображение экрана.",
            settings_url="x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture",
        ),
        MacOSPermissionStatus(
            key="accessibility",
            title="Универсальный доступ",
            granted=_accessibility_granted(),
            description="Нужен для стабильной работы глобальных горячих клавиш.",
            settings_url="x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        ),
        MacOSPermissionStatus(
            key="input_monitoring",
            title="Мониторинг ввода",
            granted=None,
            description="macOS не дает надежно проверить этот доступ из приложения. Включите его, если hotkey не срабатывает.",
            settings_url="x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent",
        ),
    ]


def has_missing_macos_permissions() -> bool:
    return any(status.granted is False for status in get_macos_permission_statuses())
