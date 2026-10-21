import sys
import os
import time
import traceback
from ultralytics import YOLO
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor
from PySide6.QtCore import Qt, QRectF
from config import SCALE_X, SCALE_Y

CRASH_LOG_PATH = "yolo_debug_log.txt"

def log_to_file(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(CRASH_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {message}\n")
    except:
        pass

def worker(q_in, q_out, q_status):
    if os.path.exists(CRASH_LOG_PATH):
        try: os.remove(CRASH_LOG_PATH)
        except: pass

    log_to_file("=== ЗАПУСК YOLO ВОРКЕРА ===")
    
    try:
        is_linux = sys.platform.startswith('linux')
        
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        
        if is_linux:
            # rpi prod
            model_path = os.path.join(BASE_DIR, 'models', 'v6_960', 'weights', 'ncnn')
            target_device = "vulkan"
            print("[YOLO] rpi!")
            log_to_file(f"Платформа: Linux (RPi). Абс. путь: {model_path}, Девайс: {target_device}")
        else:
            # win tests
            model_path = os.path.join(BASE_DIR, 'models', 'v6_960', 'weights', 'best.pt')
            target_device = "cpu"
            print("[YOLO] win!")
            log_to_file(f"Платформа: Windows. Абс. путь: {model_path}, Девайс: {target_device}")
            
        m = YOLO(model_path)
        q_status.put("READY")
        log_to_file("Инициализация успешна. Отправлен READY.")
    except Exception as e:
        err_msg = f"ОШИБКА ИНИЦИАЛИЗАЦИИ: {e}\n{traceback.format_exc()}"
        print(f"[YOLO CRITICAL] Startup error: {e}")
        log_to_file(err_msg)
        q_status.put(f"yolo startup error: {e}")
        return
    
    frame_count = 0
    
    while True:
        try:
            f = q_in.get()
            if f is None: 
                log_to_file("Получен сигнал None. Выход.")
                break
                
            frame_count += 1
            if frame_count <= 5 or frame_count % 30 == 0:
                log_to_file(f"Кадр #{frame_count} взят из очереди. Shape: {f.shape if hasattr(f, 'shape') else 'None'}")
            
            start_time = time.time()
            results = m.predict(f, verbose=False, device=target_device, imgsz=960)
            
            if isinstance(results, (list, tuple)):
                r = results[0]
            else:
                r = results
                
            end_time = time.time()
            inference_ms = (end_time - start_time) * 1000
            
            if frame_count <= 5 or frame_count % 30 == 0:
                log_to_file(f"Инференс кадра #{frame_count}: {inference_ms:.2f} мс. Найдено сырых боксов: {len(r.boxes) if hasattr(r, 'boxes') else 'None'}")

            out = []
            if hasattr(r, 'boxes') and r.boxes is not None:
                for b in r.boxes:
                    box_data = b.xyxy.tolist()
                    if isinstance(box_data[0], list):
                        coords = box_data[0]
                    else:
                        coords = box_data
                        
                    cls_id = int(b.cls.item() if hasattr(b.cls, 'shape') and len(b.cls.shape) > 0 else int(b.cls))
                    name = r.names[cls_id]
                    conf = float(b.conf.item() if hasattr(b.conf, 'shape') and len(b.conf.shape) > 0 else float(b.conf))
                    
                    out.append((*coords, name, conf))
            
            if (frame_count <= 5 or frame_count % 30 == 0) and len(out) > 0:
                log_to_file(f"Собрано для GUI: {out}")
                
            q_out.put(out)
            
        except Exception as e:
            err_loop = f"ВЫЛЕТ НА КАДРЕ #{frame_count}:\nОшибка: {e}\n{traceback.format_exc()}"
            print(f"[YOLO LOOP ERROR] Сбой шага. См. {CRASH_LOG_PATH}")
            log_to_file(err_loop)
            try: q_out.put([])
            except: pass
            continue

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
