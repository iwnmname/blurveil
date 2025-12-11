import sys
from PyQt6.QtWidgets import QApplication
from gui.tray import BlurveilTrayApp

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    tray = BlurveilTrayApp(app)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()