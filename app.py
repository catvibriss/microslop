import sys

import threading
import multiprocessing as mp

import queue

from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QApplication
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen, QColor
from PySide6.QtCore import QTimer, Qt, QRectF

from config import *

import model
import camera

# global quwue
q_in  = mp.Queue(maxsize=1)
q_out = mp.Queue(maxsize=4)
q_status = mp.Queue(maxsize=1)

video_buffer_lock = threading.Lock()
buffer_container = {'frame': None}

class UIOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)
        
        self.btn = QPushButton("close", self)
        self.btn.move(20, 20)
        self.btn.resize(100, 35)
        self.btn.clicked.connect(QApplication.instance().quit)

class Win(QWidget):
    def __init__(self, proc, q_out, buffer_container, video_buffer_lock):
        super().__init__()
        self.proc = proc  
        self.q_out = q_out
        self.buffer_container = buffer_container
        self.lock = video_buffer_lock
        
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()          
        self.boxes_overlay = model.BoxesOverlay(self)  
        self.ui_overlay = UIOverlay(self)        

        self.video_label.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.boxes_overlay.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.ui_overlay.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        layout.addWidget(self.video_label, 0, 0)
        layout.addWidget(self.boxes_overlay, 0, 0)
        layout.addWidget(self.ui_overlay, 0, 0)
        
        self.boxes_overlay.raise_()
        self.ui_overlay.raise_()
        
        self.t = QTimer(self)
        self.t.timeout.connect(self.update_ui)
        self.t.start(33)  
        print("interface ready")

    def update_ui(self):
        boxes = self.boxes_overlay.boxes
        while True:
            try:
                boxes = self.q_out.get_nowait()
            except queue.Empty:
                break

        with self.lock: 
            f = self.buffer_container.get('frame', None)
        if f is None: 
            return

        qimg = QImage(f.data, SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH * 3, QImage.Format_RGB888)
        pm = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pm)

        self.boxes_overlay.set_results(boxes)

def main():
    mp.freeze_support()
    mp.set_start_method('spawn', force=True)
    app = QApplication(sys.argv)
    
    # YOLO worker
    p = mp.Process(target=model.worker, args=(q_in, q_out, q_status))
    p.start()
    
    status = q_status.get()
    if status != "READY":
        print(f"yolo error: {status}")
        p.terminate()
        return

    # caameraaa thread
    threading.Thread(target=camera.cam_loop, args=(q_in, buffer_container, video_buffer_lock), daemon=True).start()
    
    # gui init
    w = Win(p, q_out, buffer_container, video_buffer_lock)
    w.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
