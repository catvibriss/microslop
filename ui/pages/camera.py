from datetime import datetime
from pathlib import Path

from PySide6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QGridLayout, QScrollArea, QToolButton
from PySide6.QtGui import QFont, QImage, QPixmap, QImageReader, QIcon
from PySide6.QtCore import Qt, Signal, QSize

from .base import ModeBasic

from utils.graphical import make_colored_svg
from ui import icons

from config import SCREEN_WIDTH, SCREEN_HEIGHT, PHOTO_DIR

class CameraMode(ModeBasic):
    gallery_opened = Signal()
    gallery_closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.app_buffer = None
        self.photo_dir = Path(PHOTO_DIR)
        self.photo_dir.mkdir(parents=True, exist_ok=True)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.addStretch(1)

        self.status_label = QLabel('', self)
        self.status_label.setFont(QFont('Arial', 14, QFont.Bold))
        self.status_label.setStyleSheet('color: white; background: transparent;')
        self.status_label.setAlignment(Qt.AlignCenter)
        self.layout.addWidget(self.status_label)

        self.photo_button = QPushButton('СФОТКАТЬ', self)
        self.photo_button.setFixedSize(420, 74)
        self.photo_button.setFont(QFont('Arial', 20, QFont.Bold))
        self.photo_button.setLayoutDirection(Qt.RightToLeft)
        self.photo_button.setIcon(make_colored_svg(icons.CAMERA, Qt.white))
        self.photo_button.setIconSize(QSize(28, 28))
        self.photo_button.setStyleSheet(self._button_style())
        self.photo_button.clicked.connect(self.take_photo)

        self.gallery_button = QPushButton('', self)
        self.gallery_button.setFixedSize(74, 74)
        self.gallery_button.setIcon(make_colored_svg(icons.IMAGE, Qt.white))
        self.gallery_button.setIconSize(QSize(28, 28))
        self.gallery_button.setStyleSheet(self._button_style())
        self.gallery_button.clicked.connect(self.open_gallery)

        buttons = QHBoxLayout()
        buttons.setSpacing(12)
        buttons.setAlignment(Qt.AlignHCenter)
        buttons.addWidget(self.photo_button)
        buttons.addWidget(self.gallery_button)
        self.layout.addLayout(buttons)
        self.layout.addSpacing(24)

        self.gallery = PhotoGallery(self.photo_dir, self)
        self.gallery.closed.connect(self.gallery_closed.emit)

    @staticmethod
    def _button_style():
        return '''
            QPushButton {
                color: white;
                background-color: rgba(255, 255, 255, 100);
                border: 3px solid #D4D4D4;
                border-radius: 12px;
            }
            QPushButton:hover { background-color: rgba(255, 255, 255, 150); }
            QPushButton:pressed { background-color: rgba(255, 255, 255, 200); }
        '''

    def set_app_buffer(self, app_buffer):
        self.app_buffer = app_buffer

    def take_photo(self):
        if self.app_buffer is None:
            self.status_label.setText('Камера недоступна')
            return

        with self.app_buffer.frame_lock:
            frame = self.app_buffer.frame_state.get('frame')
            frame = frame.copy() if frame is not None else None

        if frame is None:
            self.status_label.setText('Нет кадра')
            return

        try:
            self.photo_dir.mkdir(parents=True, exist_ok=True)
            h, w = frame.shape[:2]
            image = QImage(frame.data, w, h, frame.strides[0], QImage.Format_RGB888).copy()
            path = self.photo_dir / f'photo_{datetime.now():%Y%m%d_%H%M%S_%f}.jpg'
            if not image.save(str(path), 'JPG', 95):
                raise OSError('Не удалось записать JPEG')
            self.status_label.setText('Фото сохранено')
        except Exception as exc:
            self.status_label.setText(f'Ошибка сохранения: {exc}')

    def open_gallery(self):
        try:
            self.gallery.open()
        except Exception as exc:
            self.status_label.setText(f'Ошибка галереи: {exc}')
            return
        self.gallery_opened.emit()

