import queue
import cv2

from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QVBoxLayout, QPushButton
from PySide6.QtGui import QFont, QPainter, QPen, QColor, QImage
from PySide6.QtCore import Qt, QRectF, Signal, QTimer, QObject

from .base import ModeBasic

from config import *

class YoloMode(ModeBasic):
    analysis_requested = Signal()
    result_closed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)

        self.yolo_enabled = True

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        font = QFont("Arial", 16, QFont.Bold)
        label_style = "color: white; background-color: rgba(0, 0, 0, 150); padding: 5px; border-radius: 0px;"

        self.model_info_label = QLabel(f"модель v6_960 • ONNX • {YOLO_IMGSZ}x{YOLO_IMGSZ}", self)
        self.model_info_label.setFont(font)
        self.model_info_label.setStyleSheet(label_style)
        self.model_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.defect_counter_label = QLabel("всего дефектов: 0", self)
        self.defect_counter_label.setFont(font)
        self.defect_counter_label.setStyleSheet(label_style)
        self.defect_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.layout.addWidget(self.model_info_label, alignment=Qt.AlignmentFlag.AlignLeft)
        self.layout.addWidget(self.defect_counter_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.layout.addStretch(1)

        self.analysis_button = QPushButton("АНАЛИЗ ЗОНЫ", self)
        self.analysis_button.setFixedSize(420, 74)
        self.analysis_button.setFont(QFont("Arial", 20, QFont.Bold))
        
        self.analysis_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 100);
                
                border: 3px solid #D4D4D4;
                border-radius: 12px;
                background-clip: border;
                
            }}
        """)

        self.analysis_button.clicked.connect(self.analysis_requested.emit)
        self.layout.addWidget(self.analysis_button, 0, Qt.AlignmentFlag.AlignHCenter)
        self.layout.addSpacing(24)

        self.result_view = AnalysisResultView(self)
        self.result_view.closed.connect(self.result_closed.emit)
        
    def update_defect_count(self, count: int):
        self.defect_counter_label.setText(f"всего дефектов: {count}")

    def show_analysis_result(self, frame_rgb, boxes):
        self.result_view.show_result(frame_rgb, boxes)

    def hide_analysis_result(self):
        self.result_view.clear_result()

class AnalysisResultView(QWidget):
    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        self.setStyleSheet('background: #000;')

        self.image = None
        self.boxes = []

        self.close_button = QPushButton('✕', self)
        self.close_button.setGeometry(SCREEN_WIDTH - 90, 20, 65, 65)

        self.close_button.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(255, 255, 255, 100);
                
                border: 3px solid #D4D4D4;
                border-radius: 12px;
                background-clip: border;
            }}
        """)

        self.close_button.clicked.connect(self.closed.emit)

        self.hide()

    def show_result(self, frame_rgb, boxes):
        h, w = frame_rgb.shape[:2]
        self.image = QImage(frame_rgb.data, w, h, frame_rgb.strides[0], QImage.Format_RGB888).copy()
        self.boxes = list(boxes)
        self.show()
        self.raise_()
        self.close_button.raise_()
        self.update()

    def clear_result(self):
        self.hide()
        self.image = None
        self.boxes = []

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(0, 0, 0))
        if self.image is None:
            p.end()
            return
        p.drawImage(self.rect(), self.image)
        p.setRenderHint(QPainter.Antialiasing)
        sx = self.width() / self.image.width()
        sy = self.height() / self.image.height()
        names = {'excessive_solder': 'много припоя', 'solder_bridge': 'мостик'}
        colors = {'excessive_solder': QColor(255, 127, 39),
                  'solder_bridge': QColor(237, 28, 36)}
        for x1, y1, x2, y2, name, conf in self.boxes:
            color = colors.get(name, QColor(255, 50, 60))
            rx, ry = x1 * sx, y1 * sy
            rw, rh = (x2 - x1) * sx, (y2 - y1) * sy
            p.setFont(QFont('Arial', 11, QFont.Bold))
            caption = f'{names.get(name, name)}  {conf:.2f}'
            rect = QRectF(rx, max(0, ry - 29), max(rw, p.fontMetrics().horizontalAdvance(caption) + 20), 29)
            p.fillRect(rect, color)
            p.setPen(QColor(255, 255, 255))
            p.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignVCenter | Qt.AlignLeft, caption)
            p.setPen(QPen(color, 3))
            p.drawRect(QRectF(rx, ry, rw, rh))
        p.end()

