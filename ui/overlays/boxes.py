from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QRectF
from config import *

class BOXESoverlay(QWidget):
    colors = {
        "excessive_solder": QColor(255, 127, 39),
        "solder_bridge": QColor(237, 28, 36),
    }

    translatings = {
        "excessive_solder": "много припоя",
        "solder_bridge": "мостик"
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        self.boxes = []  
        
    def set_results(self, boxes):
        self.boxes = boxes

        _page = self.parent().mode_overlay.currentWidget()
        if _page and hasattr(_page, "update_defect_count"):
            _page.update_defect_count(len(self.boxes))
        if _page and hasattr(_page, "set_boxes"):
            _page.set_boxes(self.boxes)

        self.update() 

    def paintEvent(self, event):
        if not self.boxes:
            return
        
        p = QPainter(self)
        self.draw_boxes(p, self.boxes, SCALE_X, SCALE_Y)

        p.end()

    @staticmethod
    def draw_boxes(p, boxes, scale_x, scale_y):
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        
        for x1, y1, x2, y2, name, cf in boxes:
            # main color
            color = BOXESoverlay.colors.get(name, QColor(255, 0, 0))

            # cords
            rx = x1 * scale_x
            ry = y1 * scale_y
            rw = (x2 - x1) * scale_x
            rh = (y2 - y1) * scale_y

            # font
            font = p.font()
            font.setPointSize(10)          
            font.setBold(True)
            p.setFont(font)

            # text
            name_text = BOXESoverlay.translatings.get(name, name)
            conf_text = f"{round(cf*100)}%"

            # size
            metrics = p.fontMetrics()

            name_width = metrics.horizontalAdvance(name_text)
            conf_width = metrics.horizontalAdvance(conf_text)
            
            padding = 6
            spacing = 15
            
            required_text_width = name_width + conf_width + (padding * 2) + spacing
            
            header_width = max(rw, required_text_width)
            header_height = 24  

            # rectangle
            header_rect = QRectF(rx, ry - header_height, header_width, header_height)
            p.fillRect(header_rect, color)

            # text writing
            p.setPen(QColor(255, 255, 255))
            
            text_rect = QRectF(rx + padding, ry - header_height, header_width - (padding * 2), header_height)
            
            p.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, name_text)
            p.drawText(text_rect, Qt.AlignRight | Qt.AlignVCenter, conf_text)
            
            p.setPen(QPen(color, 2))
            p.setBrush(Qt.NoBrush)
            p.drawRect(QRectF(rx, ry, rw, rh))
        