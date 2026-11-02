from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from .base import ModeBasic

from config import *

class YoloMode(ModeBasic):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.yolo_enabled = True

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        font = QFont("Arial", 16, QFont.Bold)
        label_style = "color: white; background-color: rgba(0, 0, 0, 150); padding: 5px; border-radius: 0px;"

        self.model_info_label = QLabel(f"модель v6_960 • ONNX • {YOLO_IMGSZ}x{YOLO_IMGSZ}", self)
        self.model_info_label.setFont(font)
        self.model_info_label.setStyleSheet(label_style)
        self.model_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.defect_counter_label = QLabel("всего дефектов: 0", self)
        self.defect_counter_label.setFont(font)
        self.defect_counter_label.setStyleSheet(label_style)
        self.defect_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(self.model_info_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.defect_counter_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.layout.addStretch(1)

    def update_defect_count(self, count: int):
        self.defect_counter_label.setText(f"всего дефектов: {count}")
