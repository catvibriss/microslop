import multiprocessing as mp
import threading

class AppBuffer:
    def __init__(self):
        self.yolo_q_input = mp.Queue(maxsize=1)
        self.yolo_q_result = mp.Queue(maxsize=4)
        self.yolo_q_status = mp.Queue(maxsize=1)

        self.frame_lock = mp.Lock()
        self.frame_state = {
            'frame': None,
            'frame_idx': None,
            'yolo_enabled': False,
        }

        self.camera_stop = threading.Event()
        self.camera_thread = None
        self.model_process = None
