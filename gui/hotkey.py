from PyQt6.QtCore import QObject, pyqtSignal
import platform
from pynput import keyboard


DEFAULT_HOTKEY = "<ctrl>+<alt>+s"


def format_hotkey_for_display(hotkey: str) -> str:
    labels = {
        "<ctrl>": "Ctrl",
        "<alt>": "Option" if platform.system() == "Darwin" else "Alt",
        "<shift>": "Shift",
        "<cmd>": "Cmd" if platform.system() == "Darwin" else "Win",
    }

    parts = hotkey.split("+")
    return "+".join(labels.get(part, part.upper()) for part in parts)


class HotkeyHandler(QObject):
    activated = pyqtSignal()
    
    def __init__(self, hotkey: str = DEFAULT_HOTKEY):
        super().__init__()
        self.hotkey = hotkey
        self._listener = None
        self._running = False
        
    def start(self):
        if self._running:
            return
        
        def on_activate():
            self.activated.emit()
        
        self._listener = keyboard.GlobalHotKeys({self.hotkey: on_activate})
        self._listener.start()
        self._running = True
    
    def stop(self):
        if not self._running:
            return
            
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._running = False