class PhotoGallery(QWidget):
    closed = Signal()

    def __init__(self, photo_dir, parent=None):
        super().__init__(parent)
        self.photo_dir = Path(photo_dir)
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setStyleSheet('background: white; color: black;')

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        header = QHBoxLayout()
        self.back_button = QPushButton('назад', self)
        self.back_button.setFixedSize(150, 55)
        self.back_button.setStyleSheet(self._button_style())
        self.back_button.clicked.connect(self.back)
        header.addWidget(self.back_button)

        self.title = QLabel('галерея', self)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont('Arial', 20, QFont.Bold))
        header.addWidget(self.title, 1)

        self.close_button = QPushButton('', self)
        self.close_button.setFixedSize(65, 55)
        self.close_button.setIcon(make_colored_svg(icons.CLOSE, Qt.black))
        self.close_button.setIconSize(QSize(28, 28))
        self.close_button.setStyleSheet(self._button_style())
        self.close_button.clicked.connect(self.close_gallery)
        header.addWidget(self.close_button)
        layout.addLayout(header)

        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet('QScrollArea { border: none; background: white; }')
        self.grid_widget = QWidget()
        self.grid = QGridLayout(self.grid_widget)
        self.grid.setAlignment(Qt.AlignTop)
        self.grid.setSpacing(16)
        self.scroll.setWidget(self.grid_widget)
        layout.addWidget(self.scroll)

        self.preview = QLabel(self)
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setStyleSheet('background: white;')
        self.preview.hide()
        layout.addWidget(self.preview)

        self.hide()

    @staticmethod
    def _button_style():
        return '''
            QPushButton {
                background-color: white;
                color: black;
                border: 2px solid #D4D4D4;
                border-radius: 12px;
                font-weight: normal;
            }
            QPushButton:hover { background-color: rgb(240, 240, 240); }
            QPushButton:pressed { background-color: rgb(220, 220, 220); }
        '''

    def open(self):
        self.photo_dir.mkdir(parents=True, exist_ok=True)
        self.preview.hide()
        self.scroll.show()
        self._load_photos()
        self.show()
        self.raise_()

    def _load_photos(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        photos = sorted(
            (p for p in self.photo_dir.iterdir() if p.is_file() and p.suffix.lower() in ('.jpg', '.jpeg', '.png')),
            key=lambda p: p.name, reverse=True
        )
        if not photos:
            label = QLabel('Фотографий пока нет', self.grid_widget)
            label.setFont(QFont('Arial', 16))
            self.grid.addWidget(label, 0, 0)
            return

        for i, path in enumerate(photos):
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            reader.setScaledSize(QSize(260, 165))
            image = reader.read()
            button = QToolButton(self.grid_widget)
            button.setFixedSize(285, 210)
            button.setText('')
            button.setIcon(QIcon(QPixmap.fromImage(image)))
            button.setIconSize(QSize(260, 165))
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)
            button.setStyleSheet('''
                QToolButton { background: white; border: 2px solid #D4D4D4;
                    border-radius: 12px; padding: 6px; }
                QToolButton:hover { background: rgb(240, 240, 240); }
                QToolButton:pressed { background: rgb(220, 220, 220); }
            ''')
            button.clicked.connect(lambda checked=False, p=path: self.show_photo(p))
            self.grid.addWidget(button, i // 4, i % 4)

    def show_photo(self, path):
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return
        self.preview.setPixmap(pixmap.scaled(
            SCREEN_WIDTH - 60, SCREEN_HEIGHT - 115,
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
        self.scroll.hide()
        self.preview.show()

    def back(self):
        if self.preview.isVisible():
            self.preview.clear()
            self.preview.hide()
            self.scroll.show()
        else:
            self.close_gallery()

    def close_gallery(self):
        self.hide()
        self.preview.clear()
        self.closed.emit()
