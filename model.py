import sys
from ultralytics import YOLO
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QRectF
from config import SCALE_X, SCALE_Y

def worker(q_in, q_out, q_status):
    try:
        is_linux = sys.platform.startswith('linux')
        
        if is_linux:
            # rpi prod
            model_path = './models/v6_960/weights/best_ncnn_model'
            target_device = "vulkan"
            print("[YOLO] rpi!")
        else:
            # win tests
            model_path = './models/v6_960/weights/best.pt'
            target_device = "cpu"
            print("[YOLO] win!")
            
        m = YOLO(model_path)
        q_status.put("READY")
    except Exception as e:
        q_status.put(f"yolo startup error: {e}")
        return
    
    while True:
        try:
            f = q_in.get()
            if f is None: 
                break
                
            r = m.predict(f, verbose=False, device=target_device, imgsz=960)[0] 

            out = [( *b.xyxy[0].tolist(), r.names[int(b.cls[0])], float(b.conf[0]) )
                   for b in r.boxes]
            
            q_out.put(out)
            
        except Exception:
            break

class BOXESoverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        self.boxes = []  

    def set_results(self, boxes):
        self.boxes = boxes
        self.update() 

    def paintEvent(self, event):
        if not self.boxes:
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(255, 0, 0), 2))
        
        for x1, y1, x2, y2, name, cf in self.boxes:
            rx = x1 * SCALE_X
            ry = y1 * SCALE_Y
            rw = (x2 - x1) * SCALE_X
            rh = (y2 - y1) * SCALE_Y
            
            p.drawRect(QRectF(rx, ry, rw, rh))
            p.drawText(QRectF(rx, ry - 14, 200, 14), f"{name} {cf:.2f}")
        p.end()