import logging
import traceback
from functools import wraps

from PyQt6.QtWidgets import QMessageBox, QWidget


logger = logging.getLogger(__name__)


def show_exception(title: str, exc: Exception, parent=None, tray_icon=None):
    logger.exception(title, exc_info=(type(exc), exc, exc.__traceback__))
    traceback.print_exception(type(exc), exc, exc.__traceback__)

    if tray_icon is not None:
        try:
            tray_icon.showMessage("Blurveil", str(exc))
        except Exception:
            logger.exception("Failed to show tray error message")

    try:
        QMessageBox.critical(
            parent if isinstance(parent, QWidget) else None,
            title,
            f"{exc}\n\nПодробности напечатаны в консоль.",
        )
    except Exception:
        logger.exception("Failed to show error dialog")


def safe_slot(title: str):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                owner = args[0] if args else None
                parent = owner if isinstance(owner, QWidget) else None
                tray_icon = getattr(owner, "tray_icon", None)
                show_exception(title, exc, parent=parent, tray_icon=tray_icon)
                return None

        return wrapper

    return decorator
