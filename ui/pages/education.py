import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, Signal, QRectF, QSize
from PySide6.QtGui import QFont, QPainter, QPainterPath, QColor
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QScrollArea, QStackedWidget

from .base import ModeBasic
from utils.graphical import make_colored_svg
from ui import icons
from config import SCALE_X, SCALE_Y

STUDENTS_DIR = Path(__file__).resolve().parents[2] / 'students'

class EducationMode(ModeBasic):
    profile_selected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_student = None
        self.profile_picker = None
        self.handbook = None
        self._boxes = []
        self.yolo_enabled = True

        self.handbook = HandbookViewer(self)

    def set_popup(self, popup_overlay):
        self.profile_picker = StudentPicker(popup_overlay)
        self.profile_picker.selected.connect(self._select_student)

    def open_profile_picker(self):
        self.profile_picker.open()

    def _select_student(self, student):
        self.active_student = student
        self.profile_selected.emit()

    def set_boxes(self, boxes):
        self._boxes = list(boxes)

    def hideEvent(self, event):
        self._boxes = []
        self.handbook.close_viewer()
        super().hideEvent(event)

    def resizeEvent(self, event):
        self.handbook.update_geometry()
        super().resizeEvent(event)

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton or self.active_student is None or self.handbook is None:
            return super().mousePressEvent(event)

        point = event.position()
        hits = []

        for x1, y1, x2, y2, name, cf in self._boxes:
            rect = QRectF(x1 * SCALE_X, y1 * SCALE_Y,
                          (x2 - x1) * SCALE_X, (y2 - y1) * SCALE_Y)
            if rect.contains(point):
                hits.append((rect.width() * rect.height(), -cf, name))

        if not hits:
            return super().mousePressEvent(event)

        _, _, name = min(hits)
        self.handbook.open_article(name)
        event.accept()

