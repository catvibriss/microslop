from enum import Enum, auto

from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QApplication, QStackedWidget
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import QTimer, Qt, QSize

class AppMode(Enum):
    CLEAR = auto()
    CAMERA = auto()
    YOLO = auto()
    EDUCATION = auto()
    SETTINGS = auto()

class ModeBasic(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.yolo_enabled = False    

class ClearMode(ModeBasic):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

class YoloMode(ModeBasic):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.yolo_enabled = True
        
        self.btn_setting = QPushButton("play with me 0.0", self)
        self.btn_setting.move(20, 120)
        self.btn_setting.resize(160, 35)

MODES_CLASSES = {
    AppMode.CLEAR: ClearMode,
    AppMode.CAMERA: ClearMode,
    AppMode.YOLO: YoloMode,
    AppMode.EDUCATION: ClearMode,
    AppMode.SETTINGS: ClearMode
}
