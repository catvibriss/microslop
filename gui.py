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

        # init ==
        self.change_mode = change_mode_callback
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)

        # setup ==
        self.collapsed_width = 70
        self.expanded_width = 250
        self.is_expanded = False

        self.resize(self.collapsed_width, SCREEN_HEIGHT)

        # toggle  ==
        self.btn_toggle = QPushButton("", self)
        self.btn_toggle.resize(self.collapsed_width, 150)
        self.btn_toggle.clicked.connect(self.toggle_menu)
        
        svg_path = "img/menu.svg"

        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 100);
                
                border: 3px solid #D4D4D4;
                border-left-color: transparent;
                
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
                background-clip: border;
                
                qproperty-icon: url('{svg_path}');
                qproperty-iconSize: 16px 16px;
                padding-left: 2px;
            }}
            QPushButton:hover {{ 
                background-color: rgba(255, 255, 255, 150);
                border-color: #EAEAEA;
                border-left-color: transparent;
            }}
            QPushButton:pressed {{ 
                background-color: rgba(255, 255, 255, 200);
                border-color: #FFFFFF;
                border-left-color: transparent;
            }}
        """)

        self.btn_toggle.move(0, (SCREEN_HEIGHT - self.btn_toggle.height()) // 2)

        # menu ==
        self.btn_height = 50
        self.menu_buttons = []
        # -- -- --

        self.btn_cam = QPushButton("clear", self)
        self.btn_cam.clicked.connect(lambda: self.select_mode("CLEAR"))
        
        self.btn_yolo = QPushButton("YOLO", self)
        self.btn_yolo.clicked.connect(lambda: self.select_mode("YOLO"))

        self.btn_close = QPushButton("close", self)
        self.btn_close.clicked.connect(main_window.close)

        self.menu_buttons = [self.btn_cam, self.btn_yolo, self.btn_close]
        # -- -- --

        self.menu_height = len(self.menu_buttons) * self.btn_height
        self.start_y = (SCREEN_HEIGHT - self.menu_height) // 2

        self.menu_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 255);
                color: #000000;
                border: none;
                border-bottom: 2px solid rgba(0, 0, 0, 30);
                font-weight: normal;
                text-align: left;
                padding-left: 20px;
            }
            QPushButton:hover { background-color: rgba(240, 240, 240, 255); }
            QPushButton:pressed { background-color: rgba(220, 220, 220, 255); }
        """
        
        for i, btn in enumerate(self.menu_buttons):
            btn.resize(self.expanded_width, self.btn_height)
            btn.move(0, self.start_y + (i * self.btn_height))
            btn.setVisible(False)
            
            style = self.menu_style
            
            if i == 0:
                style += "QPushButton { border-top-right-radius: 12px; }"

            elif i == len(self.menu_buttons) - 1:
                style += "QPushButton { border-bottom-right-radius: 12px; border-bottom: none; }"
                
            btn.setStyleSheet(style)

    def toggle_menu(self):
        if not self.is_expanded:
            self.resize(self.expanded_width, SCREEN_HEIGHT)
            self.btn_toggle.setVisible(False)
            for btn in self.menu_buttons:
                btn.setVisible(True)
            self.is_expanded = True
        else:
            self.collapse_menu()

    def collapse_menu(self):
        for btn in self.menu_buttons:
            btn.setVisible(False)
        self.btn_toggle.setVisible(True)
        self.resize(self.collapsed_width, SCREEN_HEIGHT)
        self.is_expanded = False

    def select_mode(self, mode_name):
        self.change_mode(mode_name)
        self.collapse_menu()

    def mousePressEvent(self, event):
        if self.is_expanded:
            if not (0 <= event.x() <= self.expanded_width and self.start_y <= event.y() <= self.start_y + self.menu_height):
                self.collapse_menu()
        super().mousePressEvent(event)


class Win(QWidget):
    def __init__(self, proc, q_out, buffer_container, video_buffer_lock, q_status):
        super().__init__()
        self.proc = proc  
        self.q_out = q_out
        self.buffer_container = buffer_container
        self.lock = video_buffer_lock

        self.q_status = q_status
        self.current_mode = "CLEAR"
        self.yolo_ready = False
        
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
        self.ui_overlay.setVisible(False)

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

        self.yolo_ready_timer = QTimer(self)
        self.yolo_ready_timer.timeout.connect(self.check_yolo_status)
        self.yolo_ready_timer.start(50)

    def check_yolo_status(self):
        try:
            status = self.q_status.get_nowait()
            if status == "READY":
                print("[GUI] yolo are ready!")
                self.yolo_ready = True
                self.yolo_ready_timer.stop()

                self.ui_overlay.setVisible(True)
                self.handle_mode_change("CLEAR")
            else:
                print(f"[GUI] error: {status}")
                self.close()

        except queue.Empty:
            pass

    def handle_mode_change(self, mode_name):
        if not self.yolo_ready and mode_name != "LOADING":
            return

        if mode_name == "CLEAR":
            self.mode_overlay.setCurrentIndex(0)      
            self.current_mode = "CLEAR"
            self.boxes_overlay.set_results([])

            with self.lock:
                self.buffer_container['yolo_enabled'] = False
                
        elif mode_name == "YOLO":
            self.mode_overlay.setCurrentIndex(1)
            self.current_mode = "YOLO"
            with self.lock:
                self.buffer_container['yolo_enabled'] = True

    def update_ui(self):
        boxes = self.boxes_overlay.boxes
        if self.current_mode == "YOLO":
            while True:
                try:
                    boxes = self.q_out.get_nowait()
                except queue.Empty:
                    break
            self.boxes_overlay.set_results(boxes)
        else:
            # self.boxes_overlay.set_results([])
            while True:
                try: self.q_out.get_nowait()
                except queue.Empty: break

        with self.lock: 
            f = self.buffer_container.get('frame', None)
            if f is None: 
                return

        qimg = QImage(f.data, SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH * 3, QImage.Format_RGB888).copy()
        
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
