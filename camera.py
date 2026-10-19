import sys
import cv2
import queue
import subprocess
import numpy as np
from config import SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT

def cam_loop(q_in, buffer_container, video_buffer_lock):
    if sys.platform.startswith('linux'):
        use_rpicam = True
        cmd = [
            'rpicam-vid',
            '--width', str(CAMERA_WIDTH),
            '--height', str(CAMERA_HEIGHT),
            '--codec', 'yuv420',
            '--timeout', '0',
            '--nopreview',
            '--stdout'
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        frame_size = CAMERA_WIDTH * CAMERA_HEIGHT * 3 // 2
        print(f"camera ready via rpicam-vid. size: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")
    else:
        use_rpicam = False
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print(f"camera ready. size: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")

    while True:
        if use_rpicam:
            raw = proc.stdout.read(frame_size)
            if len(raw) < frame_size: break
            yuv = np.frombuffer(raw, dtype=np.uint8).reshape((CAMERA_HEIGHT * 3 // 2, CAMERA_WIDTH))
            f_bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
        else:
            ok, f_bgr = cap.read()
            if not ok: break

        with video_buffer_lock:
            yolo_active = buffer_container.get('yolo_enabled', True)

        if yolo_active:
            try:
                q_in.put(f_bgr, block=False)
            except queue.Full:
                pass

        f_resized = cv2.resize(f_bgr, (SCREEN_WIDTH, SCREEN_HEIGHT), interpolation=cv2.INTER_AREA)
        f_rgb = cv2.cvtColor(f_resized, cv2.COLOR_BGR2RGB)

        with video_buffer_lock:
            buffer_container['frame'] = f_rgb.copy()

    if use_rpicam:
        proc.terminate()
    else:
        cap.release()