import sys
from PyQt5.QtWidgets import QApplication
from ui import ImageAnnotationApp


def main():
    """Launch the PyQt-based image annotation tool."""

    qt_app = QApplication(sys.argv)
    window = ImageAnnotationApp()
    window.show()
    sys.exit(qt_app.exec())

if __name__ == '__main__':
    main()
