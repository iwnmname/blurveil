from PyQt6.QtCore import QObject, pyqtSignal
import threading
from pynput import keyboard


class HotkeyHandler(QObject):
    activated = pyqtSignal()
    
    def __init__(self, hotkey: str = "<ctrl>+<shift>+s"):
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
