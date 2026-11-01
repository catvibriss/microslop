from pathlib import Path

import numpy as np

from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QRectF

from config import *

import time #[p]
from _perf import perf #[p]

def worker(q_in, q_out, q_status):
    
    # YOLO speed эксперименты

    import os
    nice = int(os.environ.get("YOLO_NICE", "0"))
    thr = int(os.environ.get("YOLO_THREADS", "0"))

    if nice:
        os.nice(nice)

    if thr:
        import onnxruntime as ort
        _orig = ort.InferenceSession

        class _Sess(_orig):
            def __init__(self, path, sess_options=None, providers=None, **kw):
                if sess_options is None:
                    sess_options = ort.SessionOptions()
                sess_options.intra_op_num_threads = thr
                super().__init__(path, sess_options=sess_options, providers=providers, **kw)

        ort.InferenceSession = _Sess

    print(f"[yolo] tune: nice={nice} threads={thr}", flush=True)

    # -- -- -- -- --
    
    from ultralytics import YOLO

    t_boot = time.perf_counter() #[p]
    perf.tag = 'yolo' #[p]

    try:
        # model_path = Path("models") / "v6_960" / "best.pt"
        model_path = Path("models") / "v6_960" / "best.onnx"
        target_device = "cpu"

        m = YOLO(str(model_path))

        # prewarm
        print("[yolo] prewarm: start")
        _f_fake = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)

        for i in range(3):
            
            t_warm = time.perf_counter() #[p]

            m.predict(_f_fake, verbose=False, device=target_device, imgsz=320)
            print(f"[yolo] prewarm: predict #{i} {(time.perf_counter() - t_warm)*1000:.0f} ms") #[p]


        q_status.put("READY")
        print(f"[yolo] start -> READY: {time.perf_counter() - t_boot:.2f} s", flush=True) #[p]

    except Exception as e:
        q_status.put(f"[yolo] startup error: {e}")
        return

    n = 0  #[p]

    while True:
        try:
            f = q_in.get()
            if f is None:
                break

            #[p]
            t = time.perf_counter()
            results = m.predict(f, verbose=False, device=target_device, imgsz=320)
            dt = time.perf_counter() - t

            n += 1
            if n <= 3:
                print(f"[yolo] predict #{n}: {dt * 1000:.0f} ms", flush=True)
            perf.add('infer', dt)
            perf.count('infer_done')
            perf.report_if_due()
            #[p]

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
