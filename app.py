import sys
import threading
import multiprocessing as mp
from PySide6.QtWidgets import QApplication

import model
import camera
import gui

def main():
    mp.freeze_support()

    mp.set_start_method('spawn', force=True)
    
    q_in  = mp.Queue(maxsize=1)
    q_out = mp.Queue(maxsize=4)
    q_status = mp.Queue(maxsize=1)
    video_buffer_lock = mp.Lock()

    buffer_container = {
        'frame': None,
        'yolo_enabled': False
    }

    app = QApplication(sys.argv)
    
    # YOLO worker
    p = mp.Process(target=model.worker, args=(q_in, q_out, q_status))
    p.start()
    
    status = q_status.get()
    if status != "READY":
        print(f"yolo error: {status}")
        p.terminate()
        return

    # camera thread
    threading.Thread(target=camera.cam_loop, args=(q_in, buffer_container, video_buffer_lock), daemon=True).start()

    # window :d
    w = gui.Win(p, q_out, buffer_container, video_buffer_lock)
    w.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    main()