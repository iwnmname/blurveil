import platform
import sys


SUPPORTED_SYSTEMS = {"Darwin", "Windows"}


def _is_supported_platform() -> bool:
    return platform.system() in SUPPORTED_SYSTEMS


def main():
    if not _is_supported_platform():
        print(
            "Blurveil сейчас поддерживает только macOS и Windows. Linux/Ubuntu не поддерживается.",
            file=sys.stderr,
        )
        return 1

    from PyQt6.QtWidgets import QApplication
    from gui.tray import BlurveilTrayApp, app_icon

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(app_icon())

    tray = BlurveilTrayApp(app)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