class AnalysisController(QObject):
    started = Signal()
    result_shown = Signal()
    finished = Signal()

    def __init__(self, app_buffer, popup_overlay, page: YoloMode, parent=None):
        super().__init__(parent or page)
        self.app_buffer = app_buffer
        self.popup_overlay = popup_overlay
        self.page = page

        self.state = 'idle'
        self.frame = None
        self.request_id = 0
        self.count = 0

        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._countdown_tick)

        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._poll)
        self.poll_timer.start(80)

        self.page.analysis_requested.connect(self.start)
        self.page.result_closed.connect(self.close_result)

    def _set_live(self, enabled):
        with self.app_buffer.frame_lock:
            self.app_buffer.frame_state['yolo_enabled'] = enabled
        if not enabled:
            self._clear_live_results()

    def _clear_live_results(self):
        while True:
            try:
                self.app_buffer.yolo_q_result.get_nowait()
            except queue.Empty:
                break

    def start(self):
        if self.state != 'idle' or not self.page.isVisible():
            return
        self.state = 'countdown'
        self.page.analysis_button.setEnabled(False)
        self._set_live(False)
        self.started.emit()
        self.count = 0
        self.popup_overlay.show_status(f'Анализ зоны\nСнимок через {self.count}...')
        self.countdown_timer.start(1000)

    def _countdown_tick(self):
        if self.state != 'countdown':
            self.countdown_timer.stop()
            return
        self.count -= 1
        if self.count > 0:
            self.popup_overlay.set_status(f'Анализ зоны\nСнимок через {self.count}...')
            return

        self.countdown_timer.stop()
        self.popup_overlay.set_status('Делаю снимок')
        with self.app_buffer.frame_lock:
            frame = self.app_buffer.frame_state.get('frame')
            self.frame = frame.copy() if frame is not None else None
        if self.frame is None:
            self._error('Камера не предоставила кадр')
            return

        self.request_id += 1
        try:
            bgr = cv2.cvtColor(self.frame, cv2.COLOR_RGB2BGR)
            self.app_buffer.analysis_q_input.put_nowait((self.request_id, bgr))
        except Exception as exc:
            self._error(f'Не удалось отправить снимок: {exc}')
            return

        self.state = 'processing'
        self.popup_overlay.set_status('Анализирую кадр')

    def _poll(self):
        if self.state != 'processing':
            return
        
        if self.app_buffer.model_process and not self.app_buffer.model_process.is_alive():
            self._error('Процесс нейросети неожиданно завершился')
            return

        while True:
            try:
                request_id, kind, payload = self.app_buffer.analysis_q_events.get_nowait()
            except queue.Empty:
                return
            if request_id != self.request_id:
                continue
            if kind == 'status':
                self.popup_overlay.set_status(payload)
            elif kind == 'done':
                self.popup_overlay.set_status('Проверяю достоверность')
                QTimer.singleShot(500, lambda boxes=payload: self._report_stage(boxes))
                return
            elif kind == 'error':
                self._error(payload)
                return

    def _report_stage(self, boxes):
        if self.state != 'processing':
            return
        self.popup_overlay.set_status('Готовлю отчёт')
        QTimer.singleShot(650, lambda: self._show_result(boxes))

    def _show_result(self, boxes):
        if self.state != 'processing':
            return
        self.state = 'result'
        self.popup_overlay.hide_popup()
        self.page.show_analysis_result(self.frame, boxes)
        self.result_shown.emit()

    def _error(self, message):
        self.countdown_timer.stop()
        self.state = 'idle'
        self.frame = None
        self.page.analysis_button.setEnabled(True)
        self._clear_live_results()
        self._set_live(True)
        self.popup_overlay.show_error(str(message))
        self.finished.emit()

    def close_result(self):
        if self.state != 'result':
            return
        self.page.hide_analysis_result()
        self.frame = None
        self.state = 'idle'
        self.page.analysis_button.setEnabled(True)
        self._clear_live_results()
        self._set_live(True)
        self.finished.emit()

    def stop(self):
        self.countdown_timer.stop()
        self.poll_timer.stop()
        self.page.hide_analysis_result()
        self.frame = None
        self.state = 'idle'
        self.page.analysis_button.setEnabled(True)
