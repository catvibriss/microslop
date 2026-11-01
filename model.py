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
    if IS_LINUX:
        import os
        nice = int(os.environ.get("YOLO_NICE", YOLO_NICE))
        thr = int(os.environ.get("YOLO_THREADS", YOLO_THREADS))

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

            m.predict(_f_fake, verbose=False, device=target_device, imgsz=480)
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
            results = m.predict(f, verbose=False, device=target_device, imgsz=480)
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
            "excessive_solder": QColor(255, 127, 39),
            "solder_bridge": QColor(237, 28, 36),
        }

        self.translatings = {
            "excessive_solder": "много припойойойа",
            "solder_bridge": "мостик"
        }

    def set_results(self, boxes):
        self.boxes = boxes

        _page = self.parent().mode_overlay.currentWidget()
        if _page and hasattr(_page, "update_defect_count"):
            _page.update_defect_count(len(self.boxes))

        self.update() 

    def paintEvent(self, event):
        if not self.boxes:
            return
        
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.TextAntialiasing)
        
        for x1, y1, x2, y2, name, cf in self.boxes:
            # main color
            color = self.colors.get(name, QColor(255, 0, 0))

            # cords
            rx = x1 * SCALE_X
            ry = y1 * SCALE_Y
            rw = (x2 - x1) * SCALE_X
            rh = (y2 - y1) * SCALE_Y

            # font
            font = p.font()
            font.setPointSize(10)          
            font.setBold(True)
            p.setFont(font)

            # text
            name_text = self.translatings.get(name, name)
            conf_text = f"{cf:.2f}"

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
            
        p.end()