class HandbookViewer(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.panel_width = 460
        self.corner_radius = 48
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName('handbookViewer')
        self.setStyleSheet('''
            QWidget#handbookViewer { background: transparent; border: none; }
            QLabel { color: #1F2937; background: transparent; border: none; }
        ''')

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(28, 22, 20, 20)

        header = QHBoxLayout()
        self.title = QLabel('справка(?)', self)
        self.title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.title.setFont(QFont('Arial', 20, QFont.Bold))
        header.addWidget(self.title, 1)

        self.close_button = QPushButton('', self)
        self.close_button.setFixedSize(48, 46)
        self.close_button.setIcon(make_colored_svg(icons.CLOSE, Qt.black))
        self.close_button.setIconSize(QSize(24, 24))
        self.close_button.setStyleSheet('''
            QPushButton { background: #F3F4F6; border: none; border-radius: 12px; }
            QPushButton:hover { background: #E5E7EB; }
            QPushButton:pressed { background: #D1D5DB; }
        ''')
        self.close_button.clicked.connect(self.close_viewer)
        header.addWidget(self.close_button)
        self.layout.addLayout(header)
        self.layout.addStretch(1)

        self.update_geometry()
        self.hide()

    def paintEvent(self, event):
        r = min(self.corner_radius, self.width() / 2, self.height() / 2)
        w = self.width()
        h = self.height()

        path = QPainterPath()
        path.moveTo(r, 0)
        path.lineTo(w, 0)
        path.lineTo(w, h)
        path.lineTo(r, h)
        path.quadTo(0, h, 0, h - r)
        path.lineTo(0, r)
        path.quadTo(0, 0, r, 0)
        path.closeSubpath()

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillPath(path, QColor('#FFFFFF'))
        painter.end()

    def update_geometry(self):
        self.setGeometry(self.parent().width() - self.panel_width, 0,
                         self.panel_width, self.parent().height())

    def open_article(self, name):
        self.update_geometry()
        self.show()
        self.raise_()

    def close_viewer(self):
        self.hide()

class StudentPicker(QWidget):
    selected = Signal(dict)

    def __init__(self, popup_overlay):
        super().__init__(popup_overlay.card)
        self.popup_overlay = popup_overlay
        self.setObjectName('studentPicker')
        self.setStyleSheet('''
            QWidget#studentPicker { background: transparent; }
            QPushButton#studentCard {
                background: white; color: black; border: 2px solid #D4D4D4;
                border-radius: 8px; padding: 8px; font-size: 17px;
            }
            QPushButton#studentCard:hover { background: #F0F0F0; }
            QPushButton#studentCard:pressed { background: #DCDCDC; }
            QLineEdit {
                background: white; color: black; border: 2px solid #D4D4D4;
                border-radius: 5px; padding: 12px; font-size: 20px;
            }
            QLabel { color: white; background: transparent; }
        ''')

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(12)

        self.stack = QStackedWidget(self)
        self.layout.addWidget(self.stack)

        # profile selection
        self.list_page = QWidget(self)
        list_layout = QVBoxLayout(self.list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea(self.list_page)
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFixedHeight(205)
        self.scroll.setStyleSheet('QScrollArea { border: none; background: transparent; }')
        self.cards_widget = QWidget()
        self.cards = QHBoxLayout(self.cards_widget)
        self.cards.setContentsMargins(2, 2, 2, 2)
        self.cards.setSpacing(12)
        self.scroll.setWidget(self.cards_widget)
        list_layout.addWidget(self.scroll)

        self.cancel_button = QPushButton('Отмена', self.list_page)
        self.cancel_button.clicked.connect(self.close_picker)
        list_layout.addWidget(self.cancel_button, alignment=Qt.AlignCenter)
        self.stack.addWidget(self.list_page)

        # create student
        self.create_page = QWidget(self)
        create_layout = QVBoxLayout(self.create_page)
        create_layout.setContentsMargins(0, 0, 0, 0)
        create_layout.setSpacing(14)

        self.name_input = QLineEdit(self.create_page)
        self.name_input.setPlaceholderText('Имя ученика')
        self.name_input.setMaxLength(80)
        self.name_input.returnPressed.connect(self.create_student)
        create_layout.addWidget(self.name_input)

        self.error_label = QLabel('', self.create_page)
        self.error_label.setStyleSheet('color: #ffb3b3; background: transparent;')
        self.error_label.hide()
        create_layout.addWidget(self.error_label)

        buttons = QHBoxLayout()
        back_button = QPushButton('Отмена', self.create_page)
        back_button.clicked.connect(lambda: self._show_list())
        create_button = QPushButton('Создать', self.create_page)
        create_button.clicked.connect(self.create_student)
        buttons.addWidget(back_button)
        buttons.addWidget(create_button)
        create_layout.addLayout(buttons)
        self.stack.addWidget(self.create_page)

        self.popup_overlay.layout.insertWidget(self.popup_overlay.layout.count() - 1, self)
        self.hide()

    def open(self):
        try:
            STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
            self._load_students()
        except OSError as exc:
            self.popup_overlay.show_error(f'Не удалось открыть профили: {exc}')
            return

        self.stack.setCurrentWidget(self.list_page)
        self.popup_overlay.card.setFixedWidth(860)
        self.popup_overlay._show('выберите ученика', '', ok=False, cancel=False)
        self.popup_overlay.message.hide()
        self.show()
        self.popup_overlay._center()

    def _load_students(self):
        while self.cards.count():
            item = self.cards.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()

        for path in sorted(STUDENTS_DIR.glob('*.json')):
            try:
                student = json.loads(path.read_text(encoding='utf-8'))
                if not isinstance(student, dict) or not isinstance(student.get('name'), str):
                    continue
                if not student['name'].strip() or not isinstance(student.get('id'), str):
                    continue
            except (OSError, ValueError, UnicodeError):
                continue
            button = self._card(student['name'])
            button.clicked.connect(lambda checked=False, s=student: self._choose(s))
            self.cards.addWidget(button)

        add_button = self._card('＋\nдобавить')
        add_button.clicked.connect(self._show_create)
        self.cards.addWidget(add_button)
        self.cards.addStretch(1)
        self.scroll.horizontalScrollBar().setValue(0)

    def _card(self, caption):
        button = QPushButton(caption, self.cards_widget)
        button.setObjectName('studentCard')
        button.setFixedSize(155, 155)
        button.setFont(QFont('Arial', 17))
        return button

    def _show_create(self):
        self.name_input.clear()
        self.error_label.hide()
        self.stack.setCurrentWidget(self.create_page)
        self.popup_overlay.title.setText('новый ученик')
        self.popup_overlay._center()
        self.name_input.setFocus()

    def _show_list(self):
        self.stack.setCurrentWidget(self.list_page)
        self.popup_overlay.title.setText('выберите ученика')
        self.popup_overlay._center()

    def create_student(self):
        name = self.name_input.text().strip()
        if not name:
            self.error_label.setText('введите имя')
            self.error_label.show()
            return

        student = {
            'id': uuid4().hex,
            'name': name,
            'created_at': datetime.now().isoformat(timespec='seconds')
        }
        try:
            STUDENTS_DIR.mkdir(parents=True, exist_ok=True)
            path = STUDENTS_DIR / f"{student['id']}.json"
            path.write_text(json.dumps(student, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        except OSError as exc:
            self.error_label.setText(f'ошибка сохранения: {exc}')
            self.error_label.show()
            return
        self._choose(student)

    def _choose(self, student):
        self.close_picker()
        self.selected.emit(student)

    def close_picker(self):
        self.hide()
        self.popup_overlay.message.show()
        self.popup_overlay.card.setFixedWidth(550)
        self.popup_overlay.hide_popup()
