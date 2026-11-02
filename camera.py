import cv2
import queue
from config import SCREEN_WIDTH, SCREEN_HEIGHT, IS_LINUX, ZOOM_MIN, ZOOM_MAX

import time #[p]
from _perf import perf #[p]

def set_zoom(buffer_container, video_buffer_lock, zoom):
    zoom = max(ZOOM_MIN, min(ZOOM_MAX, float(zoom)))
    with video_buffer_lock:
        buffer_container['zoom'] = zoom

def get_zoom(buffer_container, video_buffer_lock):
    with video_buffer_lock:
        return buffer_container.get('zoom', 1.0)

def cam_loop(q_in, buffer_container, video_buffer_lock, stop_event):
    frame_idx = 0

    with video_buffer_lock:
        buffer_container['frame_idx'] = 0
        buffer_container['zoom'] = 1.0

    if IS_LINUX:
        from picamera2 import Picamera2

        cam = Picamera2()
        cam.configure(cam.create_video_configuration(
            main={"size": (SCREEN_WIDTH, SCREEN_HEIGHT), "format": "RGB888"}
        ))
        crop_min, crop_max, _ = cam.camera_controls['ScalerCrop']
        cam.start()

        base_x, base_y, base_w, base_h = crop_max
        last_zoom = 1.0

        print(f"[camera] picamera2. res: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    else: # windows tests
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, SCREEN_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, SCREEN_HEIGHT)
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        last_zoom = 1.0
        print(f"[camera] openCV. res: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    try:
        while not stop_event.is_set():
            yolo_active = buffer_container.get('yolo_enabled', False)
            zoom = get_zoom(buffer_container, video_buffer_lock)

            if IS_LINUX:
                if zoom != last_zoom:
                    w = max(crop_min[2], int(base_w / zoom))
                    h = max(crop_min[3], int(base_h / zoom))
                    x = base_x + (base_w - w) // 2
                    y = base_y + (base_h - h) // 2

                    cam.set_controls({"ScalerCrop": (x, y, w, h)})
                    last_zoom = zoom

                f_bgr = cam.capture_array()
                t_work = time.perf_counter() #[p]

                f_rgb = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2RGB)

            else:
                ok, f_bgr = cap.read()
                if not ok:
                    break

                t_work = time.perf_counter() #[p]

                if zoom != 1.0:
                    h, w = f_bgr.shape[:2]
                    cw, ch = int(w / zoom), int(h / zoom)
                    x, y = (w - cw) // 2, (h - ch) // 2
                    f_bgr = cv2.resize(
                        f_bgr[y:y+ch, x:x+cw],
                        (w, h),
                        interpolation=cv2.INTER_LINEAR
                    )

                f_rgb = cv2.cvtColor(f_bgr, cv2.COLOR_BGR2RGB)

            if yolo_active:

                if q_in.full():
                    perf.count('yolo_drop') #[p]

                else:
                    f_raw = f_bgr
                    # f_yolo = cv2.resize(f_raw, (320, 200), interpolation=cv2.INTER_LINEAR)

                    try:
                        q_in.put(f_raw, block=False)

                        perf.count('yolo_send') #[p]

                    except queue.Full:
                        perf.count('yolo_drop') #[p]

            frame_idx += 1
            with video_buffer_lock:
                buffer_container['frame'] = f_rgb
                buffer_container['frame_idx'] = frame_idx

            #[p]
            perf.add('cam_work', time.perf_counter() - t_work)
            perf.count('cam_frames')
            perf.report_if_due()
            #[p]

    finally:
        if IS_LINUX:
            cam.stop()
            cam.close()

        else:
            cap.release()

        print("camera stopped")
