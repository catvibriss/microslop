import sys
import cv2
import queue
import numpy as np
from config import SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT

def cam_loop(q_in, buffer_container, video_buffer_lock):
    use_picamera2 = False
    
    if sys.platform.startswith('linux'):
        try:
            from picamera2 import Picamera2
            picam2 = Picamera2()
            config = picam2.create_preview_configuration(
                main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"}
            )
            picam2.configure(config)
            picam2.start()
            use_picamera2 = True
            print("camera ready via picamera2")
        except Exception as e:
            print(f"picamera2 failed: {e}, trying OpenCV V4L2...")
            cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
    else:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    
    if not use_picamera2:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print(f"camera ready via OpenCV. size: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")

    while True:
        if use_picamera2:
            f_rgb = picam2.capture_array("main")
            ok = True
        else:
            ok, f_bgr = cap.read()
            if not ok:
                print("camera read failed")
                break
            f_rgb = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2RGB)

        with video_buffer_lock:
            yolo_active = buffer_container.get('yolo_enabled', True)

        if yolo_active:
            try:
                q_in.put(f_rgb, block=False)
            except queue.Full:
                pass

        f_resized = cv2.resize(f_rgb, (SCREEN_WIDTH, SCREEN_HEIGHT), interpolation=cv2.INTER_AREA)

        with video_buffer_lock:
            buffer_container['frame'] = f_resized.copy()

    if use_picamera2:
        picam2.stop()
    else:
        cap.release()