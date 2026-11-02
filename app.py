import os
os.environ["QT_LOGGING_RULES"] = "*=false"
os.environ["QT_QUIET"] = "1"
os.environ["QT_DEBUG_PLUGINS"] = "0"

import sys
import threading
import multiprocessing as mp
from PySide6.QtWidgets import QApplication

def main():
    import config
    config.IS_LINUX = sys.platform.startswith('linux')
    
    import camera
    import gui
    import model

    mp.freeze_support()
    mp.set_start_method('spawn', force=True)
    
    q_in  = mp.Queue(maxsize=1)
    q_out = mp.Queue(maxsize=4)
    q_status = mp.Queue(maxsize=1)
    video_buffer_lock = mp.Lock()

    buffer_container = {
        'frame': None,
        'frame_idx': None,
        'yolo_enabled': False,
        'zoom': config.ZOOM_MIN,
        'zoom_applied': config.ZOOM_MIN
    }

    app = QApplication(sys.argv)
    
    # YOLO worker
    p = mp.Process(target=model.worker, args=(q_in, q_out, q_status))
    p.start()

    # camera thread
    cam_stop = threading.Event()
    cam_thread = threading.Thread(target=camera.cam_loop, args=(q_in, buffer_container, video_buffer_lock, cam_stop), daemon=True)
    cam_thread.start()

    # window :d
    w = gui.Win(p, q_in, q_out, buffer_container, video_buffer_lock, q_status, cam_stop, cam_thread)

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