import queue
import os

from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QStackedWidget
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QTimer, Qt

from config import SCREEN_WIDTH, SCREEN_HEIGHT

from ui import pages
from ui.pages.yolo import AnalysisController
from ui.pages.settings import SettingsPanel

from ui.overlays.ui_palace import UIoverlay
from ui.overlays.boxes import BOXESoverlay
from ui.overlays.popup import POPUPoverlay

import time #[p]
from utils.perf import perf #[p]

class Win(QWidget):
    def __init__(self, app_buffer):
        super().__init__()

        # app basics
        self.app_buffer = app_buffer
        self.current_mode = None
        self.restart_requested = False

        # YOLO flags
        self.yolo_ready = False
        self.yolo_enabled = False

        # basics layout
        self.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # GUI layers
        self.video_label = QLabel()          
        self.video_label.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.boxes_overlay = BOXESoverlay(self)  
        self.boxes_overlay.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)

        self.mode_overlay = QStackedWidget(self)
        self.mode_overlay.setAttribute(Qt.WA_TranslucentBackground)
        self.mode_overlay.setFixedSize(SCREEN_WIDTH, SCREEN_HEIGHT)
        
        self.ui_overlay = UIoverlay(self, self.handle_mode_change)        
        self.ui_overlay.setVisible(False)
        
        # modes registration
        self.modes_pages = {}
        self.page_indices = {}
        for mode_enum, page_class in pages.MODES_CLASSES.items():
            page_widget = page_class()
            self.modes_pages[mode_enum] = page_widget

            idx = self.mode_overlay.addWidget(page_widget)
            self.page_indices[mode_enum] = idx

        # layout build
        layout.addWidget(self.video_label, 0, 0)
        layout.addWidget(self.boxes_overlay, 0, 0)
        layout.addWidget(self.mode_overlay, 0, 0)
        
        self.boxes_overlay.raise_()
        self.mode_overlay.raise_()
        self.ui_overlay.raise_()

        # zone analysis
        self.popup_overlay = POPUPoverlay(self)
        self.analysis_controller = AnalysisController(
            self.app_buffer, self.popup_overlay, self.modes_pages[pages.AppMode.YOLO], self
        )
        self.analysis_controller.started.connect(self._analysis_started)
        self.analysis_controller.result_shown.connect(self._analysis_result_shown)
        self.analysis_controller.finished.connect(self._analysis_finished)
        self.popup_overlay.raise_()

        # settings
        self.settings_panel = SettingsPanel(self.popup_overlay)
        self.settings_panel.restart_requested.connect(self._restart_from_settings)

        # timers
        self.t = QTimer(self)
        self.t.timeout.connect(self.update_ui)
        self.t.start(33)  

        print("4-layer sandwich ready withOUT zoom")

        self.yolo_ready_timer = QTimer(self)
        self.yolo_ready_timer.timeout.connect(self.check_yolo_status)
        self.yolo_ready_timer.start(50)

    def check_yolo_status(self):
        try:
            status = self.app_buffer.yolo_q_status.get_nowait()
            if status == "READY":
                print("[GUI] yolo are ready!")

                self.yolo_ready = True
                self.yolo_ready_timer.stop()

                self.ui_overlay.setVisible(True)
                self.handle_mode_change(pages.AppMode.CLEAR)

                if os.environ.get('MICROSLOP_TEST_MODE'):
                    QTimer.singleShot(3000, self._perf_test_begin)
            
            else:
                print(f"[GUI] error: {status}")
                self.close()

        except queue.Empty:
            pass

    def _perf_test_begin(self):
        mode = os.environ.get('MICROSLOP_TEST_MODE', 'CLEAR').upper()
        self.handle_mode_change(pages.AppMode.YOLO if mode == 'YOLO' else pages.AppMode.CLEAR)
        print(f'[TEST START] mode={mode} imgsz={os.environ.get("MICROSLOP_TEST_IMGSZ", "default")} '
              f'threads={os.environ.get("YOLO_THREADS", "default")}', flush=True)
        duration = max(1, int(os.environ.get('MICROSLOP_TEST_SECONDS', '40')))
        QTimer.singleShot(duration * 1000, self._perf_test_end)

    def _perf_test_end(self):
        print('[TEST END]', flush=True)
        self.close()

    def _clear_q_out(self):
        while True:
            try:
                self.app_buffer.yolo_q_result.get_nowait()
            except queue.Empty:
                break
    
    def handle_mode_change(self, mode_enum):
        if not self.yolo_ready or self.analysis_controller.state != 'idle':
            return

        if mode_enum == pages.AppMode.SETTINGS:
            self.settings_panel.open()
            return

        target_idx = self.page_indices.get(mode_enum)
        target_page = self.modes_pages.get(mode_enum)
        
        if target_idx is None or target_page is None:
            return

        self.boxes_overlay.set_results([])
        self._clear_q_out()

        self.mode_overlay.setCurrentIndex(target_idx)
        self.current_mode = mode_enum

        with self.app_buffer.frame_lock:
            self.app_buffer.frame_state['yolo_enabled'] = target_page.yolo_enabled
            self.yolo_enabled = self.app_buffer.frame_state['yolo_enabled']

    # settings
    def _restart_from_settings(self):
        self.restart_requested = True
        self.close()

    # zone analysis
    def _analysis_started(self):
        self.yolo_enabled = False
        self.boxes_overlay.set_results([])

    def _analysis_result_shown(self):
        self.boxes_overlay.hide()
        self.ui_overlay.hide()
        self.popup_overlay.raise_()

    def _analysis_finished(self):
        self.boxes_overlay.show()
        self.ui_overlay.setVisible(self.yolo_ready)
        self.boxes_overlay.set_results([])
        self._clear_q_out()
        with self.app_buffer.frame_lock:
            self.yolo_enabled = self.app_buffer.frame_state['yolo_enabled']
        self.popup_overlay.raise_()

    #[p]
    def update_ui(self):
        t = time.perf_counter()
        prev = getattr(self, '_perf_prev', None)
        if prev is not None:
            perf.add('ui_tick_gap', t - prev)
        self._perf_prev = t
        with self.app_buffer.frame_lock:
            idx = self.app_buffer.frame_state.get('frame_idx') 
        is_new_frame = (idx != getattr(self, '_perf_idx', None))
        if is_new_frame:
            perf.count('ui_new_frames')
            self._perf_idx = idx 
        if self.analysis_controller.state != 'result':
            self._pt_update_ui(is_new_frame)
        perf.add('ui_work', time.perf_counter() - t)
        perf.count('ui_ticks')
        perf.report_if_due()
    #[p]

    def _pt_update_ui(self, is_new_frame): #[p]
        t_boxes = time.perf_counter() #[p]
        if self.yolo_enabled:
            new_boxes = None
            while True:
                try:
                    new_boxes = self.app_buffer.yolo_q_result.get_nowait()
                except queue.Empty:
                    break
            if new_boxes is not None:
                self.boxes_overlay.set_results(new_boxes)
        else:
            # self.boxes_overlay.set_results([])
            while True:
                try: self.app_buffer.yolo_q_result.get_nowait()
                except queue.Empty: break

        perf.add('ui_boxes', time.perf_counter() - t_boxes) #[p]

        if not is_new_frame:
            return

        with self.app_buffer.frame_lock: 
            f = self.app_buffer.frame_state.get('frame', None)
            if f is None: 
                return

        t_render = time.perf_counter() #[p]
        qimg = QImage(f.data, SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH * 3, QImage.Format_RGB888).copy()
        
        pm = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pm)
        perf.add('ui_render', time.perf_counter() - t_render) #[p]

    def closeEvent(self, event):
        print("closing app...")

        self.analysis_controller.stop()

        for t in (getattr(self, 't', None), getattr(self, 'yolo_ready_timer', None)):
            if t is not None and t.isActive():
                t.stop()

        self.app_buffer.camera_stop.set()
        if self.app_buffer.camera_thread.is_alive():
            self.app_buffer.camera_thread.join(timeout=1.5)

        if self.app_buffer.model_process and self.app_buffer.model_process.is_alive():
            try:
                print("terminating YOLO...")
                self.app_buffer.model_process.terminate()
                self.app_buffer.model_process.join(timeout=1.0)
                if self.app_buffer.model_process.is_alive():
                    self.app_buffer.model_process.kill()
            except Exception as e:
                print(f"[GUI] YOLO terminate err: {e}")

        for q in (self.app_buffer.yolo_q_input, self.app_buffer.yolo_q_result, self.app_buffer.yolo_q_status,
                  self.app_buffer.analysis_q_input, self.app_buffer.analysis_q_events):
            try:
                q.cancel_join_thread()
                q.close()
            except Exception:
                pass

        print("app closed!")
        event.accept()
