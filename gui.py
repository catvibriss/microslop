import queue
import time
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QApplication, QStackedWidget
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import QTimer, Qt
from config import SCREEN_WIDTH, SCREEN_HEIGHT
import model

class ClearMode(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)

class YoloMode(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.btn_setting = QPushButton("play with me 0.0", self)
        self.btn_setting.move(20, 120)
        self.btn_setting.resize(160, 35)

class UIoverlay(QWidget):
    def __init__(self, main_window, change_mode_callback):
        super().__init__(main_window)
        self.change_mode = change_mode_callback
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        
        self.btn_cam = QPushButton("clear", self)
        self.btn_cam.move(20, 20)
        self.btn_cam.resize(120, 35)
        self.btn_cam.clicked.connect(lambda: self.change_mode("CLEAR"))
        
        self.btn_yolo = QPushButton("YOLO", self)
        self.btn_yolo.move(150, 20)
        self.btn_yolo.resize(120, 35)
        self.btn_yolo.clicked.connect(lambda: self.change_mode("YOLO"))

        self.btn_zoom = QPushButton("zoom: 1.0x", self)
        self.btn_zoom.move(300, 20)  
        self.btn_zoom.resize(120, 35)
        self.btn_zoom.clicked.connect(main_window.toggle_zoom)

        self.btn_close = QPushButton("close", self)
        self.btn_close.move(20, 70)
        self.btn_close.resize(100, 35)
        self.btn_close.clicked.connect(main_window.close)


class Win(QWidget):
    def __init__(self, proc, q_out, buffer_container, video_buffer_lock):
        super().__init__()
        self.proc = proc  
        self.q_out = q_out
        self.buffer_container = buffer_container
        self.lock = video_buffer_lock

        self.current_mode = "CLEAR"
        
        self.last_time = time.time()
        self.fps = 0.0
        
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()          
        self.video_label.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.boxes_overlay = model.BOXESoverlay(self)  
        self.boxes_overlay.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.mode_overlay = QStackedWidget(self)
        self.mode_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.mode_overlay.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        self.mode_overlay.addWidget(ClearMode()) 
        self.mode_overlay.addWidget(YoloMode())

        self.ui_overlay = UIoverlay(self, self.handle_mode_change)        
        self.ui_overlay.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        layout.addWidget(self.video_label, 0, 0)
        layout.addWidget(self.boxes_overlay, 0, 0)
        layout.addWidget(self.mode_overlay, 0, 0)
        layout.addWidget(self.ui_overlay, 0, 0)
        
        self.boxes_overlay.raise_()
        self.mode_overlay.raise_()
        self.ui_overlay.raise_()
        
        self.t = QTimer(self)
        self.t.timeout.connect(self.update_ui)
        self.t.start(33)  
        print("4-layer sandwich ready with *ZOOM*")

    def toggle_zoom(self):
        with self.lock:
            current_zoom = self.buffer_container.get('zoom_factor', 1.0)
            
            if current_zoom == 1.0:
                new_zoom = 2.0
            elif current_zoom == 2.0:
                new_zoom = 4.0
            else:
                new_zoom = 1.0
                
            self.buffer_container['zoom_factor'] = new_zoom
            self.ui_overlay.btn_zoom.setText(f"zoom: {new_zoom:.1f}x")
            print(f"zoom set to: {new_zoom:.1f}x")

    def handle_mode_change(self, mode_name):
        if mode_name == "CLEAR":
            self.mode_overlay.setCurrentIndex(0)      
            self.current_mode = "CLEAR"
            with self.lock:
                self.buffer_container['yolo_enabled'] = False
                
        elif mode_name == "YOLO":
            self.mode_overlay.setCurrentIndex(1)
            self.current_mode = "YOLO"
            with self.lock:
                self.buffer_container['yolo_enabled'] = True

    def update_ui(self):
        current_time = time.time()
        delta = current_time - self.last_time
        if delta > 0:
            self.fps = 1.0 / delta
        self.last_time = current_time

        boxes = self.boxes_overlay.boxes
        if self.current_mode == "YOLO":
            while True:
                try:
                    boxes = self.q_out.get_nowait()
                except queue.Empty:
                    break
            self.boxes_overlay.set_results(boxes)
        else:
            self.boxes_overlay.set_results([])
            while True:
                try: self.q_out.get_nowait()
                except queue.Empty: break

        with self.lock: 
            f = self.buffer_container.get('frame', None)
        if f is None: return

        qimg = QImage(f.data, SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH * 3, QImage.Format_RGB888)
        
        painter = QPainter(qimg)
        painter.setPen(QColor(0, 255, 0))
        painter.setFont(QFont("Arial", 16, QFont.Bold))
        painter.drawText(SCREEN_WIDTH - 120, 30, f"FPS: {self.fps:.1f}")
        painter.end()

        pm = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pm)

    def closeEvent(self, event):
        print("closing app...")
        self.t.stop()
        
        if self.proc and self.proc.is_alive():
            try:
                self.proc.terminate()
                self.proc.join(timeout=1.0)
            except:
                pass
        
        print("app closed!")
        event.accept()
