import sys
import threading
from PyQt5.QtWidgets import QApplication
from ui import ImageAnnotationApp
from flask_app import app

def run_flask():
    app.run(port=5000)

def main():
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Start the PyQt application
    qt_app = QApplication(sys.argv)
    window = ImageAnnotationApp()
    window.show()
    sys.exit(qt_app.exec())

if __name__ == '__main__':
    main()