from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QFrame

class POPUPoverlay(QWidget):
    accepted = Signal()
    rejected = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setGeometry(parent.rect())
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setVisible(False)
        self._dismissible = False
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide_popup)

        self.card = QFrame(self)
        self.card.setObjectName('popupCard')
        self.card.setStyleSheet('''
            QFrame#popupCard { background: #FFFFFF; border: 2px solid #D4D4D4;
                border-radius: 12px; }
            QLabel { color: #000000; background: transparent; border: none; }
            QPushButton { background: #FFFFFF; color: #000000;
                border: 1px solid #D4D4D4; border-radius: 4px;
                padding: 10px 20px; font-size: 17px; font-weight: normal; }
            QPushButton:hover { background: #F0F0F0; }
            QPushButton:pressed { background: #DCDCDC; }
            QPushButton#cancel { background: #FFFFFF; color: #000000; }
        ''')
        self.card.setFixedWidth(550)
        self.layout = QVBoxLayout(self.card)
        self.layout.setContentsMargins(30, 25, 30, 25)
        self.layout.setSpacing(14)

        self.title = QLabel(self.card)
        self.title.setAlignment(Qt.AlignCenter)
        font = QFont('Arial', 20)
        self.title.setFont(font)
        self.layout.addWidget(self.title)

        self.message = QLabel(self.card)
        self.message.setWordWrap(True)
        self.message.setAlignment(Qt.AlignCenter)
        self.message.setFont(QFont('Arial', 17))
        self.layout.addWidget(self.message)

        self.button_row = QHBoxLayout()
        self.button_row.setSpacing(14)
        self.button_row.addStretch(1)
        self.ok_button = QPushButton('ОК', self.card)
        self.ok_button.clicked.connect(self._accept)
        self.cancel_button = QPushButton('Отмена', self.card)
        self.cancel_button.setObjectName('cancel')
        self.cancel_button.clicked.connect(self._reject)
        self.button_row.addWidget(self.cancel_button)
        self.button_row.addWidget(self.ok_button)
        self.button_row.addStretch(1)
        self.layout.addLayout(self.button_row)
        self._center()

    def _center(self):
        self.card.adjustSize()
        self.card.move((self.width() - self.card.width()) // 2,
                       (self.height() - self.card.height()) // 2)

    def resizeEvent(self, event):
        self._center()
        super().resizeEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 155))
        painter.end()

    def _show(self, title, message, *, ok=False, cancel=False,
              dismissible=False, timeout_ms=0):
        self._timer.stop()

        self.title.setText(title)
        self.title.setVisible(bool(title))

        self.message.setText(message)

        self.ok_button.setVisible(ok)

        self.cancel_button.setVisible(cancel)

        self._dismissible = dismissible

        self.card.adjustSize()
        self._center()
        self.show()

        self.raise_()
        self.setFocus()
        if timeout_ms:
            self._timer.start(timeout_ms)

    def show_info(self, text, timeout_ms=2500):
        self._show('Информация', text, timeout_ms=timeout_ms)

    def show_warning(self, text):
        self._show('Предупреждение', text, ok=True)

    def show_error(self, text):
        self._show('Ошибка', text, ok=True)

    def show_status(self, text):
        """Non-dismissible: only calling code can update/close it."""
        self._show('', text)

    def set_status(self, text):
        self.message.setText(text)
        self._center()

    def show_ok(self, text, title='Информация'):
        self._show(title, text, ok=True)

    def show_confirm(self, text, title='Подтверждение'):
        self._show(title, text, ok=True, cancel=True)

    def hide_popup(self):
        self._timer.stop()
        self.hide()

    def _accept(self):
        self.hide_popup()
        self.accepted.emit()

    def _reject(self):
        self.hide_popup()
        self.rejected.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape and self._dismissible:
            self._reject()
        else:
            event.accept()

    def mousePressEvent(self, event):
        # Always consume background clicks: lower UI is never clicked through.
        event.accept()
