import os
os.environ["QT_LOGGING_RULES"] = "*=false"
os.environ["QT_QUIET"] = "1"
os.environ["QT_DEBUG_PLUGINS"] = "0"

import sys
import threading
import multiprocessing as mp

from PySide6.QtWidgets import QApplication

import config

def main():
    from core import camera, yolo_worker
    from core.appbuffer import AppBuffer
    
    from ui import window

    mp.freeze_support()
    mp.set_start_method('spawn', force=True)
    
    app_buffer = AppBuffer()

    app = QApplication(sys.argv)

    # YOLO worker
    app_buffer.model_process = mp.Process(
        target=yolo_worker.worker,
        args=(app_buffer.yolo_q_input, app_buffer.yolo_q_result, app_buffer.yolo_q_status,
              app_buffer.analysis_q_input, app_buffer.analysis_q_events),
    )

    app_buffer.model_process.start()

    # camera thread
    app_buffer.camera_thread = threading.Thread(target=camera.cam_loop, args=(app_buffer,), daemon=True)
    app_buffer.camera_thread.start()

    # window :d
    w = window.Win(app_buffer)

    if config.IS_LINUX:
        # rpi prod
        w.showFullScreen()
    else: 
        # win tests
        w.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    main()