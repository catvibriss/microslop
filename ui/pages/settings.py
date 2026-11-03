from PySide6.QtCore import Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QDoubleSpinBox

from config import SETTINGS

class SettingsPanel(QWidget):
    restart_requested = Signal()

    def __init__(self, popup_overlay, parent=None):
        super().__init__(popup_overlay.card)

        self.popup_overlay = popup_overlay
        self.setObjectName('settingsPanel')
        self.setStyleSheet('QWidget#settingsPanel { background: transparent; }')

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(14)

        # model settings
        row = QHBoxLayout()
        label = QLabel('Порог уверенности YOLO', self)
        label.setFont(QFont('Arial', 16))
        row.addWidget(label, 1)

        self.yolo_conf = QDoubleSpinBox(self)
        self.yolo_conf.setRange(0.01, 1.00)
        self.yolo_conf.setSingleStep(0.05)
        self.yolo_conf.setDecimals(2)
        self.yolo_conf.setFixedWidth(115)
        self.yolo_conf.setFont(QFont('Arial', 16))
        self.yolo_conf.setStyleSheet('''
            QDoubleSpinBox { color: #000000; background: #FFFFFF;
                border: 1px solid #D4D4D4; border-radius: 4px;
                padding: 8px; }
            QDoubleSpinBox:hover { background: #F0F0F0; }
        ''')
        row.addWidget(self.yolo_conf)
        self.layout.addLayout(row)

        hint = QLabel('Изменения модели применятся после перезапуска приложения.', self)
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666666; background: transparent;')
        self.layout.addWidget(hint)

        # actions
        buttons = QHBoxLayout()
        self.cancel_button = QPushButton('Отмена', self)
        self.cancel_button.setObjectName('cancel')
        self.cancel_button.clicked.connect(self.cancel)

        self.save_button = QPushButton('Сохранить', self)
        self.save_button.clicked.connect(self.save)

        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        self.layout.addLayout(buttons)

        self.restart_button = QPushButton('Сохранить и перезапустить', self)
        self.restart_button.clicked.connect(self.save_and_restart)
        self.layout.addWidget(self.restart_button)

        self.popup_overlay.layout.insertWidget(self.popup_overlay.layout.count() - 1, self)
        self.hide()

    def open(self):
        self.yolo_conf.setValue(SETTINGS.yolo.conf)
        self.show()
        self.popup_overlay.message.hide()
        self.popup_overlay._show('настройки', '', ok=False, cancel=False)
        self.popup_overlay._center()

    def _close(self):
        self.hide()
        self.popup_overlay.message.show()
        self.popup_overlay.hide_popup()

    def cancel(self):
        self._close()

    def _save(self):
        previous = SETTINGS.yolo.conf
        try:
            SETTINGS.yolo.conf = self.yolo_conf.value()
            SETTINGS.save()
        except Exception as exc:
            SETTINGS.yolo.conf = previous
            self._close()
            self.popup_overlay.show_error(f'Не удалось сохранить настройки: {exc}')
            return False
        self._close()
        return True

    def save(self):
        if self._save():
            self.popup_overlay.show_info('Настройки сохранены. Для применения перезапусти приложение.')

    def save_and_restart(self):
        if self._save():
            self.restart_requested.emit()
