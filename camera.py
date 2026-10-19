import cv2
import queue
import platform
from config import SCREEN_WIDTH, SCREEN_HEIGHT, CAMERA_WIDTH, CAMERA_HEIGHT


def cam_loop(q_in, buffer_container, video_buffer_lock):
    if platform.system() == "Windows":
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        read_frame = lambda: cap.read()
        release = cap.release

    else:
        from picamera2 import Picamera2

        cap = Picamera2()
        cap.configure(cap.create_video_configuration(
            main={"size": (CAMERA_WIDTH, CAMERA_HEIGHT), "format": "RGB888"}
        ))
        cap.start()

        read_frame = lambda: (True, cap.capture_array())
        release = cap.stop

    print(f"Camera ready. Size: {CAMERA_WIDTH}x{CAMERA_HEIGHT}")

    try:
        while True:
            ok, f_bgr = read_frame()
            if not ok:
                break

            with video_buffer_lock:
                yolo_active = buffer_container.get('yolo_enabled', True)

            if yolo_active:
                try:
                    q_in.put(f_bgr.copy(), block=False)
                except queue.Full:
                    pass

            f_resized = cv2.resize(
                f_bgr, (SCREEN_WIDTH, SCREEN_HEIGHT),
                interpolation=cv2.INTER_AREA
            )
            f_rgb = cv2.cvtColor(f_resized, cv2.COLOR_BGR2RGB)

            with video_buffer_lock:
                buffer_container['frame'] = f_rgb.copy()

    finally:
        release()