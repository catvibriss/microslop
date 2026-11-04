from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QPushButton, QApplication, QStackedWidget
from PySide6.QtGui import QImage, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import QTimer, Qt, QSize

from utils.graphical import make_colored_svg 

from config import SCREEN_WIDTH, SCREEN_HEIGHT
from ui import pages, icons

class UIoverlay(QWidget):
    def __init__(self, main_window, change_mode_callback):
        super().__init__(main_window)

        # init ==
        self.change_mode = change_mode_callback
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_AlwaysStackOnTop, True)

        # setup ==
        self.collapsed_width = 70
        self.expanded_width = 290
        self.is_expanded = False

        self.toggle_y = (SCREEN_HEIGHT - 150) // 2

        # toggle  ==
        self.btn_toggle = QPushButton("", self)
        self.btn_toggle.resize(self.collapsed_width, 150)
        self.btn_toggle.clicked.connect(self.toggle_menu)

        svg_path = icons.MENU
        self.btn_toggle.setIcon(make_colored_svg(svg_path, Qt.white))
        self.btn_toggle.setIconSize(QSize(28, 28))

        self.btn_toggle.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 100);
                
                border: 3px solid #D4D4D4;
                border-left-color: transparent;
                
                border-top-right-radius: 12px;
                border-bottom-right-radius: 12px;
                background-clip: border;
                
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

        self.btn_toggle.move(0, 0)

        # menu ==
        self.btn_height = 70
        self.menu_buttons = []
        # -- -- --

        self.btn_clear = QPushButton("микроскоп", self)
        self.btn_clear.clicked.connect(lambda: self.select_mode(pages.AppMode.CLEAR))
        
        self.btn_camera = QPushButton("камера", self)
        self.btn_camera.clicked.connect(lambda: self.select_mode(pages.AppMode.CAMERA))

        self.btn_yolo = QPushButton("поиск дефектов", self)
        self.btn_yolo.clicked.connect(lambda: self.select_mode(pages.AppMode.YOLO))

        # self.btn_edu = QPushButton("обучение", self)
        # self.btn_edu.clicked.connect(lambda: self.select_mode(pages.AppMode.EDUCATION))

        self.btn_settings = QPushButton("настройки", self)
        self.btn_settings.clicked.connect(lambda: self.select_mode(pages.AppMode.SETTINGS))

        self.btn_close = QPushButton("выход", self)
        self.btn_close.clicked.connect(main_window.close)

        self.menu_buttons = [self.btn_clear, self.btn_camera, self.btn_yolo, self.btn_settings, self.btn_close]
        # -- -- --

        self.menu_height = len(self.menu_buttons) * self.btn_height
        self.start_y = (SCREEN_HEIGHT - self.menu_height) // 2

        self.menu_style = """
            QPushButton {
                background-color: rgba(255, 255, 255, 255);
                color: #000000;
                border-style: none none solid none;
                border-width: 0px 0px 2px 0px;
                border-color: transparent transparent #E1E1E1 transparent;
                margin: 0px;
                font-weight: normal;
                text-align: left;
                padding-left: 20px;
                font-size: 20px;
            }
            QPushButton:hover { background-color: rgb(240, 240, 240); }
            QPushButton:pressed { background-color: rgb(220, 220, 220); }
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

        self._apply_collapsed()

    def _apply_collapsed(self):
        self.setGeometry(0, self.toggle_y, self.collapsed_width, self.btn_toggle.height())

    def toggle_menu(self):
        if not self.is_expanded:
            self.setGeometry(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
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

        self._apply_collapsed()
        self.is_expanded = False

    def select_mode(self, mode):
        self.change_mode(mode)
        self.collapse_menu()

    def mousePressEvent(self, event):
        if self.is_expanded:
            if not (0 <= event.x() <= self.expanded_width and self.start_y <= event.y() <= self.start_y + self.menu_height):
                self.collapse_menu()
        super().mousePressEvent(event)


