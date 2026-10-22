import sys
from pathlib import Path
from ultralytics import YOLO
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QRectF
from config import SCALE_X, SCALE_Y

def worker(q_in, q_out, q_status):
    try:
        # win tests
        # model_path = Path("models") / "v6_960" / "best.pt"
        model_path = Path("models") / "v6_960" / "best.onnx"
        target_device = "cpu"
        
        m = YOLO(str(model_path))
        q_status.put("READY")
    except Exception as e:
        q_status.put(f"[yolo] startup error: {e}")
        return
    
    while True:
        try:
            f = q_in.get()
            if f is None: 
                break
                
            results = m.predict(f, verbose=False, device=target_device, imgsz=320)
            r = results[0]

            out = []
            for b in r.boxes:
                x1, y1, x2, y2 = b.xyxy[0].tolist()
                cls_id = int(b.cls[0])
                conf_val = float(b.conf[0])
                out.append((x1, y1, x2, y2, r.names[cls_id], conf_val))
            
            q_out.put(out)
            
        except Exception:
            break

class BOXESoverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        self.boxes = []  
        
        self.colors = {
            "excessive_solder": QColor(120, 190, 255)
        }

    def set_results(self, boxes):
        self.boxes = boxes
        self.update() 

    def paintEvent(self, event):
        if not self.boxes:
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        for x1, y1, x2, y2, name, cf in self.boxes:
            color = self.colors.get(name, QColor(255, 0, 0))
            p.setPen(QPen(color, 2))
            
            rx = x1 * SCALE_X
            ry = y1 * SCALE_Y
            rw = (x2 - x1) * SCALE_X
            rh = (y2 - y1) * SCALE_Y
            
            p.drawRect(QRectF(rx, ry, rw, rh))
            p.drawText(QRectF(rx, ry - 14, 200, 14), f"{name} {cf:.2f}")
        p.end()
