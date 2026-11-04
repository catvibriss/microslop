import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QLineEdit, QVBoxLayout, QHBoxLayout, QScrollArea, QStackedWidget

from .base import ModeBasic

STUDENTS_DIR = Path(__file__).resolve().parents[2] / 'students'

class EducationMode(ModeBasic):
    profile_selected = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.active_student = None
        self.profile_picker = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addStretch(1)

        self.student_label = QLabel('', self)
        self.student_label.setFont(QFont('Arial', 20, QFont.Bold))
        self.student_label.setAlignment(Qt.AlignCenter)
        self.student_label.setStyleSheet('color: white; background: rgba(0, 0, 0, 150);')
        self.layout.addWidget(self.student_label)
        self.layout.addStretch(1)

    def set_popup(self, popup_overlay):
        self.profile_picker = StudentPicker(popup_overlay)
        self.profile_picker.selected.connect(self._select_student)

    def open_profile_picker(self):
        self.profile_picker.open()

    def _select_student(self, student):
        self.active_student = student
        self.student_label.setText(f"ученик: {student['name']}")
        self.profile_selected.emit()

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
