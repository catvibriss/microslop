from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

class ModeBasic(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.yolo_enabled = False    