import sys
from adbutils import adb
from taskManager import TaskManagerGUI
from PyQt6.QtWidgets import QApplication

adb_device = adb.device()


def TaskCreator():
    app = QApplication(sys.argv)
    window = TaskManagerGUI(adb_device)
    window.show()
    sys.exit(app.exec())

if __name__=="__main__":
    TaskCreator()
